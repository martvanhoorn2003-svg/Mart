"""
Operational Trends Analysis stream for the ACECQA education & care
services dataset.

Business questions this answers for ACECQA:
  - How big are services, and does that vary by type or by urban/rural
    location? (capacity planning)
  - Which service types run year-round vs only during school terms?
  - Is the sector still growing, and is that growth genuine or an
    artifact of the 2012 National Quality Framework rollout?
  - Do longer opening hours or bigger centres associate with quality —
    and does transport accessibility influence capacity or hours at all?

Outputs PNGs to outputs/figures/ and appends to outputs/summary_stats.json.

Run: python src/operational_analysis.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from clean import NOT_YET_ASSESSED, load_clean
from quality_analysis import primary_service_type
from urban_rural import classify_urban_rural

FIG_DIR = Path("outputs/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)
SUMMARY_PATH = Path("outputs/summary_stats.json")

INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"
SURFACE = "#fcfcfb"
CAT = {
    "blue": "#2a78d6", "orange": "#eb6834", "aqua": "#1baf7a", "yellow": "#eda100",
    "magenta": "#e87ba4", "green": "#008300", "violet": "#4a3aa7", "red": "#e34948",
}
SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#1c5cab", "#104281"]

RATING_ORDER_SUBSTANTIVE = [
    "Significant Improvement Required", "Working Towards NQS", "Meeting NQS", "Exceeding NQS", "Excellent",
]

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "axes.edgecolor": BASELINE,
    "axes.labelcolor": INK_SECONDARY, "text.color": INK_PRIMARY,
    "xtick.color": INK_SECONDARY, "ytick.color": INK_SECONDARY,
    "axes.grid": False, "font.family": "sans-serif", "font.size": 11,
})


def add_operational_fields(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["PrimaryServiceType"] = primary_service_type(d)

    has_annual = d["Annual Monday Start Time"].notna()
    has_term = d["School Terms Only Session 1 Monday Start Time"].notna()
    d["OperatingPattern"] = "Neither / other pattern"
    d.loc[~has_annual & has_term, "OperatingPattern"] = "Term-time only"
    d.loc[has_annual, "OperatingPattern"] = "Year-round"

    def to_hours(series):
        return pd.to_timedelta(series.astype(str), errors="coerce").dt.total_seconds() / 3600

    total = pd.Series(0.0, index=d.index)
    for day in DAYS:
        start = to_hours(d[f"Annual {day} Start Time"])
        end = to_hours(d[f"Annual {day} End Time"])
        total = total.add((end - start).clip(lower=0).fillna(0))
    d["WeeklyHours"] = np.where(has_annual, total, np.nan)
    # Family Day Care schemes record round-the-clock availability across
    # their whole educator network (median ~168h/week = "always open"),
    # which isn't a comparable "opening hours" figure to a single centre -
    # excluded from the hours analysis, kept for capacity/type charts.
    d.loc[d["PrimaryServiceType"] == "Family Day Care", "WeeklyHours"] = np.nan
    return d


def chart_capacity_by_type(df: pd.DataFrame, urban_rural_medians: pd.Series) -> dict:
    # Family Day Care excluded: capacity is recorded per individually-
    # registered educator across a scheme, not as a single site limit, so
    # NumberOfApprovedPlaces is populated for only 2 of 417 FDC services -
    # not enough to report a meaningful median.
    d = df[~df["PrimaryServiceType"].isin(["Other", "Family Day Care"])].dropna(subset=["NumberOfApprovedPlaces"])
    med = d.groupby("PrimaryServiceType")["NumberOfApprovedPlaces"].median().sort_values(ascending=False)
    counts = d["PrimaryServiceType"].value_counts()

    fig, ax = plt.subplots(figsize=(8.5, 5))
    bars = ax.barh(med.index, med.values, color=CAT["blue"], height=0.6)
    for bar, name in zip(bars, med.index):
        ax.text(bar.get_width() + 1.5, bar.get_y() + bar.get_height() / 2,
                f"{bar.get_width():.0f} places (n={counts[name]:,})", va="center", fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Median approved places")
    ax.set_title("How big is a typical service, by type?", fontsize=13, fontweight="bold",
                 color=INK_PRIMARY, loc="left", pad=14)
    ax.text(0.99, 0.03, f"Urban services: {urban_rural_medians['Urban']:.0f} places (median)  |  "
                        f"Rural services: {urban_rural_medians['Rural']:.0f} places (median)",
            transform=ax.transAxes, ha="right", fontsize=8.5, color=INK_SECONDARY)
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.tick_params(left=False)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "10_capacity_by_type.png", dpi=200)
    plt.close(fig)
    return {
        "median_places_urban": round(float(urban_rural_medians["Urban"]), 1),
        "median_places_rural": round(float(urban_rural_medians["Rural"]), 1),
    }


def chart_operating_pattern(df: pd.DataFrame) -> dict:
    d = df[df["PrimaryServiceType"] != "Other"]
    ct = pd.crosstab(d["PrimaryServiceType"], d["OperatingPattern"], normalize="index")
    order = ["Year-round", "Term-time only", "Neither / other pattern"]
    ct = ct.reindex(columns=order, fill_value=0)
    ct = ct.sort_values("Year-round", ascending=False)
    counts = d["PrimaryServiceType"].value_counts()
    ct.index = [f"{i}  (n={counts[i]:,})" for i in ct.index]

    colors = {"Year-round": SEQ_BLUE[5], "Term-time only": CAT["orange"], "Neither / other pattern": GRIDLINE}
    fig, ax = plt.subplots(figsize=(9, 4.2))
    left = np.zeros(len(ct))
    y = np.arange(len(ct))
    for cat in order:
        vals = ct[cat].to_numpy()
        ax.barh(y, vals, left=left, height=0.6, color=colors[cat], edgecolor=SURFACE, linewidth=1.2, label=cat)
        for i, v in enumerate(vals):
            if v >= 0.08:
                ax.text(left[i] + v / 2, y[i], f"{v:.0%}", ha="center", va="center", fontsize=8.5,
                        color="white" if cat != "Neither / other pattern" else INK_PRIMARY)
        left += vals
    ax.set_yticks(y); ax.set_yticklabels(ct.index)
    ax.set_xlim(0, 1); ax.set_xticks([0, .25, .5, .75, 1.0]); ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.invert_yaxis()
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.tick_params(left=False)
    ax.set_title("Year-round vs term-time-only operation, by service type", fontsize=13,
                 fontweight="bold", color=INK_PRIMARY, loc="left", pad=14)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=3, frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "11_operating_pattern_by_type.png", dpi=200)
    plt.close(fig)
    return {}


def chart_approval_trend(df: pd.DataFrame) -> dict:
    d = df[df["ApprovalYear"].between(2006, 2024)]  # drop the handful of pre-2006 / 2025-partial-year points
    by_year = d.groupby("ApprovalYear").size()

    fig, ax = plt.subplots(figsize=(9.5, 5))
    colors = [CAT["red"] if y == 2012 else CAT["blue"] for y in by_year.index]
    ax.bar(by_year.index, by_year.values, color=colors, width=0.7)
    ax.annotate(
        "2012: National Quality Framework\ncommenced - existing services bulk-\ntransferred to new approval numbers,\nnot genuine new openings",
        xy=(2012, by_year.loc[2012]), xytext=(2013.5, by_year.loc[2012] * 0.92),
        fontsize=8.5, color=INK_SECONDARY,
        arrowprops=dict(arrowstyle="->", color=INK_MUTED),
    )
    ax.set_ylabel("Services approved")
    ax.set_title("Services approved per year — mind the 2012 regulatory transition",
                 fontsize=12.5, fontweight="bold", color=INK_PRIMARY, loc="left", pad=14)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(BASELINE); ax.spines["bottom"].set_color(BASELINE)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "12_approval_trend.png", dpi=200)
    plt.close(fig)

    post_2013 = d[d["ApprovalYear"] >= 2013]
    trend_years = post_2013.groupby("ApprovalYear").size()
    return {
        "approvals_2012_nqf_spike": int(by_year.loc[2012]),
        "approvals_2024": int(trend_years.get(2024, 0)),
        "approvals_2014": int(trend_years.get(2014, 0)),
    }


def chart_hours_vs_quality(df: pd.DataFrame) -> dict:
    d = df[df["OverallRating"].notna() & df["WeeklyHours"].notna()].copy()
    d["OverallRating"] = d["OverallRating"].astype(str)
    d = d[d["OverallRating"] != NOT_YET_ASSESSED]
    d = d[d["WeeklyHours"].between(1, 100)]  # exclude the near-zero and near-168h data artifacts
    d["rating_code"] = d["OverallRating"].map({v: i for i, v in enumerate(RATING_ORDER_SUBSTANTIVE)})

    bins = [0, 45, 50, 55, 60, 100]
    labels = ["<45h", "45-50h", "50-55h", "55-60h", "60h+"]
    d["hours_bin"] = pd.cut(d["WeeklyHours"], bins=bins, labels=labels)
    props = d.groupby("hours_bin", observed=True)["OverallRating"].apply(lambda s: (s == "Exceeding NQS").mean())
    counts = d["hours_bin"].value_counts().reindex(labels)

    rho, pval = stats.spearmanr(d["WeeklyHours"], d["rating_code"])

    # Same question the assignment asks for transport: does accessibility
    # influence operational capacity or hours? Tested here rather than as
    # a separate chart, alongside the hours-vs-quality result above.
    cap = df.dropna(subset=["NumberOfApprovedPlaces"])
    cap = cap[~cap["train_dist_outlier"]]
    rho_cap, p_cap = stats.spearmanr(cap["DistanceToTrainStation_km"], cap["NumberOfApprovedPlaces"])
    hrs = df.dropna(subset=["WeeklyHours"])
    hrs = hrs[~hrs["train_dist_outlier"] & hrs["WeeklyHours"].between(1, 100)]
    rho_hrs, p_hrs = stats.spearmanr(hrs["DistanceToTrainStation_km"], hrs["WeeklyHours"])

    ymax = max(props.max() * 1.3, 0.05)
    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(labels, props.reindex(labels).values, color=CAT["blue"], width=0.6, edgecolor=SURFACE, linewidth=1.5)
    for bar, lbl in zip(bars, labels):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005, f"{bar.get_height():.0%}",
                ha="center", fontsize=9, color=INK_PRIMARY)
        ax.text(bar.get_x() + bar.get_width() / 2, -0.13 * ymax, f"n={counts[lbl]:,}",
                ha="center", fontsize=7.5, color=INK_MUTED)
    ax.set_ylim(0, ymax)
    ax.set_ylabel("Share rated 'Exceeding NQS'")
    ax.set_title("Longer opening hours track with (slightly) lower quality",
                 fontsize=12.5, fontweight="bold", color=INK_PRIMARY, loc="left", pad=14)
    ax.text(0.99, 0.97,
            f"Weekly hours vs rating: Spearman ρ = {rho:.3f} (p = {pval:.2g}, n={len(d):,})\n"
            f"Transport distance vs capacity: ρ = {rho_cap:.3f} (p = {p_cap:.2g})\n"
            f"Transport distance vs weekly hours: ρ = {rho_hrs:.3f} (p = {p_hrs:.2g})\n"
            "Both effect sizes are negligible: transport accessibility isn't a\n"
            "meaningful lever for capacity or opening hours, even where p < .05.",
            transform=ax.transAxes, ha="right", va="top", fontsize=8, color=INK_SECONDARY,
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#f9f9f7", edgecolor=GRIDLINE))
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(BASELINE); ax.spines["bottom"].set_color(BASELINE)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "13_hours_vs_quality.png", dpi=200)
    plt.close(fig)
    return {
        "hours_quality_spearman_rho": round(float(rho), 4),
        "hours_quality_spearman_p": float(pval),
        "transport_capacity_spearman_rho": round(float(rho_cap), 4),
        "transport_hours_spearman_rho": round(float(rho_hrs), 4),
        "transport_hours_spearman_p": float(p_hrs),
    }


def main():
    df = classify_urban_rural(load_clean())
    df = add_operational_fields(df)

    summary = {}
    if SUMMARY_PATH.exists():
        summary = json.loads(SUMMARY_PATH.read_text())

    urban_rural_medians = df.groupby("UrbanRural")["NumberOfApprovedPlaces"].median()
    summary.update(chart_capacity_by_type(df, urban_rural_medians))
    summary.update(chart_operating_pattern(df))
    summary.update(chart_approval_trend(df))
    summary.update(chart_hours_vs_quality(df))

    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=2, default=str))
    print(f"\nFigures written to {FIG_DIR}/")


if __name__ == "__main__":
    main()

"""
Operational Trends Analysis stream for the ACECQA education & care
services dataset.

Business questions this answers for ACECQA:
  - How big are services, and does that vary by type or by urban/rural
    location? Does size predict whether a service meets the standard?
  - Is the sector still growing, and is that growth genuine or an
    artifact of the 2012 National Quality Framework rollout? Does
    approval cohort predict non-compliance?
  - Do longer opening hours associate with non-compliance — and does
    transport accessibility influence capacity or hours at all?

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
SOS_ORDER = ["Major Urban", "Other Urban", "Bounded Locality", "Rural Balance"]

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


def chart_capacity_by_type(df: pd.DataFrame, sos_medians: pd.Series) -> dict:
    # Family Day Care excluded: capacity is recorded per individually-
    # registered educator across a scheme, not as a single site limit, so
    # NumberOfApprovedPlaces is populated for only 2 of 417 FDC services -
    # not enough to report a meaningful median.
    d = df[~df["PrimaryServiceType"].isin(["Other", "Family Day Care"])].copy()
    d = d.dropna(subset=["NumberOfApprovedPlaces"])
    d = d[d["OverallRating"].notna()]
    d["OverallRating"] = d["OverallRating"].astype(str)
    d = d[d["OverallRating"] != NOT_YET_ASSESSED]
    d["BelowStandard"] = d["OverallRating"].isin(
        ["Working Towards NQS", "Significant Improvement Required"]
    ).astype(int)

    # Quantile bins (not fixed cutoffs) so each bin has enough services for
    # a reliable rate and the labels show the real capacity range.
    d["cap_bin"], edges = pd.qcut(d["NumberOfApprovedPlaces"], q=5, retbins=True, duplicates="drop")
    labels = [f"{int(edges[i])}-{int(edges[i + 1])}" for i in range(len(edges) - 1)]
    d["cap_bin"] = pd.qcut(d["NumberOfApprovedPlaces"], q=5, labels=labels, duplicates="drop")
    props = d.groupby("cap_bin", observed=True)["BelowStandard"].mean()
    counts = d["cap_bin"].value_counts().reindex(labels)

    rho, pval = stats.spearmanr(d["NumberOfApprovedPlaces"], d["BelowStandard"])

    ymax = max(props.max() * 1.3, 0.05)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    bars = ax.bar(labels, props.reindex(labels).values, color=CAT["blue"], width=0.6, edgecolor=SURFACE, linewidth=1.5)
    for bar, lbl in zip(bars, labels):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.004, f"{bar.get_height():.1%}",
                ha="center", fontsize=9, color=INK_PRIMARY, fontweight="bold")
        ax.text(bar.get_x() + bar.get_width() / 2, -0.13 * ymax, f"n={counts[lbl]:,}",
                ha="center", fontsize=7.5, color=INK_MUTED)
    ax.set_ylim(0, ymax)
    ax.set_xlabel("Approved places (quintile bins)")
    ax.set_ylabel("Share rated below the NQS standard")
    ax.set_title("Does service size predict whether it meets the standard? No.",
                 fontsize=12.5, fontweight="bold", color=INK_PRIMARY, loc="left", pad=14)
    sos_line = "  |  ".join(f"{cat}: {sos_medians[cat]:.0f}" for cat in SOS_ORDER)
    ax.text(0.99, 0.97,
            f"Capacity vs non-compliance: Spearman ρ = {rho:.3f} (p = {pval:.2g}, n={len(d):,})\n"
            "Not statistically significant - essentially zero relationship\n"
            "across a 5x range in capacity. A rural service doesn't need\n"
            "city-sized capacity to meet the standard, and a large centre\n"
            "is no safer bet either.\n"
            f"Median places by area: {sos_line}",
            transform=ax.transAxes, ha="right", va="top", fontsize=8, color=INK_SECONDARY,
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#f9f9f7", edgecolor=GRIDLINE))
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(BASELINE); ax.spines["bottom"].set_color(BASELINE)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "11_capacity_by_type.png", dpi=200)
    plt.close(fig)
    out = {f"median_places_{cat.lower().replace(' ', '_')}": round(float(sos_medians[cat]), 1) for cat in SOS_ORDER}
    out["capacity_noncompliance_spearman_rho"] = round(float(rho), 4)
    out["capacity_noncompliance_spearman_p"] = float(pval)
    out["noncompliance_pct_smallest_capacity_bin"] = round(float(props.iloc[0]) * 100, 1)
    out["noncompliance_pct_largest_capacity_bin"] = round(float(props.iloc[-1]) * 100, 1)
    return out


def chart_approval_trend(df: pd.DataFrame) -> dict:
    d = df[df["ApprovalYear"].between(2006, 2024)]  # drop the handful of pre-2006 / 2025-partial-year points
    by_year = d.groupby("ApprovalYear").size()

    # The real payoff question: does WHEN a service was approved relate to
    # its quality today? Cohorts, not raw year, since individual-year
    # samples get noisy - "2012" is kept separate as the NQF bulk-transfer
    # cohort (mostly long-established services, not new ones, despite the
    # approval date).
    rated = d[d["OverallRating"].notna()].copy()
    rated["OverallRating"] = rated["OverallRating"].astype(str)
    rated = rated[rated["OverallRating"] != NOT_YET_ASSESSED]
    bins = [2005, 2012, 2013, 2016, 2019, 2025]
    labels = ["pre-2012", "2012", "2013-15", "2016-18", "2019+"]
    rated["cohort"] = pd.cut(rated["ApprovalYear"], bins=bins, labels=labels, right=False)
    cohort_noncompliance = rated.groupby("cohort", observed=True)["OverallRating"].apply(
        lambda s: s.isin(["Working Towards NQS", "Significant Improvement Required"]).mean()
    )
    cohort_counts = rated["cohort"].value_counts().reindex(labels)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.2))

    colors = [CAT["red"] if y == 2012 else CAT["blue"] for y in by_year.index]
    ax1.bar(by_year.index, by_year.values, color=colors, width=0.7)
    ax1.annotate(
        "2012: NQF commenced -\nexisting services bulk-\ntransferred, not new\nopenings",
        xy=(2012, by_year.loc[2012]), xytext=(2013.3, by_year.loc[2012] * 0.85),
        fontsize=8, color=INK_SECONDARY, arrowprops=dict(arrowstyle="->", color=INK_MUTED),
    )
    ax1.set_ylabel("Services approved")
    ax1.set_title("Services approved per year", fontsize=12, fontweight="bold", color=INK_PRIMARY, loc="left", pad=12)
    for spine in ["top", "right"]:
        ax1.spines[spine].set_visible(False)
    ax1.spines["left"].set_color(BASELINE); ax1.spines["bottom"].set_color(BASELINE)

    bar_colors = [CAT["red"] if lbl == "2012" else CAT["blue"] for lbl in labels]
    ymax2 = max(cohort_noncompliance.max() * 100 * 1.25, 5)
    bars2 = ax2.bar(labels, (cohort_noncompliance.reindex(labels) * 100).values, color=bar_colors, width=0.6)
    for bar, lbl in zip(bars2, labels):
        h = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width() / 2, h + 0.4, f"{h:.1f}%", ha="center", fontsize=9)
        ax2.text(bar.get_x() + bar.get_width() / 2, -0.13 * ymax2, f"n={cohort_counts[lbl]:,}",
                 ha="center", fontsize=7.5, color=INK_MUTED)
    ax2.set_ylim(0, ymax2)
    ax2.set_ylabel("Share rated below the NQS standard")
    ax2.set_title("...and newer services are more likely to fall short", fontsize=12, fontweight="bold",
                  color=INK_PRIMARY, loc="left", pad=12)
    ax2.text(0.98, 0.95, "red = NQF bulk-transfer\ncohort, not new services",
              transform=ax2.transAxes, ha="right", va="top", fontsize=7.5, color=INK_MUTED)
    for spine in ["top", "right"]:
        ax2.spines[spine].set_visible(False)
    ax2.spines["left"].set_color(BASELINE); ax2.spines["bottom"].set_color(BASELINE)

    fig.suptitle("Approval-date data quality trap, and the real compliance-relevant signal underneath it",
                 fontsize=12.5, fontweight="bold", color=INK_PRIMARY, x=0.02, ha="left")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(FIG_DIR / "12_approval_trend.png", dpi=200)
    plt.close(fig)

    post_2013 = d[d["ApprovalYear"] >= 2013]
    trend_years = post_2013.groupby("ApprovalYear").size()
    return {
        "approvals_2012_nqf_spike": int(by_year.loc[2012]),
        "approvals_2024": int(trend_years.get(2024, 0)),
        "approvals_2014": int(trend_years.get(2014, 0)),
        "noncompliance_pct_pre2012_cohort": round(float(cohort_noncompliance["pre-2012"]) * 100, 1),
        "noncompliance_pct_2019plus_cohort": round(float(cohort_noncompliance["2019+"]) * 100, 1),
    }


def chart_hours_vs_quality(df: pd.DataFrame) -> dict:
    d = df[df["OverallRating"].notna() & df["WeeklyHours"].notna()].copy()
    d["OverallRating"] = d["OverallRating"].astype(str)
    d = d[d["OverallRating"] != NOT_YET_ASSESSED]
    d = d[d["WeeklyHours"].between(1, 100)]  # exclude the near-zero and near-168h data artifacts
    d["BelowStandard"] = d["OverallRating"].isin(
        ["Working Towards NQS", "Significant Improvement Required"]
    ).astype(int)

    bins = [0, 45, 50, 55, 60, 100]
    labels = ["<45h", "45-50h", "50-55h", "55-60h", "60h+"]
    d["hours_bin"] = pd.cut(d["WeeklyHours"], bins=bins, labels=labels)
    props = d.groupby("hours_bin", observed=True)["BelowStandard"].mean()
    counts = d["hours_bin"].value_counts().reindex(labels)

    rho, pval = stats.spearmanr(d["WeeklyHours"], d["BelowStandard"])

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
    ax.set_ylabel("Share rated below the NQS standard")
    ax.set_title("Services open the longest hours are the most likely to fall below standard",
                 fontsize=12.5, fontweight="bold", color=INK_PRIMARY, loc="left", pad=14)
    ax.text(0.02, 0.97,
            f"Weekly hours vs non-compliance: Spearman ρ = {rho:.3f} (p = {pval:.2g}, n={len(d):,})\n"
            "The rank correlation is small, but the gap between bins is real:\n"
            "non-compliance more than doubles from the shortest to the\n"
            "longest opening-hours band.\n"
            f"Transport distance vs capacity: ρ = {rho_cap:.3f} (p = {p_cap:.2g})\n"
            f"Transport distance vs weekly hours: ρ = {rho_hrs:.3f} (p = {p_hrs:.2g})\n"
            "Both transport effect sizes are negligible: transport accessibility\n"
            "isn't a meaningful lever for capacity or opening hours, even\n"
            "where p < .05.",
            transform=ax.transAxes, ha="left", va="top", fontsize=8, color=INK_SECONDARY,
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#f9f9f7", edgecolor=GRIDLINE))
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(BASELINE); ax.spines["bottom"].set_color(BASELINE)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "13_hours_vs_quality.png", dpi=200)
    plt.close(fig)
    return {
        "hours_noncompliance_spearman_rho": round(float(rho), 4),
        "hours_noncompliance_spearman_p": float(pval),
        "noncompliance_pct_shortest_hours_bin": round(float(props.iloc[0]) * 100, 1),
        "noncompliance_pct_longest_hours_bin": round(float(props.iloc[-1]) * 100, 1),
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

    sos_medians = df.groupby("SOS_Category")["NumberOfApprovedPlaces"].median()
    summary.update(chart_capacity_by_type(df, sos_medians))
    summary.update(chart_approval_trend(df))
    summary.update(chart_hours_vs_quality(df))

    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=2, default=str))
    print(f"\nFigures written to {FIG_DIR}/")


if __name__ == "__main__":
    main()

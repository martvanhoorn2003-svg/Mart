"""
Service Quality Analysis stream for the ACECQA education & care services
dataset.

Business question this answers for ACECQA:
  - How does quality (NQS ratings) vary by state and by service type -
    where should the regulator focus improvement support?
  - Which of the seven Quality Areas drags each state's rating down?
  - Does distance to public transport help explain quality, or is it a
    red herring policymakers should stop worrying about?

Service-type note: the dataset carries both a coarse ServiceType column
(Centre-Based Care / Family Day Care) and seven non-exclusive detailed
flags (a centre can be "Yes" on more than one, e.g. Long Day Care +
Vacation Care). For the by-type quality comparison we derive ONE primary
label per service with a fixed priority order (Family Day Care > Long Day
Care > Preschool standalone > Preschool school-based > OSHC > Other) so
every service is counted exactly once and the chart isn't double-counting
services that tick multiple flags.

Outputs PNGs to outputs/figures/ and a JSON of headline stats to
outputs/summary_stats.json for use in the presentation slides.

Run: python src/quality_analysis.py
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch
from scipy import stats

from clean import NOT_YET_ASSESSED, QUALITY_AREA_LABELS, load_clean, rated_only

FIG_DIR = Path("outputs/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)
SUMMARY_PATH = Path("outputs/summary_stats.json")
AU_STATES_GEOJSON = Path("data/external/au_states.geojson")

# --- dataviz skill palette (see .claude skill "dataviz" / references/palette.md) ---
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
# Sequential blue ramp, light -> dark (step 100 .. 700)
SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#1c5cab", "#104281"]

RATING_ORDER_SUBSTANTIVE = [
    "Significant Improvement Required",
    "Working Towards NQS",
    "Meeting NQS",
    "Exceeding NQS",
    "Excellent",
]
# One sequential step per substantive tier (skip the lightest step, reserved
# for "not yet assessed" in charts that show it).
RATING_COLORS = dict(zip(RATING_ORDER_SUBSTANTIVE, SEQ_BLUE[2:]))
RATING_COLORS[NOT_YET_ASSESSED] = "#e1e0d9"  # gridline gray: "no signal yet", not a tier

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": BASELINE,
    "axes.labelcolor": INK_SECONDARY,
    "text.color": INK_PRIMARY,
    "xtick.color": INK_SECONDARY,
    "ytick.color": INK_SECONDARY,
    "axes.grid": False,
    "font.family": "sans-serif",
    "font.size": 11,
})


def primary_service_type(df: pd.DataFrame) -> pd.Series:
    conditions = [
        df["ServiceType"].eq("Family Day Care"),
        df["Long Day Care"].eq(True),
        df["Preschool/Kindergarten - Stand alone"].eq(True),
        df["Preschool/Kindergarten - Part of a School"].eq(True),
        df[[
            "Outside school Hours Care - After School",
            "Outside school Hours Care - Before School",
            "Outside school Hours Care - Vacation Care",
        ]].any(axis=1),
    ]
    choices = [
        "Family Day Care",
        "Long Day Care",
        "Preschool (standalone)",
        "Preschool (school-based)",
        "Outside School Hours Care",
    ]
    return pd.Series(np.select(conditions, choices, default="Other"), index=df.index)


def _stacked_bar(ax, props: pd.DataFrame, order: list[str], colors: dict, value_fmt="{:.0%}"):
    """props: rows = groups (already sorted), cols = rating categories (0-1 shares)."""
    left = np.zeros(len(props))
    y = np.arange(len(props))
    for cat in order:
        vals = props[cat].to_numpy()
        ax.barh(y, vals, left=left, height=0.62, color=colors[cat],
                edgecolor=SURFACE, linewidth=1.2, label=cat)
        # direct label only on segments wide enough to read
        for i, v in enumerate(vals):
            if v >= 0.08:
                ax.text(left[i] + v / 2, y[i], value_fmt.format(v), ha="center", va="center",
                        fontsize=8.5, color="white" if colors[cat] not in (RATING_COLORS[NOT_YET_ASSESSED],) else INK_PRIMARY)
        left += vals
    ax.set_yticks(y)
    ax.set_yticklabels(props.index)
    ax.set_xlim(0, 1)
    ax.set_xticks([0, .25, .5, .75, 1.0])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.invert_yaxis()
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.tick_params(left=False)


def chart_rating_by_state(df: pd.DataFrame) -> dict:
    rated = df[df["State"].notna()].copy()
    rated["OverallRating"] = rated["OverallRating"].astype(str)
    order = [NOT_YET_ASSESSED] + RATING_ORDER_SUBSTANTIVE
    props = (
        rated.groupby("State")["OverallRating"]
        .value_counts(normalize=True).unstack(fill_value=0)
        .reindex(columns=order, fill_value=0)
    )
    # sort states by non-compliance (Working Towards + Significant
    # Improvement Required), worst first - consistent with the
    # non-compliance framing used everywhere else in this stream.
    props["_score"] = props["Working Towards NQS"] + props["Significant Improvement Required"]
    props = props.sort_values("_score", ascending=False).drop(columns="_score")

    fig, ax = plt.subplots(figsize=(9, 5.2))
    _stacked_bar(ax, props, order, RATING_COLORS)
    ax.set_title("Overall NQS rating by state, ranked by non-compliance (worst first)",
                 fontsize=13, fontweight="bold", color=INK_PRIMARY, loc="left", pad=14)
    ax.set_xlabel("Share of rated services")
    handles = [Patch(facecolor=RATING_COLORS[c], label=c) for c in order]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.14),
              ncol=3, frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "01_rating_by_state.png", dpi=200)
    plt.close(fig)

    worst, best = props.index[0], props.index[-1]

    def noncompliance_pct(state):
        return round(float(props.loc[state, "Working Towards NQS"] + props.loc[state, "Significant Improvement Required"]) * 100, 1)

    return {
        "best_state": best, "best_state_noncompliance_pct": noncompliance_pct(best),
        "worst_state": worst, "worst_state_noncompliance_pct": noncompliance_pct(worst),
    }


def chart_rating_by_service_type(df: pd.DataFrame) -> dict:
    d = df.copy()
    d["PrimaryServiceType"] = primary_service_type(d)
    d = d[d["PrimaryServiceType"] != "Other"]  # 3 services, not a meaningful group
    d = d[d["OverallRating"].notna()]
    d["OverallRating"] = d["OverallRating"].astype(str)
    d = d[d["OverallRating"] != NOT_YET_ASSESSED]
    order = RATING_ORDER_SUBSTANTIVE
    props = (
        d.groupby("PrimaryServiceType")["OverallRating"]
        .value_counts(normalize=True).unstack(fill_value=0)
        .reindex(columns=order, fill_value=0)
    )
    counts = d["PrimaryServiceType"].value_counts()
    # Ranked by non-compliance, worst first - consistent with Chart 1 and
    # Chart 3's framing (who's actually failing the legal minimum, not who's
    # excelling).
    props["_score"] = props["Working Towards NQS"] + props["Significant Improvement Required"]
    props = props.sort_values("_score", ascending=False).drop(columns="_score")
    props.index = [f"{i}  (n={counts[i]:,})" for i in props.index]

    fig, ax = plt.subplots(figsize=(9, 5.0))
    _stacked_bar(ax, props, order, RATING_COLORS)
    ax.set_title("Overall NQS rating by primary service type,\nranked by non-compliance (worst first)",
                 fontsize=13, fontweight="bold", color=INK_PRIMARY, loc="left", pad=14)
    ax.set_xlabel("Share of rated services (assessed services only)")
    handles = [Patch(facecolor=RATING_COLORS[c], label=c) for c in order]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.16),
              ncol=2, frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "02_rating_by_service_type.png", dpi=200)
    plt.close(fig)
    return {"service_type_counts": counts.to_dict()}


def chart_quality_area_heatmap(df: pd.DataFrame) -> dict:
    d = df[df["State"].notna()].copy()
    qa_cols = list(QUALITY_AREA_LABELS.keys())
    rows = []
    for state, g in d.groupby("State"):
        row = {}
        for col in qa_cols:
            s = g[col].astype(str)
            s = s[(s != "nan") & (s != NOT_YET_ASSESSED)]
            # Non-compliance: rated below the NQS standard (Working Towards
            # NQS or Significant Improvement Required) - the areas actively
            # failing to meet the National Law, not just short of "Exceeding".
            row[QUALITY_AREA_LABELS[col]] = (
                s.isin(["Working Towards NQS", "Significant Improvement Required"]).mean() if len(s) else np.nan
            )
        rows.append(pd.Series(row, name=state))
    heat = pd.DataFrame(rows)
    # order states by overall mean non-compliance, worst first
    heat = heat.loc[heat.mean(axis=1).sort_values(ascending=False).index]

    fig, ax = plt.subplots(figsize=(9.5, 5))
    im = ax.imshow(heat.values, cmap="Reds", vmin=0, vmax=heat.values.max(), aspect="auto")
    ax.set_xticks(range(len(heat.columns)))
    ax.set_xticklabels(heat.columns, rotation=35, ha="right", fontsize=9)
    ax.set_yticks(range(len(heat.index)))
    ax.set_yticklabels(heat.index)
    for i in range(heat.shape[0]):
        for j in range(heat.shape[1]):
            v = heat.values[i, j]
            txt_color = "white" if v > heat.values.max() * 0.6 else INK_PRIMARY
            ax.text(j, i, f"{v:.0%}", ha="center", va="center", fontsize=8.5, color=txt_color)
    for spine in ax.spines.values():
        spine.set_visible(False)
    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cbar.set_label("Share NOT yet meeting NQS", color=INK_SECONDARY, fontsize=9)
    ax.set_title("Where non-compliance concentrates: % rated below NQS standard, by Quality Area",
                 fontsize=12.5, fontweight="bold", color=INK_PRIMARY, loc="left", pad=14)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "03_quality_area_heatmap.png", dpi=200)
    plt.close(fig)

    weakest_area = heat.mean(axis=0).idxmax()  # highest non-compliance
    strongest_area = heat.mean(axis=0).idxmin()  # lowest non-compliance
    return {"weakest_quality_area_nationally": weakest_area, "strongest_quality_area_nationally": strongest_area}


def chart_spatial_map(df: pd.DataFrame) -> dict:
    d = df[df["lon"].notna() & df["lat"].notna() & ~df["geocode_suspect"]].copy()
    d["OverallRating"] = d["OverallRating"].astype(str)
    tier_colors = {
        "Significant Improvement Required": CAT["red"],
        "Working Towards NQS": CAT["orange"],
        "Meeting NQS": SEQ_BLUE[2],
        "Exceeding NQS": SEQ_BLUE[5],
        "Excellent": CAT["violet"],
    }
    states = gpd.read_file(AU_STATES_GEOJSON)

    fig, ax = plt.subplots(figsize=(9, 8))
    states.boundary.plot(ax=ax, color=BASELINE, linewidth=0.6)
    states.plot(ax=ax, color="#f9f9f7", edgecolor="none", zorder=0)

    plot_order = ["Meeting NQS", "Exceeding NQS", "Working Towards NQS",
                  "Significant Improvement Required", "Excellent"]
    for tier in plot_order:
        sub = d[d["OverallRating"] == tier]
        if len(sub) == 0:
            continue
        ax.scatter(sub["lon"], sub["lat"], s=6, alpha=0.55, linewidths=0,
                   color=tier_colors[tier], label=f"{tier} (n={len(sub):,})")

    ax.set_xlim(112, 155)
    ax.set_ylim(-44, -9)
    ax.set_aspect(1.4)
    ax.set_xticks([]); ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title("Approved services across Australia, by overall NQS rating",
                 fontsize=13, fontweight="bold", color=INK_PRIMARY, loc="left", pad=10)
    leg = ax.legend(loc="lower left", frameon=False, fontsize=8.5, markerscale=2.2)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "04_spatial_ratings_map.png", dpi=200)
    plt.close(fig)
    return {"n_mapped": int(len(d)), "n_excluded_suspect_geocode": int(df["geocode_suspect"].sum())}


def chart_transport_vs_quality(df: pd.DataFrame) -> dict:
    d = rated_only(df["OverallRating"].dropna()).index
    sub = df.loc[d].copy()
    sub["OverallRating"] = sub["OverallRating"].astype(str)
    # The question is whether poor transport access has a NEGATIVE impact
    # on quality, so the outcome plotted is the share falling BELOW the
    # NQS standard (Working Towards NQS or Significant Improvement
    # Required) - a direct "at risk" measure - rather than the share
    # exceeding it.
    sub["BelowStandard"] = sub["OverallRating"].isin(
        ["Working Towards NQS", "Significant Improvement Required"]
    ).astype(int)

    # Torres Strait / very remote outliers (>100km, flagged in cleaning)
    # excluded here: they're real but would compress every other bin onto
    # one pixel and are a policy story of their own (see spatial map).
    sub_clean = sub[~sub["train_dist_outlier"]]
    n_excluded = int(sub["train_dist_outlier"].sum())

    bins = [0, 0.5, 1, 2, 5, 10, 100]
    labels = ["<0.5km", "0.5-1km", "1-2km", "2-5km", "5-10km", "10-100km"]
    sub_clean["dist_bin"] = pd.cut(sub_clean["DistanceToTrainStation_km"], bins=bins, labels=labels)
    props = sub_clean.groupby("dist_bin", observed=True)["BelowStandard"].mean()
    counts = sub_clean["dist_bin"].value_counts().reindex(labels)

    rho, pval = stats.spearmanr(sub_clean["DistanceToTrainStation_km"], sub_clean["BelowStandard"])

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(labels, props.reindex(labels).values, color=CAT["red"], width=0.6,
                  edgecolor=SURFACE, linewidth=1.5)
    for i, (bar, lbl) in enumerate(zip(bars, labels)):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.003,
                f"{bar.get_height():.1%}", ha="center", fontsize=9, color=INK_PRIMARY)
        ax.text(bar.get_x() + bar.get_width() / 2, -0.012, f"n={counts[lbl]:,}",
                ha="center", fontsize=7.5, color=INK_MUTED)
    ymax = max(props.max() * 1.3, 0.05)
    ax.set_ylim(0, ymax)
    ax.set_ylabel("Share rated below the NQS standard")
    ax.set_title("Does distance from transport hurt quality? Share rated 'Working Towards'\nor 'Significant Improvement Required', by distance to nearest train station",
                 fontsize=12.5, fontweight="bold", color=INK_PRIMARY, loc="left", pad=14)
    ax.text(0.02, 0.97, f"Spearman ρ = {rho:.3f}  (p = {pval:.3g}, n={len(sub_clean):,})\n"
                        "A small but real effect: services furthest from transport\n"
                        "are somewhat more likely to fall below standard - not a\n"
                        "dominant driver of quality, but not nothing either.",
            transform=ax.transAxes, ha="left", va="top", fontsize=8.5, color=INK_SECONDARY,
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#f9f9f7", edgecolor=GRIDLINE))
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(BASELINE)
    ax.spines["bottom"].set_color(BASELINE)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "05_transport_vs_quality.png", dpi=200)
    plt.close(fig)
    return {
        "transport_belowstandard_spearman_rho": round(float(rho), 4),
        "transport_belowstandard_spearman_p": float(pval),
        "belowstandard_pct_closest_bin": round(float(props.iloc[0]) * 100, 1),
        "belowstandard_pct_farthest_bin": round(float(props.iloc[-1]) * 100, 1),
        "n_excluded_remote_outliers": n_excluded,
    }


def main():
    df = load_clean()
    summary = {}
    if SUMMARY_PATH.exists():
        summary = json.loads(SUMMARY_PATH.read_text())
    summary["n_services_total"] = int(len(df))
    summary.update(chart_rating_by_state(df))
    summary.update(chart_rating_by_service_type(df))
    summary.update(chart_quality_area_heatmap(df))
    summary.update(chart_spatial_map(df))
    summary.update(chart_transport_vs_quality(df))

    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=2, default=str))
    print(f"\nFigures written to {FIG_DIR}/")


if __name__ == "__main__":
    main()

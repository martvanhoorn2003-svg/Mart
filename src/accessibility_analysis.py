"""
Accessibility & Coverage Analysis stream for the ACECQA education & care
services dataset.

Business questions this answers for ACECQA:
  - Does distance from transport push more services below the NQS
    compliance standard - and does that hold in every state?
  - Does non-compliance concentrate in rural areas specifically, and
    which state x area-type combinations are worst?
  - Where geographically are families most underserved (furthest from
    an alternative service), and does that coverage gap actually
    predict non-compliance, or are they separate problems?

Urban/rural classification: ABS Section of State (SOS) 2021, joined by
point-in-polygon on each service's own coordinates (see src/urban_rural.py
for the method and why SOS was chosen over Remoteness Areas).

Outputs PNGs to outputs/figures/ and appends to outputs/summary_stats.json.

Run: python src/accessibility_analysis.py
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
from scipy.spatial import cKDTree

from clean import NOT_YET_ASSESSED, load_clean
from urban_rural import classify_urban_rural

FIG_DIR = Path("outputs/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)
SUMMARY_PATH = Path("outputs/summary_stats.json")
AU_STATES_GEOJSON = Path("data/external/au_states.geojson")

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
    "Significant Improvement Required",
    "Working Towards NQS",
    "Meeting NQS",
    "Exceeding NQS",
    "Excellent",
]
RATING_COLORS = dict(zip(RATING_ORDER_SUBSTANTIVE, SEQ_BLUE[2:]))

SOS_ORDER = ["Major Urban", "Other Urban", "Bounded Locality", "Rural Balance"]
SOS_COLORS = {
    "Major Urban": SEQ_BLUE[5], "Other Urban": SEQ_BLUE[3],
    "Bounded Locality": CAT["orange"], "Rural Balance": CAT["red"],
}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "axes.edgecolor": BASELINE,
    "axes.labelcolor": INK_SECONDARY, "text.color": INK_PRIMARY,
    "xtick.color": INK_SECONDARY, "ytick.color": INK_SECONDARY,
    "axes.grid": False, "font.family": "sans-serif", "font.size": 11,
})


def add_nearest_service_distance(df: pd.DataFrame) -> pd.DataFrame:
    """Median distance to the nearest OTHER service, per service (km).

    A direct measure of coverage: how far would a family need to travel
    for an alternative service if their nearest one were unavailable or
    full. More meaningful for "where are services thin on the ground"
    than a land-area density, which is dominated by uninhabited land in
    a country this size and geography.
    """
    d = df.copy()
    pts = gpd.GeoDataFrame(
        d, geometry=gpd.points_from_xy(d["lon"], d["lat"]), crs="EPSG:4326"
    ).to_crs("EPSG:3577")  # GDA2020 / Australian Albers - metres
    coords = np.vstack([pts.geometry.x, pts.geometry.y]).T
    dist, _ = cKDTree(coords).query(coords, k=2)  # k=1 is the point itself
    d["nearest_service_km"] = dist[:, 1] / 1000
    return d


MIN_CELL_N = 15  # cells below this are masked - too few services for a reliable rate


def _noncompliance_grid(df: pd.DataFrame, row_col: str, col_col: str, col_order: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Share of services rated below the NQS standard, gridded by two dimensions."""
    d = df[df[row_col].notna() & df[col_col].notna() & df["OverallRating"].notna()].copy()
    d["OverallRating"] = d["OverallRating"].astype(str)
    d = d[d["OverallRating"] != NOT_YET_ASSESSED]
    d["BelowStandard"] = d["OverallRating"].isin(["Working Towards NQS", "Significant Improvement Required"]).astype(int)
    grid = d.groupby([row_col, col_col])["BelowStandard"].mean().unstack().reindex(columns=col_order)
    counts = d.groupby([row_col, col_col]).size().unstack().reindex(columns=col_order)
    grid = grid.where(counts >= MIN_CELL_N)
    return grid, counts


def _plot_noncompliance_heatmap(grid: pd.DataFrame, counts: pd.DataFrame, title: str, subtitle: str, fname: str):
    grid = grid.loc[grid.mean(axis=1, skipna=True).sort_values(ascending=False).index]  # worst state first
    counts = counts.loc[grid.index]
    vals = grid.values.astype(float)

    fig, ax = plt.subplots(figsize=(9, 5.3))
    im = ax.imshow(np.ma.masked_invalid(vals), cmap="Reds", vmin=0, aspect="auto")
    ax.set_xticks(range(len(grid.columns))); ax.set_xticklabels(grid.columns, rotation=20, ha="right")
    ax.set_yticks(range(len(grid.index))); ax.set_yticklabels(grid.index)
    vmax = np.nanmax(vals) if np.isfinite(vals).any() else 1.0
    for i in range(vals.shape[0]):
        for j in range(vals.shape[1]):
            v = vals[i, j]
            if np.isnan(v):
                ax.text(j, i, "n/a", ha="center", va="center", fontsize=7.5, color=INK_MUTED)
                continue
            txt_color = "white" if v > vmax * 0.55 else INK_PRIMARY
            n = counts.values[i, j]
            ax.text(j, i, f"{v:.0%}\n(n={n:.0f})", ha="center", va="center", fontsize=8, color=txt_color)
    for spine in ax.spines.values():
        spine.set_visible(False)
    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cbar.set_label("Share rated below the NQS standard", color=INK_SECONDARY, fontsize=9)
    ax.set_title(title, fontsize=12.5, fontweight="bold", color=INK_PRIMARY, loc="left", pad=28)
    ax.text(0, 1.06, subtitle, transform=ax.transAxes, fontsize=9, color=INK_SECONDARY)
    fig.tight_layout()
    fig.savefig(FIG_DIR / fname, dpi=200)
    plt.close(fig)
    return grid


def chart_transport_by_urban_rural(df: pd.DataFrame) -> dict:
    # Does distance from transport push MORE services below the NQS
    # standard - and does that hold in every state, or only some?
    d = df[~df["train_dist_outlier"]].copy()
    bins = [0, 2, 5, 100]
    labels = ["<2km", "2-5km", "5km+"]
    d["dist_bin"] = pd.cut(d["DistanceToTrainStation_km"], bins=bins, labels=labels)

    grid, counts = _noncompliance_grid(d, "State", "dist_bin", labels)
    grid = _plot_noncompliance_heatmap(
        grid, counts,
        "Does distance from transport push more services below standard? State by state",
        "Share of services rated 'Working Towards NQS' or 'Significant Improvement Required', by distance to nearest train station",
        "06_transport_by_urban_rural.png",
    )
    worst_cell = grid.stack().idxmax()
    return {
        "worst_state_transport_noncompliance_cell": f"{worst_cell[0]} / {worst_cell[1]}",
        "worst_state_transport_noncompliance_pct": round(float(grid.stack().max()) * 100, 1),
    }


def chart_rating_by_urban_rural(df: pd.DataFrame) -> dict:
    # Same question, but by area type (Major Urban -> Rural Balance)
    # instead of raw transport distance - does non-compliance concentrate
    # in rural areas in every state, or is it state-specific?
    grid, counts = _noncompliance_grid(df, "State", "SOS_Category", SOS_ORDER)
    grid = _plot_noncompliance_heatmap(
        grid, counts,
        "Where does non-compliance concentrate: urban vs rural? State by state",
        "Share of services rated 'Working Towards NQS' or 'Significant Improvement Required', by ABS Section of State",
        "07_rating_by_urban_rural.png",
    )
    worst_cell = grid.stack().idxmax()
    out = {
        "worst_state_sos_noncompliance_cell": f"{worst_cell[0]} / {worst_cell[1]}",
        "worst_state_sos_noncompliance_pct": round(float(grid.stack().max()) * 100, 1),
    }
    for cat in SOS_ORDER:
        if cat in grid.columns:
            out[f"national_noncompliance_{cat.lower().replace(' ', '_')}_pct"] = round(
                float(grid[cat].mean(skipna=True)) * 100, 1
            )
    return out


def chart_spatial_sos(df: pd.DataFrame) -> dict:
    d = df[df["lon"].notna() & df["lat"].notna() & ~df["geocode_suspect"] & df["SOS_Category"].notna()]
    states = gpd.read_file(AU_STATES_GEOJSON)

    fig, ax = plt.subplots(figsize=(9, 8))
    states.boundary.plot(ax=ax, color=BASELINE, linewidth=0.6)
    states.plot(ax=ax, color="#f9f9f7", edgecolor="none", zorder=0)

    for cat in SOS_ORDER:
        sub = d[d["SOS_Category"] == cat]
        if len(sub) == 0:
            continue
        s = 5 if cat in ("Major Urban", "Other Urban") else 16
        ax.scatter(sub["lon"], sub["lat"], s=s, alpha=0.7, linewidths=0,
                   color=SOS_COLORS[cat], label=f"{cat} (n={len(sub):,})", zorder=3 if s > 5 else 2)

    ax.set_xlim(112, 155); ax.set_ylim(-44, -9); ax.set_aspect(1.4)
    ax.set_xticks([]); ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title("Services by ABS Section of State: urban centres vs rural areas",
                 fontsize=13, fontweight="bold", color=INK_PRIMARY, loc="left", pad=10)
    ax.legend(loc="lower left", frameon=False, fontsize=8.5, markerscale=1.6)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "08_spatial_urban_rural.png", dpi=200)
    plt.close(fig)
    return {}


def chart_coverage_gaps(df: pd.DataFrame) -> dict:
    d = add_nearest_service_distance(df)
    d = d[d["State"].notna() & d["SOS_Category"].notna()]

    gap_grid = d.groupby(["State", "SOS_Category"])["nearest_service_km"].median().unstack().reindex(columns=SOS_ORDER)
    gap_grid = gap_grid.loc[gap_grid.mean(axis=1, skipna=True).sort_values(ascending=False).index]
    flat_gap = gap_grid.stack()
    worst_gap = flat_gap.idxmax()  # (state, sos) with the biggest coverage gap

    # Direct test: does a bigger coverage gap (nearest OTHER service further
    # away) actually predict non-compliance, cell by cell? One point per
    # state x area-type combination, masked below MIN_CELL_N.
    rated = d[d["OverallRating"].notna()].copy()
    rated["OverallRating"] = rated["OverallRating"].astype(str)
    rated = rated[rated["OverallRating"] != NOT_YET_ASSESSED]
    rated["BelowStandard"] = rated["OverallRating"].isin(["Working Towards NQS", "Significant Improvement Required"]).astype(int)
    cell = rated.groupby(["State", "SOS_Category"]).agg(
        nearest_km=("nearest_service_km", "median"),
        noncompliance=("BelowStandard", "mean"),
        n=("BelowStandard", "size"),
    ).reset_index()
    cell = cell[cell["n"] >= MIN_CELL_N]
    rho, pval = stats.spearmanr(cell["nearest_km"], cell["noncompliance"])

    # The chart's real payoff: is the single worst coverage-gap cell (left
    # panel) ALSO bad on non-compliance (right panel)? Same cell, both axes.
    worst_cell_row = cell[(cell["State"] == worst_gap[0]) & (cell["SOS_Category"] == worst_gap[1])].iloc[0]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    vals = gap_grid.values.astype(float)
    im = ax1.imshow(np.ma.masked_invalid(vals), cmap="Blues", aspect="auto")
    ax1.set_xticks(range(len(gap_grid.columns))); ax1.set_xticklabels(gap_grid.columns, rotation=20, ha="right")
    ax1.set_yticks(range(len(gap_grid.index))); ax1.set_yticklabels(gap_grid.index)
    for i in range(vals.shape[0]):
        for j in range(vals.shape[1]):
            v = vals[i, j]
            if np.isnan(v):
                continue
            txt_color = "white" if v > np.nanmax(vals) * 0.55 else INK_PRIMARY
            ax1.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=8.5, color=txt_color)
    for spine in ax1.spines.values():
        spine.set_visible(False)
    cbar = fig.colorbar(im, ax=ax1, fraction=0.045, pad=0.02)
    cbar.set_label("Median km to nearest other service", color=INK_SECONDARY, fontsize=8.5)
    ax1.set_title("Coverage gap: how far to the next service?", fontsize=11.5, fontweight="bold",
                  color=INK_PRIMARY, loc="left", pad=12)

    state_markers = {s: m for s, m in zip(sorted(cell["State"].unique()),
                     ["o", "s", "^", "D", "v", "P", "X", "*"])}
    for state in sorted(cell["State"].unique()):
        sub = cell[cell["State"] == state]
        ax2.scatter(sub["nearest_km"], sub["noncompliance"] * 100, s=sub["n"] / 3 + 30,
                   marker=state_markers[state], color=CAT["blue"], alpha=0.75, edgecolors=INK_PRIMARY,
                   linewidths=0.4, label=state)
    ax2.set_xscale("log")
    ax2.set_ylim(0, cell["noncompliance"].max() * 100 * 1.3)  # headroom for the annotation
    ax2.annotate(
        f"{worst_cell_row['State']} / {worst_cell_row['SOS_Category']}\n"
        f"(the biggest coverage gap - also\nnon-compliant {worst_cell_row['noncompliance']:.0%} of the time)",
        xy=(worst_cell_row["nearest_km"], worst_cell_row["noncompliance"] * 100),
        xytext=(-70, 25), textcoords="offset points", fontsize=7.5, color=INK_SECONDARY,
        ha="left", arrowprops=dict(arrowstyle="->", color=INK_MUTED, lw=0.8))
    ax2.set_xlabel("Median km to nearest other service (log scale)")
    ax2.set_ylabel("Share below NQS standard")
    ax2.set_title("Does a bigger coverage gap predict non-compliance?", fontsize=11.5, fontweight="bold",
                  color=INK_PRIMARY, loc="left", pad=12)
    ax2.text(0.02, 0.97, f"Spearman ρ = {rho:.3f} (p = {pval:.2g}, n={len(cell)} state×area cells)\n"
                        "No overall relationship: coverage gaps and non-compliance\n"
                        "are largely separate problems, needing separate fixes.",
            transform=ax2.transAxes, ha="left", va="top", fontsize=7.5, color=INK_SECONDARY,
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#f9f9f7", edgecolor=GRIDLINE))
    ax2.legend(loc="lower right", frameon=False, fontsize=7.5, ncol=2, title="state", title_fontsize=7.5)
    for spine in ["top", "right"]:
        ax2.spines[spine].set_visible(False)
    ax2.spines["left"].set_color(BASELINE); ax2.spines["bottom"].set_color(BASELINE)

    fig.suptitle("Where is the next service furthest away, and does that gap predict non-compliance?",
                 fontsize=13, fontweight="bold", color=INK_PRIMARY, x=0.02, ha="left")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(FIG_DIR / "09_coverage_gaps.png", dpi=200)
    plt.close(fig)

    return {
        "most_underserved_state_sos": f"{worst_gap[0]} / {worst_gap[1]}",
        "most_underserved_median_km": round(float(flat_gap.max()), 1),
        "coverage_gap_noncompliance_spearman_rho": round(float(rho), 4),
        "coverage_gap_noncompliance_spearman_p": float(pval),
        "worst_coverage_gap_cell_noncompliance_pct": round(float(worst_cell_row["noncompliance"]) * 100, 1),
    }


def main():
    df = classify_urban_rural(load_clean())

    summary = {}
    if SUMMARY_PATH.exists():
        summary = json.loads(SUMMARY_PATH.read_text())

    summary.update(chart_transport_by_urban_rural(df))
    summary.update(chart_rating_by_urban_rural(df))
    summary.update(chart_spatial_sos(df))
    summary.update(chart_coverage_gaps(df))
    summary["urban_rural_counts"] = df["UrbanRural"].value_counts(dropna=False).to_dict()
    summary["sos_category_counts"] = df["SOS_Category"].value_counts(dropna=False).to_dict()

    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=2, default=str))
    print(f"\nFigures written to {FIG_DIR}/")


if __name__ == "__main__":
    main()

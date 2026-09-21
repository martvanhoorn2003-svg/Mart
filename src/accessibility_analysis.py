"""
Accessibility & Coverage Analysis stream for the ACECQA education & care
services dataset.

Business questions this answers for ACECQA:
  - How much worse is transport access for rural services vs urban ones?
  - Does that urban/rural split show up in quality outcomes too?
  - Where geographically are families most underserved - i.e. where is
    the nearest alternative service furthest away?

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


def chart_transport_by_urban_rural(df: pd.DataFrame) -> dict:
    d = df[df["UrbanRural"].notna()]
    medians = d.groupby("UrbanRural")[["DistanceToTrainStation_km", "DistanceToBusStation_km"]].median()
    medians = medians.reindex(["Urban", "Rural"])

    fig, ax = plt.subplots(figsize=(7.5, 5))
    x = np.arange(2)
    w = 0.32
    ax.bar(x - w / 2, medians["DistanceToTrainStation_km"], width=w, color=CAT["blue"], label="Train station")
    ax.bar(x + w / 2, medians["DistanceToBusStation_km"], width=w, color=CAT["orange"], label="Bus station")
    for i, cat in enumerate(["Urban", "Rural"]):
        ax.text(i - w / 2, medians.loc[cat, "DistanceToTrainStation_km"] + 0.5,
                f"{medians.loc[cat, 'DistanceToTrainStation_km']:.1f}km", ha="center", fontsize=9)
        ax.text(i + w / 2, medians.loc[cat, "DistanceToBusStation_km"] + 0.5,
                f"{medians.loc[cat, 'DistanceToBusStation_km']:.1f}km", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(["Urban", "Rural"])
    ax.set_ylabel("Median distance (km)")
    ax.set_title("Rural services sit far further from public transport",
                 fontsize=13, fontweight="bold", color=INK_PRIMARY, loc="left", pad=14)
    ax.legend(frameon=False, loc="upper left")
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(BASELINE); ax.spines["bottom"].set_color(BASELINE)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "06_transport_by_urban_rural.png", dpi=200)
    plt.close(fig)
    return {
        "rural_median_train_km": round(float(medians.loc["Rural", "DistanceToTrainStation_km"]), 2),
        "urban_median_train_km": round(float(medians.loc["Urban", "DistanceToTrainStation_km"]), 2),
    }


def chart_rating_by_urban_rural(df: pd.DataFrame) -> dict:
    d = df[df["UrbanRural"].notna() & df["OverallRating"].notna()].copy()
    d["OverallRating"] = d["OverallRating"].astype(str)
    d = d[d["OverallRating"] != NOT_YET_ASSESSED]
    props = (
        d.groupby("UrbanRural")["OverallRating"].value_counts(normalize=True)
        .unstack(fill_value=0).reindex(columns=RATING_ORDER_SUBSTANTIVE, fill_value=0)
        .reindex(["Urban", "Rural"])
    )
    counts = d["UrbanRural"].value_counts()
    props.index = [f"{i}  (n={counts[i]:,})" for i in props.index]

    fig, ax = plt.subplots(figsize=(9, 3.2))
    left = np.zeros(len(props))
    y = np.arange(len(props))
    for cat in RATING_ORDER_SUBSTANTIVE:
        vals = props[cat].to_numpy()
        ax.barh(y, vals, left=left, height=0.55, color=RATING_COLORS[cat], edgecolor=SURFACE, linewidth=1.2, label=cat)
        for i, v in enumerate(vals):
            if v >= 0.06:
                ax.text(left[i] + v / 2, y[i], f"{v:.0%}", ha="center", va="center", fontsize=9, color="white")
        left += vals
    ax.set_yticks(y); ax.set_yticklabels(props.index)
    ax.set_xlim(0, 1); ax.set_xticks([0, .25, .5, .75, 1.0])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.invert_yaxis()
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.tick_params(left=False)
    ax.set_title("Overall NQS rating: urban vs rural services", fontsize=13,
                 fontweight="bold", color=INK_PRIMARY, loc="left", pad=14)
    handles = [Patch(facecolor=RATING_COLORS[c], label=c) for c in RATING_ORDER_SUBSTANTIVE]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.28), ncol=3, frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "07_rating_by_urban_rural.png", dpi=200)
    plt.close(fig)

    urban_exceeding = props.iloc[0][["Exceeding NQS", "Excellent"]].sum()
    rural_exceeding = props.iloc[1][["Exceeding NQS", "Excellent"]].sum()
    return {
        "urban_exceeding_pct": round(float(urban_exceeding) * 100, 1),
        "rural_exceeding_pct": round(float(rural_exceeding) * 100, 1),
    }


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
    grid = d.groupby(["State", "SOS_Category"])["nearest_service_km"].median().unstack()
    grid = grid.reindex(columns=SOS_ORDER)
    grid = grid.loc[grid.mean(axis=1, skipna=True).sort_values(ascending=False).index]

    fig, ax = plt.subplots(figsize=(8.5, 5))
    vals = grid.values.astype(float)
    im = ax.imshow(np.ma.masked_invalid(vals), cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(grid.columns))); ax.set_xticklabels(grid.columns, rotation=20, ha="right")
    ax.set_yticks(range(len(grid.index))); ax.set_yticklabels(grid.index)
    for i in range(vals.shape[0]):
        for j in range(vals.shape[1]):
            v = vals[i, j]
            if np.isnan(v):
                continue
            txt_color = "white" if v > np.nanmax(vals) * 0.55 else INK_PRIMARY
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=8.5, color=txt_color)
    for spine in ax.spines.values():
        spine.set_visible(False)
    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cbar.set_label("Median distance to nearest other service (km)", color=INK_SECONDARY, fontsize=9)
    ax.set_title("Where is the next service furthest away? (coverage gaps by state)",
                 fontsize=12, fontweight="bold", color=INK_PRIMARY, loc="left", pad=14)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "09_coverage_gaps.png", dpi=200)
    plt.close(fig)

    flat = grid.stack()
    worst = flat.idxmax()
    return {
        "most_underserved_state_sos": f"{worst[0]} / {worst[1]}",
        "most_underserved_median_km": round(float(flat.max()), 1),
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

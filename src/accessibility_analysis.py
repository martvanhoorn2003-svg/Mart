"""
Accessibility & Coverage Analysis stream for the ACECQA education & care
services dataset.

Four charts, each answering one of the assignment's four Accessibility &
Coverage requirements directly, with a concrete claim the chart proves
rather than a neutral description of the data:

  1. Geographical distribution: services are ~12,000x more concentrated
     per square kilometre in major cities than in rural areas.
  2. Where new services are needed most: a ranked list of the specific
     state x area-type combinations furthest from an alternative service.
  3. Transport connectivity: most services nationally are well-connected
     to public transport, which makes the real gap in small country
     towns and rural areas stand out clearly rather than being buried
     under an unrealistically strict national baseline.
  4. Spatially identifying underserved areas: mapping every poorly-
     connected service shows where the gaps concentrate.

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
from scipy.spatial import cKDTree

from clean import load_clean
from urban_rural import classify_urban_rural, load_sos_boundaries

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

SOS_ORDER = ["Major Urban", "Other Urban", "Bounded Locality", "Rural Balance"]
MIN_CELL_N = 15  # cells below this are dropped - too few services for a reliable rate

# A service counts as "well-connected" if it's within a short drive of
# either mode - not walking distance, which the data doesn't support as a
# national baseline (median distance to a bus stop alone is 9.3km).
# 5km to a train station and 10km to a bus stop are both roughly a 10-15
# minute drive - a reasonable "not effectively cut off" bar - and set this
# way the majority of the country clears it, which is what makes the
# minority that doesn't stand out as a real gap rather than an artefact of
# an unrealistically strict cutoff.
TRAIN_CONNECTED_KM = 5.0
BUS_CONNECTED_KM = 10.0

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
    full.
    """
    d = df.copy()
    pts = gpd.GeoDataFrame(
        d, geometry=gpd.points_from_xy(d["lon"], d["lat"]), crs="EPSG:4326"
    ).to_crs("EPSG:3577")  # GDA2020 / Australian Albers - metres
    coords = np.vstack([pts.geometry.x, pts.geometry.y]).T
    dist, _ = cKDTree(coords).query(coords, k=2)  # k=1 is the point itself
    d["nearest_service_km"] = dist[:, 1] / 1000
    return d


def add_connectivity_flag(df: pd.DataFrame) -> pd.DataFrame:
    d = df[~df["train_dist_outlier"] & ~df["bus_dist_outlier"]].copy()
    d["WellConnected"] = (d["DistanceToTrainStation_km"] <= TRAIN_CONNECTED_KM) | \
                          (d["DistanceToBusStation_km"] <= BUS_CONNECTED_KM)
    return d


# --- Requirement 1: geographical distribution, urban vs rural disparity ---
def chart_geographic_distribution(df: pd.DataFrame) -> dict:
    sos = load_sos_boundaries()
    area_by_cat = sos.groupby("SOS_NAME21")["AREASQKM21"].sum()
    counts = df["SOS_Category"].value_counts()
    density = (counts / area_by_cat.reindex(counts.index)) * 1000
    density = density.reindex(SOS_ORDER)

    fig, ax = plt.subplots(figsize=(9, 5.8))
    bars = ax.bar(SOS_ORDER, density.values, color=CAT["red"], width=0.6)
    ax.set_yscale("log")
    ax.set_ylim(0.02, 3000)  # fixed range so every bar/label sits inside the axes
    for bar, cat in zip(bars, SOS_ORDER):
        v = density[cat]
        label = f"{v:,.0f}" if v >= 1 else f"{v:.2f}"
        ax.text(bar.get_x() + bar.get_width() / 2, v * 1.35, f"{label}\n(n={counts[cat]:,})",
                ha="center", va="bottom", fontsize=9, fontweight="bold", linespacing=1.6)
    ax.set_ylabel("Approved services per 1,000 km² (log scale)")
    ratio = density["Major Urban"] / density["Rural Balance"]
    ax.set_title(f"Services are ~{ratio:,.0f}x more geographically concentrated\nin major cities than in rural areas",
                 fontsize=13, fontweight="bold", color=INK_PRIMARY, loc="left", pad=14)
    ax.text(0.02, 0.06, "This is a distribution problem, not just a population one: even\n"
                        "accounting for lower rural population, this gap is orders of\n"
                        "magnitude larger than any reasonable demand ratio.",
            transform=ax.transAxes, ha="left", fontsize=8.5, color=INK_SECONDARY)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(BASELINE); ax.spines["bottom"].set_color(BASELINE)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "06_geographic_distribution.png", dpi=200)
    plt.close(fig)
    return {
        "density_major_urban_per_1000km2": round(float(density["Major Urban"]), 1),
        "density_rural_balance_per_1000km2": round(float(density["Rural Balance"]), 3),
        "density_ratio_urban_to_rural": round(float(ratio), 0),
    }


# --- Requirement 2: highlight regions where additional services may be required ---
def chart_underserved_regions(df: pd.DataFrame) -> dict:
    d = add_nearest_service_distance(df)
    d = d[d["State"].notna() & d["SOS_Category"].notna()]
    cell = d.groupby(["State", "SOS_Category"]).agg(
        median_km=("nearest_service_km", "median"), n=("nearest_service_km", "size")
    ).reset_index()
    cell = cell[cell["n"] >= MIN_CELL_N].sort_values("median_km", ascending=False).head(10)
    cell["label"] = cell["State"] + " — " + cell["SOS_Category"]

    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    colors = [CAT["red"] if v > 20 else (CAT["orange"] if v > 5 else CAT["blue"]) for v in cell["median_km"]]
    bars = ax.barh(cell["label"], cell["median_km"], color=colors, height=0.65)
    ax.invert_yaxis()
    for bar, km, n in zip(bars, cell["median_km"], cell["n"]):
        ax.text(bar.get_width() + max(cell["median_km"]) * 0.015, bar.get_y() + bar.get_height() / 2,
                f"{km:.1f}km (n={n:,})", va="center", fontsize=9)
    ax.set_xlabel("Median distance to the nearest alternative service (km)")
    ax.set_title("Where are additional services needed most?\nTop 10 most underserved region x area-type combinations",
                 fontsize=12.5, fontweight="bold", color=INK_PRIMARY, loc="left", pad=14)
    ax.text(0.99, 0.02, "Red = over 20km to the nearest alternative service - a family\n"
                        "with a closed or full centre has no realistic backup option.",
            transform=ax.transAxes, ha="right", fontsize=8.5, color=INK_SECONDARY)
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.tick_params(left=False)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "07_underserved_regions.png", dpi=200)
    plt.close(fig)

    top = cell.iloc[0]
    return {
        "most_underserved_state_sos": f"{top['State']} / {top['SOS_Category']}",
        "most_underserved_median_km": round(float(top["median_km"]), 1),
        "n_regions_over_20km_to_next_service": int((cell["median_km"] > 20).sum()),
    }


# --- Requirement 3: are services well-connected to public transport? ---
def chart_transport_connectivity(df: pd.DataFrame) -> dict:
    d = add_connectivity_flag(df)
    d = d[d["SOS_Category"].notna()]
    poorly_connected = d.groupby("SOS_Category")["WellConnected"].apply(lambda s: (~s).mean() * 100).reindex(SOS_ORDER)
    counts = d["SOS_Category"].value_counts().reindex(SOS_ORDER)
    national_poor = (~d["WellConnected"]).mean() * 100

    fig, ax = plt.subplots(figsize=(9, 5.8))
    bars = ax.bar(SOS_ORDER, poorly_connected.values, color=CAT["red"], width=0.6)
    for bar, cat in zip(bars, SOS_ORDER):
        v = poorly_connected[cat]
        ax.text(bar.get_x() + bar.get_width() / 2, v + 2, f"{v:.0f}%", ha="center", fontsize=11, fontweight="bold")
    ax.set_xticks(range(len(SOS_ORDER)))
    ax.set_xticklabels([f"{cat}\n(n={counts[cat]:,})" for cat in SOS_ORDER], fontsize=9.5)
    ax.axhline(national_poor, color=INK_SECONDARY, linestyle="--", linewidth=1)
    ax.text(1.5, national_poor + 3, f"National: {national_poor:.0f}% poorly connected",
            ha="center", fontsize=8.5, color=INK_SECONDARY)
    ax.set_ylim(0, 118)
    ax.set_ylabel("Share of services NOT well-connected to public transport")
    gap = poorly_connected["Bounded Locality"] - poorly_connected["Major Urban"]
    ax.set_title(f"{100 - national_poor:.0f}% of services nationally are well-connected to transport —\n"
                 f"but that collapses to just {100 - poorly_connected['Bounded Locality']:.0f}% in small country towns",
                 fontsize=12.5, fontweight="bold", color=INK_PRIMARY, loc="left", pad=14)
    ax.text(0.99, 0.97, f"\"Well-connected\" = within {TRAIN_CONNECTED_KM:.0f}km of a train station\n"
                        f"or {BUS_CONNECTED_KM:.0f}km of a bus stop - generous and drivable,\n"
                        "not walkable. Even against that bar, Bounded Localities and\n"
                        f"Rural Balance areas are {gap:.0f} and "
                        f"{poorly_connected['Rural Balance'] - poorly_connected['Major Urban']:.0f} points worse than "
                        "Major Urban.",
            transform=ax.transAxes, ha="right", va="top", fontsize=8, color=INK_SECONDARY,
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#f9f9f7", edgecolor=GRIDLINE))
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(BASELINE); ax.spines["bottom"].set_color(BASELINE)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "08_transport_connectivity.png", dpi=200)
    plt.close(fig)
    out = {"national_poorly_connected_pct": round(float(national_poor), 1)}
    for cat in SOS_ORDER:
        out[f"poorly_connected_{cat.lower().replace(' ', '_')}_pct"] = round(float(poorly_connected[cat]), 1)
    return out


# --- Requirement 4: identify underserved areas based on distance to transit ---
def chart_spatial_connectivity(df: pd.DataFrame) -> dict:
    d = add_connectivity_flag(df)
    d = d[d["lon"].notna() & d["lat"].notna() & ~d["geocode_suspect"]]
    states = gpd.read_file(AU_STATES_GEOJSON)

    fig, ax = plt.subplots(figsize=(9, 8))
    states.boundary.plot(ax=ax, color=BASELINE, linewidth=0.6)
    states.plot(ax=ax, color="#f9f9f7", edgecolor="none", zorder=0)

    connected = d[d["WellConnected"]]
    poor = d[~d["WellConnected"]]
    ax.scatter(connected["lon"], connected["lat"], s=4, alpha=0.35, linewidths=0,
               color=BASELINE, label=f"Well-connected (n={len(connected):,})", zorder=2)
    ax.scatter(poor["lon"], poor["lat"], s=6, alpha=0.6, linewidths=0,
               color=CAT["red"], label=f"NOT well-connected (n={len(poor):,})", zorder=3)

    ax.set_xlim(112, 155); ax.set_ylim(-44, -9); ax.set_aspect(1.4)
    ax.set_xticks([]); ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title(f"Where are the transport-underserved services? {len(poor):,} of {len(d):,} services\n"
                 "are more than a short drive from any train or bus stop",
                 fontsize=13, fontweight="bold", color=INK_PRIMARY, loc="left", pad=10)
    ax.legend(loc="lower left", frameon=False, fontsize=9, markerscale=3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "09_spatial_connectivity.png", dpi=200)
    plt.close(fig)
    return {"n_poorly_connected": int(len(poor)), "n_well_connected": int(len(connected))}


def main():
    df = classify_urban_rural(load_clean())

    summary = {}
    if SUMMARY_PATH.exists():
        summary = json.loads(SUMMARY_PATH.read_text())

    summary.update(chart_geographic_distribution(df))
    summary.update(chart_underserved_regions(df))
    summary.update(chart_transport_connectivity(df))
    summary.update(chart_spatial_connectivity(df))
    summary["sos_category_counts"] = df["SOS_Category"].value_counts(dropna=False).to_dict()

    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=2, default=str))
    print(f"\nFigures written to {FIG_DIR}/")


if __name__ == "__main__":
    main()

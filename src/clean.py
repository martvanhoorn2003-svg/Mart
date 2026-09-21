"""
Data loading and cleaning for the ACECQA Education & Care Services dataset.

Source data: National Registers of approved education and care services
(NQA ITS extract, one CSV per state, combined here), enriched by the
subject coordinator with spatial fields (geometry, nearest train/bus
station and distance to each).

Run standalone to produce a cleaned cache:
    python src/clean.py
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

RAW_PATH = Path("data/education_services.csv")
CLEAN_PATH = Path("data/education_services_clean.parquet")

# NQS rating scale, worst to best. Used to give the rating columns a
# meaningful order instead of the default alphabetical one.
# "Provisional - Not Yet Assessed" is not a quality tier (it means the
# service is new and hasn't had its first assessment visit) - it is kept
# as a distinct, non-comparable category rather than dropped or treated
# as missing, so downstream code must exclude it explicitly when doing
# ordinal comparisons (see `rated_only`).
NOT_YET_ASSESSED = "Provisional – Not Yet Assessed"
RATING_ORDER = [
    NOT_YET_ASSESSED,
    "Significant Improvement Required",
    "Working Towards NQS",
    "Meeting NQS",
    "Exceeding NQS",
    "Excellent",
]

RATING_COLS = [
    "OverallRating",
    "QualityArea1Rating",
    "QualityArea2Rating",
    "QualityArea3Rating",
    "QualityArea4Rating",
    "QualityArea5Rating",
    "QualityArea6Rating",
    "QualityArea7Rating",
]

QUALITY_AREA_LABELS = {
    "QualityArea1Rating": "QA1 Educational program",
    "QualityArea2Rating": "QA2 Children's health & safety",
    "QualityArea3Rating": "QA3 Physical environment",
    "QualityArea4Rating": "QA4 Staffing arrangements",
    "QualityArea5Rating": "QA5 Relationships with children",
    "QualityArea6Rating": "QA6 Collaborative partnerships",
    "QualityArea7Rating": "QA7 Governance & leadership",
}

# Detailed (non-exclusive) service-type flag columns, as documented in
# the assignment brief. A service can be "Yes" on more than one of these
# (e.g. a centre offering Long Day Care and Vacation Care), unlike the
# coarse two-category "ServiceType" column (Centre-Based Care / Family
# Day Care).
DETAILED_SERVICE_TYPE_COLS = [
    "Long Day Care",
    "Preschool/Kindergarten - Part of a School",
    "Preschool/Kindergarten - Stand alone",
    "Outside school Hours Care - After School",
    "Outside school Hours Care - Before School",
    "Outside school Hours Care - Vacation Care",
    "Other",
]

# Australia's onshore + external-territory bounding box, generously
# padded. Anything outside this is a geocoding failure, not a genuine
# service location.
AU_LON_RANGE = (105.0, 170.0)
AU_LAT_RANGE = (-45.0, -8.0)

_GEOM_RE = re.compile(r"c\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)")


def _parse_geometry(series: pd.Series) -> pd.DataFrame:
    """Parse R-style 'c(lon, lat)' strings into numeric lon/lat columns."""
    parsed = series.astype(str).str.extract(_GEOM_RE)
    lon = pd.to_numeric(parsed[0], errors="coerce")
    lat = pd.to_numeric(parsed[1], errors="coerce")
    return pd.DataFrame({"lon": lon, "lat": lat})


def load_raw(path: Path = RAW_PATH) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    n_start = len(df)

    # --- Data quality issue #1: unusable / geocoded-to-nowhere rows ---
    # 10 services carry no State, Postcode or FullAddress at all, and the
    # location team's geocoder fell back to the same placeholder point in
    # Myanmar (c(97.48747, 23.14958)) for all of them. These rows have no
    # recoverable location information, so they are dropped rather than
    # imputed - keeping them would corrupt every state/postcode/spatial
    # aggregation.
    bad_geocode = df["geometry"].eq("c(97.48747, 23.14958)")
    df = df.loc[~bad_geocode].copy()

    # --- Geometry ---
    geom = _parse_geometry(df["geometry"])
    df["lon"], df["lat"] = geom["lon"], geom["lat"]
    out_of_bounds = (
        df["lon"].lt(AU_LON_RANGE[0]) | df["lon"].gt(AU_LON_RANGE[1]) |
        df["lat"].lt(AU_LAT_RANGE[0]) | df["lat"].gt(AU_LAT_RANGE[1])
    )
    df["geocode_suspect"] = out_of_bounds.fillna(True)

    # --- Dates ---
    df["ServiceApprovalGrantedDate"] = pd.to_datetime(
        df["ServiceApprovalGrantedDate"], dayfirst=True, errors="coerce"
    )
    df["ApprovalYear"] = df["ServiceApprovalGrantedDate"].dt.year

    # --- Ratings: ordered categoricals ---
    for col in RATING_COLS:
        df[col] = pd.Categorical(df[col], categories=RATING_ORDER, ordered=True)
    df["IsRated"] = df["OverallRating"].notna()

    # --- Detailed service-type flags -> booleans ---
    for col in DETAILED_SERVICE_TYPE_COLS:
        df[col] = df[col].map({"Yes": True, "No": False})

    # --- Capacity ---
    df["NumberOfApprovedPlaces"] = pd.to_numeric(
        df["NumberOfApprovedPlaces"], errors="coerce"
    )

    # --- Transport distance outlier flag (kept, not dropped: remote/island
    # services genuinely sit hundreds of km from the nearest station - see
    # Torres Strait Island campuses of Tagai State College). Flagged so
    # downstream plots can choose to log-scale or exclude them explicitly.
    df["train_dist_outlier"] = df["DistanceToTrainStation_km"] > 100
    df["bus_dist_outlier"] = df["DistanceToBusStation_km"] > 100

    df["State"] = df["State"].str.strip()
    df["Postcode"] = pd.to_numeric(df["Postcode"], errors="coerce").astype("Int64")

    n_end = len(df)
    print(
        f"[clean] {n_start} -> {n_end} rows "
        f"({n_start - n_end} dropped: unusable geocode/address); "
        f"{df['geocode_suspect'].sum()} remaining rows flagged geocode_suspect"
    )
    return df


def rated_only(series: pd.Series) -> pd.Series:
    """Drop the 'not yet assessed' pseudo-category before ordinal analysis."""
    return series[series.astype(str) != NOT_YET_ASSESSED]


def load_clean(force: bool = False) -> pd.DataFrame:
    if CLEAN_PATH.exists() and not force:
        return pd.read_parquet(CLEAN_PATH)
    df = clean(load_raw())
    CLEAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(CLEAN_PATH, index=False)
    return df


if __name__ == "__main__":
    df = load_clean(force=True)
    print(df.shape)
    print(df["OverallRating"].value_counts(dropna=False))

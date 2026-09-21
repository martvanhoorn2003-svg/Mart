"""
Urban/rural classification via ABS Section of State (SOS) 2021, GDA2020.

Uses Option A from the assignment brief (spatial join against an ABS
boundary file, matched on the services' own lon/lat) rather than Option B
(postcode -> SA1 allocation), since a direct point-in-polygon join avoids
the many-to-many postcode/SA1 ambiguity entirely and the dataset already
carries point coordinates for every service.

SOS was chosen over the coarser Remoteness Areas (RA) file because it
gives a population-based split (Major Urban / Other Urban / Bounded
Locality / Rural Balance) that lines up naturally with an urban/rural
binary, which is what the assignment's accessibility questions need.

Source: ABS Digital Boundary Files, SOS_2021_AUST_GDA2020 shapefile.
https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/access-and-downloads/digital-boundary-files
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

SOS_SHAPEFILE = Path("data/external/sos_2021/SOS_2021_AUST_GDA2020.shp")

# The SOS classification also includes non-spatial administrative
# categories (Migratory, No usual address) that carry no polygon - they
# only apply to census collection districts, never to a point location,
# so they're dropped from the boundary layer before joining.
URBAN_CATEGORIES = {"Major Urban", "Other Urban"}
RURAL_CATEGORIES = {"Bounded Locality", "Rural Balance"}


def load_sos_boundaries() -> gpd.GeoDataFrame:
    sos = gpd.read_file(SOS_SHAPEFILE)
    return sos[sos.geometry.notna()].copy()


def classify_urban_rural(df: pd.DataFrame) -> pd.DataFrame:
    """Adds SOS_Category and UrbanRural columns via spatial join on lon/lat.

    A handful of points (coastal/island services) can fall just outside
    every polygon due to coastline generalisation in the boundary file;
    those are matched to their nearest SOS polygon instead of being left
    unclassified.
    """
    sos = load_sos_boundaries()

    pts = gpd.GeoDataFrame(
        df[["lon", "lat"]],
        geometry=gpd.points_from_xy(df["lon"], df["lat"]),
        crs="EPSG:4326",
        index=df.index,
    ).to_crs(sos.crs)

    cols = ["SOS_NAME21", "STE_NAME21", "geometry"]
    joined = gpd.sjoin(pts, sos[cols], how="left", predicate="within")
    joined = joined[~joined.index.duplicated(keep="first")]

    unmatched = joined["SOS_NAME21"].isna()
    if unmatched.any():
        # Reproject to an equal-area CRS (GDA2020 / Australian Albers) so
        # nearest-neighbour distances are computed in metres, not degrees.
        albers = "EPSG:3577"
        nearest = gpd.sjoin_nearest(
            pts.loc[unmatched].to_crs(albers), sos[cols].to_crs(albers), how="left"
        )
        nearest = nearest[~nearest.index.duplicated(keep="first")]
        joined.loc[unmatched, "SOS_NAME21"] = nearest["SOS_NAME21"]
        joined.loc[unmatched, "STE_NAME21"] = nearest["STE_NAME21"]

    out = df.copy()
    out["SOS_Category"] = joined["SOS_NAME21"].reindex(out.index)
    out["UrbanRural"] = out["SOS_Category"].map(
        lambda c: "Urban" if c in URBAN_CATEGORIES else ("Rural" if c in RURAL_CATEGORIES else pd.NA)
    )
    return out


if __name__ == "__main__":
    from clean import load_clean

    df = classify_urban_rural(load_clean())
    print(df["SOS_Category"].value_counts(dropna=False))
    print(df["UrbanRural"].value_counts(dropna=False))

"""Airport workers by home tract, and population-weighted tract centroids."""

import geopandas as gpd

from src.config import COUNTY_FIPS, CRS, PROCESSED_DIR, log_step

# these are LODES column names: S000 is total jobs, followed by jobs by earnings band (low, mid, high)
JOBS = ["S000", "SE01", "SE02", "SE03"]


def airport_workers_by_tract(blocks, lodes, airports):
    """sum each airport's jobs by the workers' home tract, keeping only the bay area counties."""
    blocks = blocks.to_crs(CRS)
    # get a repr point for filtering, guarantees we pick point inside shape; centroid (from lecture) can land outside
    points = gpd.GeoDataFrame(blocks[["GEOID20"]], geometry=blocks.representative_point(), crs=CRS)
    
    # keep blocks whose point inside airport polygon
    airport_blocks = gpd.sjoin(points, airports.to_crs(CRS), predicate="within")
    log_step("blocks", "inside airport", len(points), len(airport_blocks), "not on airport land")

    # keep jobs whose workplace is an airport block
    jobs = lodes.merge(airport_blocks[["GEOID20", "code"]], left_on="w_geocode", right_on="GEOID20")
    log_step("lodes", "work at airport", len(lodes), len(jobs), "workplace not an airport block")
    jobs["GEOID"] = jobs["h_geocode"].str[:11] # first 11 digits are the tract
    by_tract = jobs.groupby(["code", "GEOID"])[JOBS].sum().reset_index()

    # drop workers who live outside the 9 counties
    inside = by_tract["GEOID"].str[2:5].isin(COUNTY_FIPS) # digits 3-5 are fips
    outside_workers = by_tract.loc[~inside, "S000"].sum()
    log_step("airport_workers", "home in 9 counties", len(by_tract), inside.sum(), f"{outside_workers:,} of {by_tract['S000'].sum():,} workers live outside the 9 counties")
    by_tract = by_tract[inside]
    by_tract.to_csv(f"{PROCESSED_DIR}/airport_workers_by_tract.csv", index=False)
    return by_tract


def tract_centroids(blocks):
    """Compute each tract's population-weighted centroid from its blocks."""
    # block points in meters, weighted by block population
    blocks = blocks.to_crs(CRS)
    xy = blocks.representative_point().get_coordinates()
    df = blocks[["GEOID20", "POP20"]].copy()
    df["GEOID"] = df["GEOID20"].str[:11]
    # for weighted avg calc
    df["x"] = xy["x"] * df["POP20"]
    df["y"] = xy["y"] * df["POP20"]
    tracts = df.groupby("GEOID")[["POP20", "x", "y"]].sum().reset_index()

    # get rid of tracts with 0 people
    before = len(tracts)
    tracts = tracts[tracts["POP20"] > 0]
    log_step("tracts", "drop zero population", before, len(tracts), "POP20 = 0")

    # weighted avg = sum(x * pop) / total pop
    centroids = gpd.GeoDataFrame(
        tracts[["GEOID", "POP20"]],
        geometry=gpd.points_from_xy(tracts["x"] / tracts["POP20"], tracts["y"] / tracts["POP20"]),
        crs=CRS,
    )
    centroids.to_file(f"{PROCESSED_DIR}/tract_centroids.gpkg")
    centroids.to_crs(4326).to_file(f"{PROCESSED_DIR}/tract_centroids_4326.gpkg")
    return centroids

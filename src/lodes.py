"""Download (once) and load census blocks, LODES jobs, and TIGER airport polygons."""

import os

import geopandas as gpd
import pandas as pd
import requests

from src.config import COUNTY_FIPS, RAW_DIR, log_step

# keys are airport names from 2020 TIGER Landmarks file, airport statistical repr census code rows (k2457)
AIRPORT_NAMES = {
    "San Francisco International": "SFO",
    "Metropolitan Oakland International": "OAK",
    "San Jose International": "SJC",
}


def download(url, path):
    if not os.path.exists(path):
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(path, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                file.write(chunk)


def load_blocks():
    # 2020 TIGER California blocks
    path = f"{RAW_DIR}/ca_blocks_2020.zip"
    download("https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_06_tabblock20.zip", path)
    blocks = gpd.read_file(path)
    blocks["GEOID20"] = blocks["GEOID20"].astype(str)
    
    # filter to 9 county Bay Area
    before = len(blocks)
    blocks = blocks[blocks["COUNTYFP20"].astype(str).isin(COUNTY_FIPS)]
    log_step("blocks", "keep 9 counties", before, len(blocks), "block outside the 9 counties")
    return blocks[["GEOID20", "POP20", "geometry"]]


def load_lodes():
    # most recent California LODES data
    path = f"{RAW_DIR}/ca_lodes_jobs_2023.csv.gz"
    download("https://lehd.ces.census.gov/data/lodes/LODES8/ca/od/ca_od_main_JT00_2023.csv.gz", path)
    return pd.read_csv(path, usecols=["w_geocode", "h_geocode", "S000", "SE01", "SE02", "SE03"], dtype={"w_geocode": str, "h_geocode": str})


def load_airports():
    # TIGER area landmarks to filter for airports
    path = f"{RAW_DIR}/ca_landmarks_2020.zip"
    download("https://www2.census.gov/geo/tiger/TIGER2020/AREALM/tl_2020_06_arealm.zip", path)
    landmarks = gpd.read_file(path)
    # keep only landmarks matching SFO, OAK, SJC
    before = len(landmarks)
    airports = landmarks[(landmarks["MTFCC"] == "K2457") & landmarks["FULLNAME"].isin(AIRPORT_NAMES)].copy()
    log_step("airports", "match airport names", before, len(airports), "TIGER landmark is not an SFO, OAK or SJC airport (k2457)")
    airports["code"] = airports["FULLNAME"].map(AIRPORT_NAMES)
    return airports[["code", "geometry"]]

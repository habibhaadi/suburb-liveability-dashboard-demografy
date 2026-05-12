import os
from datetime import datetime, timezone
from pathlib import Path
from html import escape
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in .env")

if not GOOGLE_API_KEY:
    raise ValueError("Missing GOOGLE_API_KEY in .env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Suburb Comparison", layout="wide")

# --------------------------------------------------
# Config
# --------------------------------------------------

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

SATURATION_THRESHOLD = 55
FALLBACK_GRID_ROWS = 2
FALLBACK_GRID_COLS = 2

AUSTRALIAN_STATES = ["NSW", "VIC", "QLD", "SA", "WA", "TAS", "ACT", "NT"]

STATE_TO_FULL_NAME = {
    "NSW": "New South Wales",
    "VIC": "Victoria",
    "QLD": "Queensland",
    "SA": "South Australia",
    "WA": "Western Australia",
    "TAS": "Tasmania",
    "ACT": "Australian Capital Territory",
    "NT": "Northern Territory",
}

STATE_TO_CBD_ADDRESS = {
    "NSW": "Sydney NSW 2000, Australia",
    "VIC": "Melbourne VIC 3000, Australia",
    "QLD": "Brisbane QLD 4000, Australia",
    "SA": "Adelaide SA 5000, Australia",
    "WA": "Perth WA 6000, Australia",
    "TAS": "Hobart TAS 7000, Australia",
    "ACT": "Canberra ACT 2601, Australia",
    "NT": "Darwin NT 0800, Australia",
}

AREA_COLUMN = "suburb_area_sq_km"
POPULATION_COLUMN = "population"
RENT_COLUMN = "median_rent_weekly"
PRICE_SCORE_COLUMN = "price_score"

BASE_DIR = Path(__file__).resolve().parent.parent
REFERENCE_CSV_PATH = BASE_DIR / "pipeline" / "data" / "suburb_reference.csv"

MIN_RENT_WEEKLY = 200
MAX_RENT_WEEKLY = 1000

CATEGORY_ORDER = [
    "Social Density",
    "Active Outdoor",
    "Mobility",
    "Everyday Essentials",
    "Education and Family",
]

CATEGORY_WEIGHTS = {
    "Social Density": 0.20,
    "Active Outdoor": 0.15,
    "Mobility": 0.20,
    "Everyday Essentials": 0.15,
    "Education and Family": 0.10,
    "Affordability": 0.20,
}

CATEGORY_SHORT_LABELS = {
    "Social Density": "Social",
    "Active Outdoor": "Outdoor",
    "Mobility": "Mobility",
    "Everyday Essentials": "Essentials",
    "Education and Family": "Education",
    "Affordability": "Affordability",
}

# scale_method options:
# - per_km2
# - per_1000_residents
METRICS = {
    "cafe_count": {
        "label": "Cafe density",
        "raw_label": "Cafe count",
        "query_label": "cafes",
        "included_type": "cafe",
        "category": "Social Density",
        "enable_tiled_fallback": True,
        "scale_method": "per_km2",
        "unit_suffix": "/km²",
    },
    "restaurant_count": {
        "label": "Restaurant density",
        "raw_label": "Restaurant count",
        "query_label": "restaurants",
        "included_type": "restaurant",
        "category": "Social Density",
        "enable_tiled_fallback": True,
        "scale_method": "per_km2",
        "unit_suffix": "/km²",
    },
    "bar_count": {
        "label": "Bar density",
        "raw_label": "Bar count",
        "query_label": "bars",
        "included_type": "bar",
        "category": "Social Density",
        "enable_tiled_fallback": True,
        "scale_method": "per_km2",
        "unit_suffix": "/km²",
    },
    "dessert_count": {
        "label": "Dessert density",
        "raw_label": "Dessert count",
        "query_label": "dessert places",
        "included_type": "bakery",
        "category": "Social Density",
        "enable_tiled_fallback": False,
        "scale_method": "per_km2",
        "unit_suffix": "/km²",
    },

    "park_count": {
        "label": "Park density",
        "raw_label": "Park count",
        "query_label": "parks",
        "included_type": "park",
        "category": "Active Outdoor",
        "enable_tiled_fallback": False,
        "scale_method": "per_km2",
        "unit_suffix": "/km²",
    },
    "sports_ground_count": {
        "label": "Sports ground density",
        "raw_label": "Sports ground count",
        "query_label": "sports field",
        "included_type": None,
        "category": "Active Outdoor",
        "enable_tiled_fallback": False,
        "scale_method": "per_km2",
        "unit_suffix": "/km²",
    },
    "playground_count": {
        "label": "Playground density",
        "raw_label": "Playground count",
        "query_label": "playgrounds",
        "included_type": "playground",
        "category": "Active Outdoor",
        "enable_tiled_fallback": False,
        "scale_method": "per_km2",
        "unit_suffix": "/km²",
    },
    "gym_count": {
        "label": "Gym density",
        "raw_label": "Gym count",
        "query_label": "gyms",
        "included_type": "gym",
        "category": "Active Outdoor",
        "enable_tiled_fallback": False,
        "scale_method": "per_km2",
        "unit_suffix": "/km²",
    },

    "train_station_count": {
        "label": "Train station density",
        "raw_label": "Train station count",
        "query_label": "train stations",
        "included_type": "train_station",
        "category": "Mobility",
        "enable_tiled_fallback": False,
        "scale_method": "per_km2",
        "unit_suffix": "/km²",
    },
    "tram_stop_count": {
        "label": "Tram stop density",
        "raw_label": "Tram stop count",
        "query_label": "tram stop",
        "included_type": None,
        "category": "Mobility",
        "enable_tiled_fallback": True,
        "scale_method": "per_km2",
        "unit_suffix": "/km²",
    },
    "bus_stop_count": {
        "label": "Bus stop density",
        "raw_label": "Bus stop count",
        "query_label": "bus stop",
        "included_type": None,
        "category": "Mobility",
        "enable_tiled_fallback": False,
        "scale_method": "per_km2",
        "unit_suffix": "/km²",
    },

    "supermarket_count": {
        "label": "Supermarkets per 1,000 residents",
        "raw_label": "Supermarket count",
        "query_label": "supermarkets",
        "included_type": "supermarket",
        "category": "Everyday Essentials",
        "enable_tiled_fallback": False,
        "scale_method": "per_1000_residents",
        "unit_suffix": "per 1,000",
    },
    "pharmacy_count": {
        "label": "Pharmacies per 1,000 residents",
        "raw_label": "Pharmacy count",
        "query_label": "pharmacies",
        "included_type": "pharmacy",
        "category": "Everyday Essentials",
        "enable_tiled_fallback": False,
        "scale_method": "per_1000_residents",
        "unit_suffix": "per 1,000",
    },
    "gp_clinic_count": {
        "label": "GP clinics per 1,000 residents",
        "raw_label": "GP clinic count",
        "query_label": "GP clinic",
        "included_type": None,
        "category": "Everyday Essentials",
        "enable_tiled_fallback": False,
        "scale_method": "per_1000_residents",
        "unit_suffix": "per 1,000",
    },
    "bank_count": {
        "label": "Banks per 1,000 residents",
        "raw_label": "Bank count",
        "query_label": "banks",
        "included_type": "bank",
        "category": "Everyday Essentials",
        "enable_tiled_fallback": False,
        "scale_method": "per_1000_residents",
        "unit_suffix": "per 1,000",
    },

    "childcare_count": {
        "label": "Childcare centres per 1,000 residents",
        "raw_label": "Childcare count",
        "query_label": "childcare centre",
        "included_type": None,
        "category": "Education and Family",
        "enable_tiled_fallback": False,
        "scale_method": "per_1000_residents",
        "unit_suffix": "per 1,000",
    },
    "primary_school_count": {
        "label": "Primary schools per 1,000 residents",
        "raw_label": "Primary school count",
        "query_label": "primary school",
        "included_type": "school",
        "category": "Education and Family",
        "enable_tiled_fallback": False,
        "scale_method": "per_1000_residents",
        "unit_suffix": "per 1,000",
    },
    "high_school_count": {
        "label": "High schools per 1,000 residents",
        "raw_label": "High school count",
        "query_label": "high school",
        "included_type": "school",
        "category": "Education and Family",
        "enable_tiled_fallback": False,
        "scale_method": "per_1000_residents",
        "unit_suffix": "per 1,000",
    },
    "library_count": {
        "label": "Libraries per 1,000 residents",
        "raw_label": "Library count",
        "query_label": "libraries",
        "included_type": "library",
        "category": "Education and Family",
        "enable_tiled_fallback": False,
        "scale_method": "per_1000_residents",
        "unit_suffix": "per 1,000",
    },
    "community_centre_count": {
        "label": "Community centres per 1,000 residents",
        "raw_label": "Community centre count",
        "query_label": "community centres",
        "included_type": "community_center",
        "category": "Education and Family",
        "enable_tiled_fallback": False,
        "scale_method": "per_1000_residents",
        "unit_suffix": "per 1,000",
    },
}

TRAVEL_METRICS = {
    "distance_to_cbd_km": {
        "label": "Distance to CBD (km)",
        "category": "Mobility",
    },
    "car_time_to_cbd_mins": {
        "label": "Car time to CBD (mins)",
        "category": "Mobility",
    },
    "transit_time_to_cbd_mins": {
        "label": "Transit time to CBD (mins)",
        "category": "Mobility",
    },
    "walk_time_to_cbd_mins": {
        "label": "Walk time to CBD (mins)",
        "category": "Mobility",
    },
}

# Benchmarks for converting scaled metrics into 0-10 scores.
# Higher is better for amenity metrics.
METRIC_SCORE_BENCHMARKS = {
    "cafe_count": 8.0,
    "restaurant_count": 10.0,
    "bar_count": 4.0,
    "dessert_count": 4.0,
    "park_count": 3.0,
    "sports_ground_count": 1.2,
    "playground_count": 2.0,
    "gym_count": 2.0,
    "train_station_count": 0.8,
    "tram_stop_count": 6.0,
    "bus_stop_count": 8.0,
    "supermarket_count": 0.35,
    "pharmacy_count": 0.20,
    "gp_clinic_count": 0.18,
    "bank_count": 0.12,
    "childcare_count": 0.25,
    "primary_school_count": 0.08,
    "high_school_count": 0.05,
    "library_count": 0.05,
    "community_centre_count": 0.08,
}

# Lower is better for travel metrics.
TRAVEL_SCORE_BOUNDS = {
    "distance_to_cbd_km": {"best": 2.0, "worst": 50.0},
    "car_time_to_cbd_mins": {"best": 10.0, "worst": 80.0},
    "transit_time_to_cbd_mins": {"best": 15.0, "worst": 120.0},
    "walk_time_to_cbd_mins": {"best": 20.0, "worst": 240.0},
}


# --------------------------------------------------
# UI styling helpers
# --------------------------------------------------

def apply_custom_styles() -> None:
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

:root {
    --bg: #070A12;
    --bg-2: #0B1020;
    --panel: rgba(13, 18, 32, 0.84);
    --panel-solid: #0F172A;
    --panel-soft: rgba(30, 41, 59, 0.62);
    --panel-lift: rgba(51, 65, 85, 0.48);
    --border: rgba(226, 232, 240, 0.13);
    --border-strong: rgba(226, 232, 240, 0.24);
    --text: #F8FAFC;
    --muted: #94A3B8;
    --muted-2: #CBD5E1;
    --accent: #A78BFA;
    --accent-strong: #7C3AED;
    --accent-2: #38BDF8;
    --gold: #F8D57E;
    --good: #34D399;
    --warn: #FBBF24;
    --bad: #FB7185;
}

html, body, [class*="css"] {
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at 8% 0%, rgba(124, 58, 237, 0.22), transparent 34rem),
        radial-gradient(circle at 90% 8%, rgba(56, 189, 248, 0.15), transparent 30rem),
        radial-gradient(circle at 50% 110%, rgba(248, 213, 126, 0.08), transparent 32rem),
        linear-gradient(180deg, var(--bg) 0%, var(--bg-2) 48%, #090D18 100%);
    color: var(--text);
}

.block-container {
    padding-top: 1.4rem;
    padding-bottom: 4rem;
    max-width: 1480px;
}

#MainMenu, footer, header {visibility: hidden;}

h1, h2, h3, h4, h5, h6, p, label, span, div {
    color: inherit;
}

hr { border-color: rgba(226, 232, 240, 0.12); }

.hero-shell {
    position: relative;
    overflow: hidden;
    border: 1px solid var(--border);
    border-radius: 34px;
    padding: 2.4rem;
    margin-bottom: 1.1rem;
    background:
        linear-gradient(135deg, rgba(15, 23, 42, 0.96), rgba(2, 6, 23, 0.92)),
        radial-gradient(circle at 82% 16%, rgba(167, 139, 250, 0.28), transparent 22rem);
    box-shadow: 0 30px 100px rgba(0,0,0,0.44), inset 0 1px 0 rgba(255,255,255,0.04);
}

.hero-shell:before {
    content: "";
    position: absolute;
    inset: 0;
    background-image:
        linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.032) 1px, transparent 1px);
    background-size: 42px 42px;
    mask-image: radial-gradient(circle at 70% 20%, black, transparent 62%);
    pointer-events: none;
}

.hero-content { position: relative; z-index: 1; max-width: 920px; }

.eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    color: var(--gold);
    font-size: 0.76rem;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    font-weight: 900;
    margin-bottom: 0.85rem;
}

.hero-title {
    font-size: clamp(2.35rem, 5vw, 5.25rem);
    line-height: 0.94;
    font-weight: 900;
    letter-spacing: -0.075em;
    margin-bottom: 1rem;
}

.hero-title span {
    background: linear-gradient(135deg, #FFFFFF 0%, #C4B5FD 46%, #7DD3FC 100%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
}

.hero-copy {
    color: var(--muted-2);
    max-width: 820px;
    font-size: 1.04rem;
    line-height: 1.72;
}

.hero-meta-row, .pill-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem;
    margin-top: 1.15rem;
}

.pill, .hero-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    border: 1px solid rgba(226, 232, 240, 0.16);
    background: rgba(15, 23, 42, 0.62);
    border-radius: 999px;
    padding: 0.48rem 0.78rem;
    color: var(--muted-2);
    font-size: 0.8rem;
    font-weight: 800;
    backdrop-filter: blur(12px);
}

.input-card, .result-card, .suburb-card, .detail-card, .method-card, .comparison-table-card {
    border: 1px solid var(--border);
    border-radius: 28px;
    background: linear-gradient(180deg, rgba(15, 23, 42, 0.78), rgba(15, 23, 42, 0.56));
    box-shadow: 0 22px 70px rgba(0,0,0,0.30), inset 0 1px 0 rgba(255,255,255,0.035);
    backdrop-filter: blur(14px);
}

.input-card {
    padding: 1.45rem 1.55rem;
    margin: 1.1rem 0 1.15rem 0;
}

.section-kicker {
    color: var(--accent-2);
    font-size: 0.76rem;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    margin-bottom: 0.4rem;
}

.section-heading {
    font-size: 1.45rem;
    font-weight: 900;
    letter-spacing: -0.045em;
    margin-bottom: 0.45rem;
}

.section-copy {
    color: var(--muted);
    font-size: 0.92rem;
    line-height: 1.62;
    margin-bottom: 0.9rem;
}

.result-card {
    position: relative;
    overflow: hidden;
    padding: 1.7rem;
    margin: 1.2rem 0;
}

.result-card:after {
    content: "";
    position: absolute;
    right: -4rem;
    top: -4rem;
    width: 16rem;
    height: 16rem;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(167,139,250,0.22), transparent 70%);
    pointer-events: none;
}

.winner-title {
    position: relative;
    z-index: 1;
    font-size: clamp(1.65rem, 3vw, 3rem);
    font-weight: 900;
    letter-spacing: -0.065em;
    margin: 0.25rem 0 0.45rem 0;
}

.winner-subtext {
    position: relative;
    z-index: 1;
    color: var(--muted-2);
    font-size: 1rem;
    line-height: 1.6;
    margin-bottom: 1.1rem;
}

.score-strip {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 0.9rem;
    margin-top: 1rem;
}

.score-strip-tile {
    border: 1px solid rgba(226, 232, 240, 0.14);
    border-radius: 22px;
    padding: 1rem;
    background: rgba(2, 6, 23, 0.38);
}

.score-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(148px, 1fr));
    gap: 0.82rem;
    margin-top: 0.9rem;
}

.score-tile {
    border: 1px solid rgba(226, 232, 240, 0.13);
    border-radius: 22px;
    background: linear-gradient(180deg, rgba(30, 41, 59, 0.64), rgba(2, 6, 23, 0.34));
    padding: 1rem;
    min-height: 112px;
}

.tile-label {
    color: var(--muted);
    font-size: 0.72rem;
    font-weight: 900;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.36rem;
}

.tile-value {
    color: var(--text);
    font-size: 1.55rem;
    font-weight: 900;
    letter-spacing: -0.045em;
    font-variant-numeric: tabular-nums;
}

.tile-sub {
    color: var(--muted);
    font-size: 0.78rem;
    margin-top: 0.3rem;
    line-height: 1.35;
}

.suburb-card {
    overflow: hidden;
    padding: 0;
    margin-bottom: 1rem;
}

.suburb-card-header {
    padding: 1.35rem 1.35rem 1.1rem 1.35rem;
    background:
        radial-gradient(circle at 90% 0%, rgba(56,189,248,0.12), transparent 14rem),
        linear-gradient(180deg, rgba(30,41,59,0.58), transparent);
    border-bottom: 1px solid rgba(226, 232, 240, 0.10);
}

.suburb-name {
    font-size: 1.55rem;
    font-weight: 900;
    letter-spacing: -0.055em;
}

.suburb-score-line {
    color: var(--muted-2);
    margin-top: 0.35rem;
    font-size: 0.9rem;
}

.suburb-card-body { padding: 1.2rem 1.25rem 1.35rem 1.25rem; }

.status-pill {
    display: inline-flex;
    margin-top: 0.75rem;
    padding: 0.32rem 0.66rem;
    border-radius: 999px;
    background: rgba(56, 189, 248, 0.10);
    color: #7DD3FC;
    border: 1px solid rgba(56, 189, 248, 0.24);
    font-size: 0.72rem;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.09em;
}

.category-band {
    display: grid;
    grid-template-columns: minmax(110px, 1fr) minmax(110px, 1.2fr) auto;
    gap: 0.8rem;
    align-items: center;
    padding: 0.75rem 0;
    border-bottom: 1px solid rgba(226, 232, 240, 0.10);
}

.category-band:last-child { border-bottom: 0; }
.category-name { font-weight: 850; color: var(--text); font-size: 0.88rem; }
.category-score { color: var(--muted-2); font-weight: 900; font-variant-numeric: tabular-nums; font-size: 0.86rem; }
.category-leader { color: var(--accent-2); font-size: 0.76rem; font-weight: 900; text-align: right; }

.mini-bar {
    width: 100%;
    height: 8px;
    border-radius: 999px;
    background: rgba(148, 163, 184, 0.16);
    overflow: hidden;
}

.mini-bar-fill {
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, var(--accent-strong), var(--accent-2));
}

.method-card {
    padding: 1.2rem 1.3rem;
    margin: 1.2rem 0;
}

.comparison-table-card {
    padding: 1.2rem;
    margin: 1rem 0;
}

.stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
    background-color: rgba(2, 6, 23, 0.62) !important;
    border: 1px solid rgba(226, 232, 240, 0.18) !important;
    border-radius: 16px !important;
    color: #F8FAFC !important;
    min-height: 3rem !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
}

.stTextInput input:focus {
    border-color: rgba(125, 211, 252, 0.58) !important;
    box-shadow: 0 0 0 3px rgba(56,189,248,0.10) !important;
}

.stTextInput label, .stSelectbox label {
    color: #CBD5E1 !important;
    font-weight: 850 !important;
}

.stButton > button {
    width: 100%;
    border-radius: 18px;
    border: 1px solid rgba(167, 139, 250, 0.62);
    background: linear-gradient(135deg, #8B5CF6, #2563EB 52%, #0891B2);
    color: white;
    font-weight: 900;
    height: 3.25rem;
    box-shadow: 0 16px 36px rgba(37, 99, 235, 0.26), inset 0 1px 0 rgba(255,255,255,0.18);
}

.stButton > button:hover {
    border-color: rgba(248, 213, 126, 0.62);
    filter: brightness(1.08);
    transform: translateY(-1px);
}

[data-testid="stExpander"] {
    border: 1px solid rgba(226, 232, 240, 0.13) !important;
    border-radius: 20px !important;
    background: rgba(2, 6, 23, 0.36) !important;
    overflow: hidden;
}

[data-testid="stAlert"] {
    border-radius: 20px;
    border: 1px solid rgba(226, 232, 240, 0.18);
    background: rgba(15, 23, 42, 0.76);
}

.stDataFrame, .stTable {
    border-radius: 18px;
    overflow: hidden;
}

[data-testid="stDataFrame"] {
    border: 1px solid rgba(226, 232, 240, 0.12);
    border-radius: 18px;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    st.markdown(
        """
<div class="hero-shell">
    <div class="hero-content">
        <div class="eyebrow">Demografy</div>
        <div class="hero-title">A clearer way to compare <span>where life happens.</span></div>
        <div class="hero-copy">
            See how Australian suburbs compare across lifestyle, movement, everyday access, education and affordability.
            Built to turn location data into a quieter, more useful view of place.
        </div>
        <div class="hero-meta-row">
            <div class="hero-pill">Places data</div>
            <div class="hero-pill">ABS 2021</div>
            <div class="hero-pill">CBD travel</div>
            <div class="hero-pill">0–10 scoring</div>
        </div>
    </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def format_status(status: str) -> str:
    status_map = {
        "cache_hit": "Current",
        "cache_updated": "Updated",
        "cache_miss": "New",
        "history_recomputed": "Rebuilt",
    }
    return status_map.get(status, status.replace("_", " ").title())


def html_metric_tile(label: str, value: str, subtext: Optional[str] = None) -> str:
    safe_label = escape(str(label))
    safe_value = escape(str(value))
    safe_subtext = escape(str(subtext)) if subtext else ""
    sub_html = f'<div class="tile-sub">{safe_subtext}</div>' if safe_subtext else ""
    return f"""
<div class="score-tile">
    <div class="tile-label">{safe_label}</div>
    <div class="tile-value">{safe_value}</div>
    {sub_html}
</div>
"""


def render_metric_grid(metrics: List[Tuple[str, str, Optional[str]]]) -> None:
    tiles = "".join(html_metric_tile(label, value, subtext) for label, value, subtext in metrics)
    st.markdown(f'<div class="score-grid">{tiles}</div>', unsafe_allow_html=True)


def score_bar_html(score: Optional[float]) -> str:
    score_value = safe_float(score)
    width = 0 if score_value is None else max(0, min(100, score_value * 10))
    return f'<div class="mini-bar"><div class="mini-bar-fill" style="width:{width:.0f}%"></div></div>'


def render_category_score_bands(suburb: dict, other: dict) -> None:
    suburb_scores = compute_category_scores(suburb)
    other_scores = compute_category_scores(other)
    rows = []
    for category in score_keys_for_output():
        score = suburb_scores.get(category)
        other_score = other_scores.get(category)
        label = CATEGORY_SHORT_LABELS[category]
        leader = comparison_label(score, other_score)
        rows.append(
            f"""
<div class="category-band">
    <div class="category-name">{escape(label)}</div>
    <div>{score_bar_html(score)}</div>
    <div class="category-score">{escape(format_score_value(score))}</div>
</div>
            """
        )
    st.markdown("".join(rows), unsafe_allow_html=True)

# --------------------------------------------------
# Helpers
# --------------------------------------------------

def safe_float(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@st.cache_data(show_spinner=False)
def load_reference_data() -> pd.DataFrame:
    if not REFERENCE_CSV_PATH.exists():
        return pd.DataFrame(
            columns=[
                "name",
                "state",
                "population",
                "suburb_area_sq_km",
                "median_rent_weekly",
                "lookup_key",
            ]
        )

    df = pd.read_csv(REFERENCE_CSV_PATH)

    required_cols = {"name", "state", "population", "suburb_area_sq_km", "median_rent_weekly"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(
            f"{REFERENCE_CSV_PATH} is missing required columns: {sorted(missing)}"
        )

    df["name"] = df["name"].astype(str).apply(lambda x: " ".join(x.strip().title().split()))
    df["state"] = df["state"].astype(str).str.strip().str.upper()
    df["lookup_key"] = df["name"] + "|" + df["state"]

    df["population"] = pd.to_numeric(df["population"], errors="coerce")
    df["suburb_area_sq_km"] = pd.to_numeric(df["suburb_area_sq_km"], errors="coerce")
    df["median_rent_weekly"] = pd.to_numeric(df["median_rent_weekly"], errors="coerce")

    return df


def normalize_suburb_name(name: str) -> str:
    return " ".join(name.strip().title().split())


def normalize_state_code(state: str) -> str:
    state = state.strip().upper()
    if state not in AUSTRALIAN_STATES:
        raise ValueError(f"Invalid Australian state/territory: {state}")
    return state


def build_suburb_key(suburb_name: str, state_code: str) -> str:
    return f"{normalize_suburb_name(suburb_name)}, {normalize_state_code(state_code)}"


def get_state_full_name(state_code: str) -> str:
    state_code = normalize_state_code(state_code)
    return STATE_TO_FULL_NAME[state_code]


def get_cbd_destination_address(state_code: str) -> str:
    state_code = normalize_state_code(state_code)
    return STATE_TO_CBD_ADDRESS[state_code]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_price_score(median_rent_weekly: Optional[float]) -> Optional[float]:
    rent = safe_float(median_rent_weekly)
    if rent is None or rent <= 0:
        return None

    rent = max(MIN_RENT_WEEKLY, min(MAX_RENT_WEEKLY, rent))
    score = 10 * (MAX_RENT_WEEKLY - rent) / (MAX_RENT_WEEKLY - MIN_RENT_WEEKLY)
    return round(score, 2)


def get_reference_stats(suburb_name: str, state_code: str) -> Optional[dict]:
    suburb_name = normalize_suburb_name(suburb_name)
    state_code = normalize_state_code(state_code)

    df = load_reference_data()
    if df.empty:
        return None

    exact_match = df[
        (df["state"] == state_code) &
        (df["name"] == suburb_name)
    ]

    if not exact_match.empty:
        row = exact_match.iloc[0]
        population = row.get("population")
        area = row.get("suburb_area_sq_km")
        rent = row.get("median_rent_weekly")

        return {
            "population": int(population) if pd.notna(population) else None,
            "suburb_area_sq_km": float(area) if pd.notna(area) else None,
            "median_rent_weekly": float(rent) if pd.notna(rent) else None,
            "reference_match_name": row.get("name"),
            "reference_match_type": "exact",
        }

    state_variant_map = {
        "NSW": "Nsw",
        "VIC": "Vic.",
        "QLD": "Qld",
        "SA": "Sa",
        "WA": "Wa",
        "TAS": "Tas.",
        "ACT": "Act",
        "NT": "Nt",
    }

    variant = state_variant_map.get(state_code)
    candidate_name = f"{suburb_name} ({variant})" if variant else None

    if candidate_name:
        variant_match = df[
            (df["state"] == state_code) &
            (df["name"] == candidate_name)
        ]

        if not variant_match.empty:
            row = variant_match.iloc[0]
            population = row.get("population")
            area = row.get("suburb_area_sq_km")
            rent = row.get("median_rent_weekly")

            return {
                "population": int(population) if pd.notna(population) else None,
                "suburb_area_sq_km": float(area) if pd.notna(area) else None,
                "median_rent_weekly": float(rent) if pd.notna(rent) else None,
                "reference_match_name": row.get("name"),
                "reference_match_type": "state_variant",
            }

    return None


def get_suburb(suburb_name: str, state_code: str) -> List[dict]:
    response = (
        supabase
        .table("suburbs")
        .select("*")
        .eq("name", suburb_name)
        .eq("state", state_code)
        .execute()
    )
    return response.data


def insert_suburb(suburb_data: dict) -> List[dict]:
    insert_payload = suburb_data.copy()
    insert_payload["last_refreshed_at"] = utc_now_iso()

    response = (
        supabase
        .table("suburbs")
        .insert(insert_payload)
        .execute()
    )
    return response.data


def update_suburb_metrics(suburb_name: str, state_code: str, suburb_data: dict) -> List[dict]:
    update_payload = {
        key: value
        for key, value in suburb_data.items()
        if key not in {"name", "state"}
    }

    update_payload["last_refreshed_at"] = utc_now_iso()

    response = (
        supabase
        .table("suburbs")
        .update(update_payload)
        .eq("name", suburb_name)
        .eq("state", state_code)
        .execute()
    )
    return response.data


def enrich_with_reference_stats(suburb_data: dict, suburb_name: str, state_code: str) -> dict:
    reference_stats = get_reference_stats(suburb_name, state_code)
    if not reference_stats:
        suburb_data[PRICE_SCORE_COLUMN] = compute_price_score(suburb_data.get(RENT_COLUMN))
        return suburb_data

    if suburb_data.get("population") is None:
        suburb_data["population"] = reference_stats.get("population")

    if suburb_data.get("suburb_area_sq_km") is None:
        suburb_data["suburb_area_sq_km"] = reference_stats.get("suburb_area_sq_km")

    if suburb_data.get(RENT_COLUMN) is None:
        suburb_data[RENT_COLUMN] = reference_stats.get(RENT_COLUMN)

    suburb_data[PRICE_SCORE_COLUMN] = compute_price_score(suburb_data.get(RENT_COLUMN))
    return suburb_data


def insert_search_history(rows: List[dict]) -> None:
    if not rows:
        return
    supabase.table("suburb_search_history").insert(rows).execute()


def build_history_row(
    suburb_name: str,
    state_code: str,
    source: str,
    metric_key: Optional[str],
    request_payload: Optional[dict],
    response_payload: Optional[dict],
    status: str = "success",
) -> dict:
    return {
        "suburb_name": normalize_suburb_name(suburb_name),
        "state_code": normalize_state_code(state_code),
        "source": source,
        "metric_key": metric_key,
        "request_payload": request_payload,
        "response_payload": response_payload,
        "status": status,
        "fetched_at": utc_now_iso(),
    }


def get_search_history(suburb_name: str, state_code: str, limit: int = 200) -> List[dict]:
    response = (
        supabase
        .table("suburb_search_history")
        .select("*")
        .eq("suburb_name", normalize_suburb_name(suburb_name))
        .eq("state_code", normalize_state_code(state_code))
        .order("fetched_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data


def extract_geocode_from_history_payload(payload: Optional[dict]) -> Optional[dict]:
    if not payload:
        return None

    if payload.get("formatted_address") and payload.get("location") and payload.get("viewport"):
        return {
            "formatted_address": payload.get("formatted_address"),
            "location": payload.get("location"),
            "viewport": payload.get("viewport"),
            "raw_response": payload.get("raw_response"),
            "request_params": payload.get("request_params"),
        }

    results = payload.get("results")
    if not results:
        return None

    result = results[0]
    geometry = result.get("geometry", {})
    location = geometry.get("location")
    viewport = geometry.get("viewport")

    if not location or not viewport:
        return None

    return {
        "formatted_address": result.get("formatted_address"),
        "location": location,
        "viewport": viewport,
        "raw_response": payload,
        "request_params": None,
    }


def build_raw_bundle_from_history(suburb_name: str, state_code: str) -> Optional[dict]:
    rows = get_search_history(suburb_name, state_code)
    if not rows:
        return None

    latest_geocode_row = None
    latest_travel_row = None
    latest_metric_rows: Dict[str, dict] = {}

    for row in rows:
        source = row.get("source")
        metric_key = row.get("metric_key")

        if source == "google_geocode" and latest_geocode_row is None:
            latest_geocode_row = row
            continue

        if source == "google_routes" and metric_key == "travel_metrics" and latest_travel_row is None:
            latest_travel_row = row
            continue

        if source == "google_places_text_search" and metric_key in METRICS and metric_key not in latest_metric_rows:
            latest_metric_rows[metric_key] = row

        if latest_geocode_row and latest_travel_row and len(latest_metric_rows) == len(METRICS):
            break

    geocode_payload = extract_geocode_from_history_payload(
        latest_geocode_row.get("response_payload") if latest_geocode_row else None
    )
    travel_payload = latest_travel_row.get("response_payload") if latest_travel_row else None

    if geocode_payload is None or travel_payload is None:
        return None

    if len(latest_metric_rows) != len(METRICS):
        return None

    places_payload = {}
    for metric_name in METRICS.keys():
        metric_row = latest_metric_rows.get(metric_name)
        if not metric_row:
            return None

        metric_payload = metric_row.get("response_payload")
        if not metric_payload:
            return None

        places_payload[metric_name] = metric_payload

    return {
        "name": normalize_suburb_name(suburb_name),
        "state": normalize_state_code(state_code),
        "geocode": geocode_payload,
        "places": places_payload,
        "travel": travel_payload,
    }


def recompute_suburb_from_history(suburb_name: str, state_code: str) -> Optional[dict]:
    raw_bundle = build_raw_bundle_from_history(suburb_name, state_code)
    if raw_bundle is None:
        return None

    transformed_data = transform_raw_to_suburb_row(raw_bundle)
    existing = get_suburb(suburb_name, state_code)

    if existing:
        updated = update_suburb_metrics(suburb_name, state_code, transformed_data)
        return updated[0] if updated else None

    inserted = insert_suburb(transformed_data)
    return inserted[0] if inserted else None


def geocode_suburb(suburb_name: str, state_code: str) -> dict:
    state_full_name = get_state_full_name(state_code)

    params = {
        "address": f"{suburb_name}, {state_code}, Australia",
        "components": f"country:AU|administrative_area:{state_full_name}",
        "key": GOOGLE_API_KEY,
    }

    response = requests.get(GEOCODE_URL, params=params, timeout=20)
    response.raise_for_status()
    data = response.json()

    if data.get("status") != "OK" or not data.get("results"):
        raise ValueError(f"Geocoding failed for '{suburb_name}, {state_code}'")

    result = data["results"][0]
    geometry = result["geometry"]

    return {
        "formatted_address": result.get("formatted_address"),
        "location": geometry["location"],
        "viewport": geometry["viewport"],
        "raw_response": data,
        "request_params": {
            "address": params["address"],
            "components": params["components"],
        },
    }


def build_location_restriction(viewport: dict) -> dict:
    southwest = viewport["southwest"]
    northeast = viewport["northeast"]

    return {
        "rectangle": {
            "low": {
                "latitude": southwest["lat"],
                "longitude": southwest["lng"],
            },
            "high": {
                "latitude": northeast["lat"],
                "longitude": northeast["lng"],
            },
        }
    }


def split_viewport_into_tiles(viewport: dict, rows: int, cols: int) -> List[dict]:
    southwest = viewport["southwest"]
    northeast = viewport["northeast"]

    min_lat = southwest["lat"]
    min_lng = southwest["lng"]
    max_lat = northeast["lat"]
    max_lng = northeast["lng"]

    lat_step = (max_lat - min_lat) / rows
    lng_step = (max_lng - min_lng) / cols

    tiles: List[dict] = []

    for row in range(rows):
        for col in range(cols):
            tile_low_lat = min_lat + (row * lat_step)
            tile_high_lat = min_lat + ((row + 1) * lat_step)
            tile_low_lng = min_lng + (col * lng_step)
            tile_high_lng = min_lng + ((col + 1) * lng_step)

            tiles.append({
                "rectangle": {
                    "low": {
                        "latitude": tile_low_lat,
                        "longitude": tile_low_lng,
                    },
                    "high": {
                        "latitude": tile_high_lat,
                        "longitude": tile_high_lng,
                    },
                }
            })

    return tiles


def search_places_page(
    *,
    text_query: str,
    included_type: Optional[str],
    location_restriction: dict,
    page_token: Optional[str] = None,
) -> dict:
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,nextPageToken",
    }

    payload = {
        "textQuery": text_query,
        "locationRestriction": location_restriction,
        "pageSize": 20,
    }

    if included_type:
        payload["includedType"] = included_type
        payload["strictTypeFiltering"] = True

    if page_token:
        payload["pageToken"] = page_token

    response = requests.post(TEXT_SEARCH_URL, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def place_matches_suburb(place: dict, suburb_name: str, state_code: str) -> bool:
    formatted_address = (place.get("formattedAddress") or "").lower()
    suburb_token = normalize_suburb_name(suburb_name).lower()
    state_token = normalize_state_code(state_code).lower()
    state_full_token = get_state_full_name(state_code).lower()

    suburb_match = suburb_token in formatted_address
    state_match = state_token in formatted_address or state_full_token in formatted_address

    return suburb_match and state_match


def fetch_places_for_restrictions(
    *,
    suburb_name: str,
    state_code: str,
    query_label: str,
    included_type: Optional[str],
    location_restrictions: List[dict],
    filter_to_exact_suburb: bool = True,
) -> dict:
    text_query = f"{query_label} in {suburb_name}, {state_code}, Australia"

    all_places: List[dict] = []
    seen_ids: Set[str] = set()
    page_history: List[dict] = []

    for restriction_index, location_restriction in enumerate(location_restrictions, start=1):
        page_token: Optional[str] = None

        while True:
            page = search_places_page(
                text_query=text_query,
                included_type=included_type,
                location_restriction=location_restriction,
                page_token=page_token,
            )

            page_history.append({
                "restriction_index": restriction_index,
                "location_restriction": location_restriction,
                "page_token_used": page_token,
                "response": page,
            })

            places = page.get("places", [])
            for place in places:
                if filter_to_exact_suburb and not place_matches_suburb(place, suburb_name, state_code):
                    continue

                place_id = place.get("id")
                if place_id and place_id not in seen_ids:
                    seen_ids.add(place_id)
                    all_places.append(place)

            page_token = page.get("nextPageToken")
            if not page_token:
                break

    return {
        "text_query": text_query,
        "included_type": included_type,
        "location_restrictions": location_restrictions,
        "places": all_places,
        "page_history": page_history,
    }


def fetch_metric_places(
    *,
    suburb_name: str,
    state_code: str,
    viewport: dict,
    query_label: str,
    included_type: Optional[str],
    enable_tiled_fallback: bool,
) -> dict:
    primary_restriction = build_location_restriction(viewport)

    initial_result = fetch_places_for_restrictions(
        suburb_name=suburb_name,
        state_code=state_code,
        query_label=query_label,
        included_type=included_type,
        location_restrictions=[primary_restriction],
        filter_to_exact_suburb=True,
    )

    initial_places = initial_result["places"]
    should_use_fallback = enable_tiled_fallback and len(initial_places) >= SATURATION_THRESHOLD

    if not should_use_fallback:
        return {
            "strategy_used": "primary_only",
            "initial_result": initial_result,
            "final_places": initial_places,
        }

    tile_restrictions = split_viewport_into_tiles(
        viewport=viewport,
        rows=FALLBACK_GRID_ROWS,
        cols=FALLBACK_GRID_COLS,
    )

    tiled_result = fetch_places_for_restrictions(
        suburb_name=suburb_name,
        state_code=state_code,
        query_label=query_label,
        included_type=included_type,
        location_restrictions=tile_restrictions,
        filter_to_exact_suburb=True,
    )

    tiled_places = tiled_result["places"]

    if len(tiled_places) > len(initial_places):
        return {
            "strategy_used": "tiled_fallback",
            "initial_result": initial_result,
            "tiled_result": tiled_result,
            "final_places": tiled_places,
        }

    return {
        "strategy_used": "primary_only_after_fallback_check",
        "initial_result": initial_result,
        "tiled_result": tiled_result,
        "final_places": initial_places,
    }


def parse_duration_to_minutes(duration_str: Optional[str]) -> Optional[float]:
    if not duration_str:
        return None

    if not duration_str.endswith("s"):
        return None

    try:
        seconds = float(duration_str[:-1])
        return round(seconds / 60, 1)
    except ValueError:
        return None


def compute_route_metrics(
    *,
    origin_lat: float,
    origin_lng: float,
    destination_address: str,
    travel_mode: str,
    routing_preference: Optional[str] = None,
) -> dict:
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": "routes.duration,routes.staticDuration,routes.distanceMeters",
    }

    payload = {
        "origin": {
            "location": {
                "latLng": {
                    "latitude": origin_lat,
                    "longitude": origin_lng,
                }
            }
        },
        "destination": {
            "address": destination_address
        },
        "travelMode": travel_mode,
    }

    if routing_preference:
        payload["routingPreference"] = routing_preference

    response = requests.post(ROUTES_URL, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()

    routes = data.get("routes", [])
    if not routes:
        return {
            "duration_mins": None,
            "distance_km": None,
            "request_payload": payload,
            "response_payload": data,
        }

    route = routes[0]
    duration_mins = parse_duration_to_minutes(route.get("duration") or route.get("staticDuration"))

    distance_meters = route.get("distanceMeters")
    distance_km = round(distance_meters / 1000, 2) if distance_meters is not None else None

    return {
        "duration_mins": duration_mins,
        "distance_km": distance_km,
        "request_payload": payload,
        "response_payload": data,
    }


def get_travel_data(geo: dict, state_code: str) -> dict:
    origin_lat = geo["location"]["lat"]
    origin_lng = geo["location"]["lng"]
    cbd_destination_address = get_cbd_destination_address(state_code)

    car_route = compute_route_metrics(
        origin_lat=origin_lat,
        origin_lng=origin_lng,
        destination_address=cbd_destination_address,
        travel_mode="DRIVE",
        routing_preference="TRAFFIC_AWARE_OPTIMAL",
    )

    transit_route = compute_route_metrics(
        origin_lat=origin_lat,
        origin_lng=origin_lng,
        destination_address=cbd_destination_address,
        travel_mode="TRANSIT",
    )

    walk_route = compute_route_metrics(
        origin_lat=origin_lat,
        origin_lng=origin_lng,
        destination_address=cbd_destination_address,
        travel_mode="WALK",
    )

    return {
        "distance_to_cbd_km": car_route["distance_km"],
        "car_time_to_cbd_mins": car_route["duration_mins"],
        "transit_time_to_cbd_mins": transit_route["duration_mins"],
        "walk_time_to_cbd_mins": walk_route["duration_mins"],
        "raw_routes": {
            "car": car_route,
            "transit": transit_route,
            "walk": walk_route,
        },
    }


def fetch_raw_google_data(suburb_name: str, state_code: str) -> dict:
    suburb_name = normalize_suburb_name(suburb_name)
    state_code = normalize_state_code(state_code)

    geo = geocode_suburb(suburb_name, state_code)
    viewport = geo["viewport"]

    raw_bundle = {
        "name": suburb_name,
        "state": state_code,
        "geocode": geo,
        "places": {},
        "travel": None,
    }

    total_steps = len(METRICS) + 1
    progress_bar = st.progress(0)
    status_text = st.empty()

    for index, (column_name, config) in enumerate(METRICS.items(), start=1):
        status_text.write(f"Fetching {config['raw_label']} for {suburb_name}, {state_code}...")

        metric_result = fetch_metric_places(
            suburb_name=suburb_name,
            state_code=state_code,
            viewport=viewport,
            query_label=config["query_label"],
            included_type=config["included_type"],
            enable_tiled_fallback=config.get("enable_tiled_fallback", False),
        )

        final_places = metric_result["final_places"]

        raw_bundle["places"][column_name] = {
            "raw_label": config["raw_label"],
            "query_label": config["query_label"],
            "included_type": config["included_type"],
            "strategy_used": metric_result["strategy_used"],
            "count": len(final_places),
            "places": final_places,
            "initial_result": metric_result.get("initial_result"),
            "tiled_result": metric_result.get("tiled_result"),
        }

        progress_bar.progress(index / total_steps)

    status_text.write(f"Fetching travel times for {suburb_name}, {state_code}...")
    raw_bundle["travel"] = get_travel_data(geo, state_code)
    progress_bar.progress(1.0)

    progress_bar.empty()
    status_text.empty()

    return raw_bundle


def save_raw_google_data(raw_bundle: dict) -> None:
    suburb_name = raw_bundle["name"]
    state_code = raw_bundle["state"]

    history_rows = []

    geocode_payload = raw_bundle.get("geocode", {})
    history_rows.append(
        build_history_row(
            suburb_name=suburb_name,
            state_code=state_code,
            source="google_geocode",
            metric_key=None,
            request_payload=geocode_payload.get("request_params"),
            response_payload=geocode_payload,
        )
    )

    for metric_key, metric_payload in raw_bundle.get("places", {}).items():
        history_rows.append(
            build_history_row(
                suburb_name=suburb_name,
                state_code=state_code,
                source="google_places_text_search",
                metric_key=metric_key,
                request_payload={
                    "query_label": metric_payload.get("query_label"),
                    "included_type": metric_payload.get("included_type"),
                    "strategy_used": metric_payload.get("strategy_used"),
                },
                response_payload=metric_payload,
            )
        )

    travel_payload = raw_bundle.get("travel", {})
    history_rows.append(
        build_history_row(
            suburb_name=suburb_name,
            state_code=state_code,
            source="google_routes",
            metric_key="travel_metrics",
            request_payload={
                "state_code": state_code,
                "destination_address": get_cbd_destination_address(state_code),
            },
            response_payload=travel_payload,
        )
    )

    insert_search_history(history_rows)


def transform_raw_to_suburb_row(raw_bundle: dict) -> dict:
    suburb_name = raw_bundle["name"]
    state_code = raw_bundle["state"]
    geo = raw_bundle["geocode"]

    result = {
        "name": suburb_name,
        "state": state_code,
        "formatted_address": geo.get("formatted_address"),
        "population": None,
        "suburb_area_sq_km": None,
        "median_rent_weekly": None,
        "price_score": None,
        "last_refreshed_at": utc_now_iso(),
    }

    for metric_name in METRICS.keys():
        metric_payload = raw_bundle["places"].get(metric_name, {})
        result[metric_name] = metric_payload.get("count")

    travel_data = raw_bundle.get("travel") or {}
    result.update({
        "distance_to_cbd_km": travel_data.get("distance_to_cbd_km"),
        "car_time_to_cbd_mins": travel_data.get("car_time_to_cbd_mins"),
        "transit_time_to_cbd_mins": travel_data.get("transit_time_to_cbd_mins"),
        "walk_time_to_cbd_mins": travel_data.get("walk_time_to_cbd_mins"),
    })

    result = enrich_with_reference_stats(result, suburb_name, state_code)
    return result


def metrics_complete(suburb_row: dict) -> bool:
    required_columns = list(METRICS.keys()) + list(TRAVEL_METRICS.keys())
    return all(suburb_row.get(metric_name) is not None for metric_name in required_columns)


def ensure_reference_stats_present(suburb_name: str, state_code: str, suburb_row: dict) -> dict:
    needs_population = suburb_row.get("population") is None
    needs_area = suburb_row.get("suburb_area_sq_km") is None
    needs_rent = suburb_row.get(RENT_COLUMN) is None
    needs_price_score = suburb_row.get(PRICE_SCORE_COLUMN) is None

    if not needs_population and not needs_area and not needs_rent and not needs_price_score:
        return suburb_row

    reference_stats = get_reference_stats(suburb_name, state_code)
    if not reference_stats:
        if needs_price_score:
            derived_price_score = compute_price_score(suburb_row.get(RENT_COLUMN))
            if derived_price_score is not None:
                updated = update_suburb_metrics(
                    suburb_name=suburb_name,
                    state_code=state_code,
                    suburb_data={
                        "name": suburb_name,
                        "state": state_code,
                        PRICE_SCORE_COLUMN: derived_price_score,
                    },
                )
                return updated[0] if updated else suburb_row
        return suburb_row

    update_payload = {}

    if needs_population and reference_stats.get("population") is not None:
        update_payload["population"] = reference_stats["population"]

    if needs_area and reference_stats.get("suburb_area_sq_km") is not None:
        update_payload["suburb_area_sq_km"] = reference_stats["suburb_area_sq_km"]

    if needs_rent and reference_stats.get(RENT_COLUMN) is not None:
        update_payload[RENT_COLUMN] = reference_stats[RENT_COLUMN]

    final_rent = update_payload.get(RENT_COLUMN, suburb_row.get(RENT_COLUMN))
    final_price_score = compute_price_score(final_rent)

    if needs_price_score and final_price_score is not None:
        update_payload[PRICE_SCORE_COLUMN] = final_price_score

    if not update_payload:
        return suburb_row

    updated = update_suburb_metrics(
        suburb_name=suburb_name,
        state_code=state_code,
        suburb_data={"name": suburb_name, "state": state_code, **update_payload},
    )
    return updated[0] if updated else suburb_row


def get_or_create_suburb(suburb_name: str, state_code: str) -> Tuple[dict, str]:
    suburb_name = normalize_suburb_name(suburb_name)
    state_code = normalize_state_code(state_code)

    existing = get_suburb(suburb_name, state_code)

    if existing:
        suburb = existing[0]
        suburb = ensure_reference_stats_present(suburb_name, state_code, suburb)

        if metrics_complete(suburb):
            return suburb, "cache_hit"

        recomputed = recompute_suburb_from_history(suburb_name, state_code)
        if recomputed and metrics_complete(recomputed):
            return recomputed, "history_recomputed"

    else:
        recomputed = recompute_suburb_from_history(suburb_name, state_code)
        if recomputed and metrics_complete(recomputed):
            return recomputed, "history_recomputed"

    raw_bundle = fetch_raw_google_data(suburb_name, state_code)
    save_raw_google_data(raw_bundle)
    transformed_data = transform_raw_to_suburb_row(raw_bundle)

    if existing:
        updated = update_suburb_metrics(suburb_name, state_code, transformed_data)
        return updated[0], "cache_updated"

    inserted = insert_suburb(transformed_data)
    return inserted[0], "cache_miss"


def compute_scaled_metric_value(suburb: dict, metric_name: str) -> Optional[float]:
    raw_value = suburb.get(metric_name)
    if raw_value is None:
        return None

    config = METRICS[metric_name]
    scale_method = config["scale_method"]

    if scale_method == "per_km2":
        area = safe_float(suburb.get(AREA_COLUMN))
        if area is None or area <= 0:
            return None
        return round(float(raw_value) / area, 2)

    if scale_method == "per_1000_residents":
        population = safe_float(suburb.get(POPULATION_COLUMN))
        if population is None or population <= 0:
            return None
        return round((float(raw_value) / population) * 1000, 3)

    return None


def build_scaled_metrics(suburb: dict) -> dict:
    return {
        metric_name: compute_scaled_metric_value(suburb, metric_name)
        for metric_name in METRICS.keys()
    }


def score_higher_is_better(value: Optional[float], benchmark: float) -> Optional[float]:
    value = safe_float(value)
    if value is None or benchmark <= 0:
        return None
    return round(max(0.0, min(10.0, (value / benchmark) * 10)), 2)


def score_lower_is_better(value: Optional[float], best: float, worst: float) -> Optional[float]:
    value = safe_float(value)
    if value is None or worst <= best:
        return None

    if value <= best:
        return 10.0
    if value >= worst:
        return 0.0

    score = 10 * (worst - value) / (worst - best)
    return round(score, 2)


def average_scores(values: List[Optional[float]]) -> Optional[float]:
    usable = [safe_float(v) for v in values if safe_float(v) is not None]
    if not usable:
        return None
    return round(sum(usable) / len(usable), 2)


def compute_category_scores(suburb: dict) -> dict:
    scaled = build_scaled_metrics(suburb)

    social_score = average_scores([
        score_higher_is_better(scaled.get("cafe_count"), METRIC_SCORE_BENCHMARKS["cafe_count"]),
        score_higher_is_better(scaled.get("restaurant_count"), METRIC_SCORE_BENCHMARKS["restaurant_count"]),
        score_higher_is_better(scaled.get("bar_count"), METRIC_SCORE_BENCHMARKS["bar_count"]),
        score_higher_is_better(scaled.get("dessert_count"), METRIC_SCORE_BENCHMARKS["dessert_count"]),
    ])

    outdoor_score = average_scores([
        score_higher_is_better(scaled.get("park_count"), METRIC_SCORE_BENCHMARKS["park_count"]),
        score_higher_is_better(scaled.get("sports_ground_count"), METRIC_SCORE_BENCHMARKS["sports_ground_count"]),
        score_higher_is_better(scaled.get("playground_count"), METRIC_SCORE_BENCHMARKS["playground_count"]),
        score_higher_is_better(scaled.get("gym_count"), METRIC_SCORE_BENCHMARKS["gym_count"]),
    ])

    mobility_score = average_scores([
        score_higher_is_better(scaled.get("train_station_count"), METRIC_SCORE_BENCHMARKS["train_station_count"]),
        score_higher_is_better(scaled.get("tram_stop_count"), METRIC_SCORE_BENCHMARKS["tram_stop_count"]),
        score_higher_is_better(scaled.get("bus_stop_count"), METRIC_SCORE_BENCHMARKS["bus_stop_count"]),
        score_lower_is_better(
            suburb.get("distance_to_cbd_km"),
            TRAVEL_SCORE_BOUNDS["distance_to_cbd_km"]["best"],
            TRAVEL_SCORE_BOUNDS["distance_to_cbd_km"]["worst"],
        ),
        score_lower_is_better(
            suburb.get("car_time_to_cbd_mins"),
            TRAVEL_SCORE_BOUNDS["car_time_to_cbd_mins"]["best"],
            TRAVEL_SCORE_BOUNDS["car_time_to_cbd_mins"]["worst"],
        ),
        score_lower_is_better(
            suburb.get("transit_time_to_cbd_mins"),
            TRAVEL_SCORE_BOUNDS["transit_time_to_cbd_mins"]["best"],
            TRAVEL_SCORE_BOUNDS["transit_time_to_cbd_mins"]["worst"],
        ),
        score_lower_is_better(
            suburb.get("walk_time_to_cbd_mins"),
            TRAVEL_SCORE_BOUNDS["walk_time_to_cbd_mins"]["best"],
            TRAVEL_SCORE_BOUNDS["walk_time_to_cbd_mins"]["worst"],
        ),
    ])

    essentials_score = average_scores([
        score_higher_is_better(scaled.get("supermarket_count"), METRIC_SCORE_BENCHMARKS["supermarket_count"]),
        score_higher_is_better(scaled.get("pharmacy_count"), METRIC_SCORE_BENCHMARKS["pharmacy_count"]),
        score_higher_is_better(scaled.get("gp_clinic_count"), METRIC_SCORE_BENCHMARKS["gp_clinic_count"]),
        score_higher_is_better(scaled.get("bank_count"), METRIC_SCORE_BENCHMARKS["bank_count"]),
    ])

    education_score = average_scores([
        score_higher_is_better(scaled.get("childcare_count"), METRIC_SCORE_BENCHMARKS["childcare_count"]),
        score_higher_is_better(scaled.get("primary_school_count"), METRIC_SCORE_BENCHMARKS["primary_school_count"]),
        score_higher_is_better(scaled.get("high_school_count"), METRIC_SCORE_BENCHMARKS["high_school_count"]),
        score_higher_is_better(scaled.get("library_count"), METRIC_SCORE_BENCHMARKS["library_count"]),
        score_higher_is_better(scaled.get("community_centre_count"), METRIC_SCORE_BENCHMARKS["community_centre_count"]),
    ])

    affordability_score = safe_float(suburb.get(PRICE_SCORE_COLUMN))

    return {
        "Social Density": social_score,
        "Active Outdoor": outdoor_score,
        "Mobility": mobility_score,
        "Everyday Essentials": essentials_score,
        "Education and Family": education_score,
        "Affordability": affordability_score,
    }


def compute_overall_score(suburb: dict) -> Optional[float]:
    category_scores = compute_category_scores(suburb)

    weighted_sum = 0.0
    total_weight_used = 0.0

    for category, weight in CATEGORY_WEIGHTS.items():
        score = safe_float(category_scores.get(category))
        if score is None:
            continue
        weighted_sum += score * weight
        total_weight_used += weight

    if total_weight_used == 0:
        return None

    return round(weighted_sum / total_weight_used, 2)


def get_score_band(score: Optional[float]) -> str:
    score = safe_float(score)
    if score is None:
        return "N/A"
    if score >= 8:
        return "Excellent"
    if score >= 6:
        return "Good"
    if score >= 4:
        return "Average"
    return "Poor"


def format_metric_value(metric_name: str, value: Optional[float]) -> str:
    if value is None:
        return "N/A"

    scale_method = METRICS[metric_name]["scale_method"]

    if scale_method == "per_km2":
        return f"{value:.2f}"

    if scale_method == "per_1000_residents":
        return f"{value:.3f}"

    return str(value)


def format_score_value(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f} / 10"


def format_travel_value(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}"


def format_currency_value(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"${value:,.0f}"


def format_price_score_value(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f} / 10"


def comparison_label(
    current: Optional[float],
    other: Optional[float],
    *,
    lower_is_better: bool = False,
    decimals: int = 2,
) -> str:
    current = safe_float(current)
    other = safe_float(other)

    if current is None or other is None:
        return "N/A"

    diff = current - other

    if abs(diff) < 1e-9:
        return "Same as other suburb"

    if lower_is_better:
        if diff < 0:
            return f"Better by {abs(diff):.{decimals}f}"
        return f"Worse by {abs(diff):.{decimals}f}"

    if diff > 0:
        return f"Better by {abs(diff):.{decimals}f}"
    return f"Worse by {abs(diff):.{decimals}f}"


def render_score_block(suburb: dict, other: dict) -> None:
    overall_score = compute_overall_score(suburb)
    other_overall_score = compute_overall_score(other)
    category_scores = compute_category_scores(suburb)
    other_category_scores = compute_category_scores(other)

    metrics = [
        (
            "Overall",
            format_score_value(overall_score),
            comparison_label(overall_score, other_overall_score),
        ),
        (
            "Rating",
            get_score_band(overall_score),
            "Weighted lifestyle score",
        ),
    ]

    strongest_category = None
    usable_scores = {k: safe_float(v) for k, v in category_scores.items() if safe_float(v) is not None}
    if usable_scores:
        strongest_category = max(usable_scores, key=usable_scores.get)
        metrics.append((
            "Best edge",
            CATEGORY_SHORT_LABELS.get(strongest_category, strongest_category),
            format_score_value(usable_scores[strongest_category]),
        ))

    for category in ["Mobility", "Affordability", "Social Density"]:
        score = category_scores.get(category)
        other_score = other_category_scores.get(category)
        metrics.append((
            CATEGORY_SHORT_LABELS[category],
            format_score_value(score),
            comparison_label(score, other_score),
        ))

    render_metric_grid(metrics)


def render_context_block(suburb: dict, other: dict) -> None:
    area = safe_float(suburb.get(AREA_COLUMN))
    population = safe_float(suburb.get(POPULATION_COLUMN))
    median_rent = safe_float(suburb.get(RENT_COLUMN))
    other_rent = safe_float(other.get(RENT_COLUMN))
    car_time = safe_float(suburb.get("car_time_to_cbd_mins"))
    transit_time = safe_float(suburb.get("transit_time_to_cbd_mins"))

    metrics = [
        (
            "Area",
            f"{area:.2f} km²" if area is not None else "N/A",
            "ABS suburb area",
        ),
        (
            "Population",
            f"{int(population):,}" if population is not None else "N/A",
            "ABS 2021 reference",
        ),
        (
            "Median rent",
            format_currency_value(median_rent),
            comparison_label(median_rent, other_rent, lower_is_better=True, decimals=0),
        ),
        (
            "Drive to CBD",
            f"{car_time:.1f} mins" if car_time is not None else "N/A",
            "Lower is better",
        ),
        (
            "Transit to CBD",
            f"{transit_time:.1f} mins" if transit_time is not None else "N/A",
            "Lower is better",
        ),
    ]

    render_metric_grid(metrics)


def build_category_detail_rows(suburb: dict, other: dict, category: str) -> List[dict]:
    rows = []
    suburb_scaled = build_scaled_metrics(suburb)
    other_scaled = build_scaled_metrics(other)

    category_score = compute_category_scores(suburb).get(category)
    other_category_score = compute_category_scores(other).get(category)
    rows.append({
        "Metric": f"{CATEGORY_SHORT_LABELS[category]} score",
        "This suburb": format_score_value(category_score),
        "Other suburb": format_score_value(other_category_score),
        "Comparison": comparison_label(category_score, other_category_score),
    })

    for metric_name, config in METRICS.items():
        if config["category"] != category:
            continue

        current_value = suburb_scaled.get(metric_name)
        other_value = other_scaled.get(metric_name)
        rows.append({
            "Metric": config["label"],
            "This suburb": format_metric_value(metric_name, current_value),
            "Other suburb": format_metric_value(metric_name, other_value),
            "Comparison": comparison_label(current_value, other_value),
        })

    for metric_name, config in TRAVEL_METRICS.items():
        if config["category"] != category:
            continue

        current_value = safe_float(suburb.get(metric_name))
        other_value = safe_float(other.get(metric_name))
        rows.append({
            "Metric": config["label"],
            "This suburb": format_travel_value(current_value),
            "Other suburb": format_travel_value(other_value),
            "Comparison": comparison_label(current_value, other_value, lower_is_better=True, decimals=1),
        })

    return rows


def render_category_metrics(suburb: dict, other: dict, category: str) -> None:
    with st.expander(category, expanded=False):
        st.dataframe(
            pd.DataFrame(build_category_detail_rows(suburb, other, category)),
            use_container_width=True,
            hide_index=True,
        )


def build_raw_metric_rows(suburb: dict) -> List[dict]:
    rows = []

    rows.append({"Metric": "Population", "Raw value": suburb.get("population")})
    rows.append({"Metric": "Suburb area (km²)", "Raw value": suburb.get("suburb_area_sq_km")})
    rows.append({"Metric": "Median weekly rent", "Raw value": suburb.get(RENT_COLUMN)})
    rows.append({"Metric": "Affordability score", "Raw value": suburb.get(PRICE_SCORE_COLUMN)})
    rows.append({"Metric": "Overall score", "Raw value": compute_overall_score(suburb)})

    category_scores = compute_category_scores(suburb)
    for category in score_keys_for_output():
        rows.append({
            "Metric": f"{CATEGORY_SHORT_LABELS[category]} score",
            "Raw value": category_scores.get(category),
        })

    for metric_name, config in METRICS.items():
        rows.append({
            "Metric": config["raw_label"],
            "Raw value": suburb.get(metric_name),
        })

    for metric_name, config in TRAVEL_METRICS.items():
        rows.append({
            "Metric": config["label"],
            "Raw value": suburb.get(metric_name),
        })

    return rows


def score_keys_for_output() -> List[str]:
    return [
        "Social Density",
        "Active Outdoor",
        "Mobility",
        "Everyday Essentials",
        "Education and Family",
        "Affordability",
    ]


def build_suburb_insight(suburb: dict, other: dict) -> str:
    scores = compute_category_scores(suburb)
    other_scores = compute_category_scores(other)
    leads = []
    for category in score_keys_for_output():
        value = safe_float(scores.get(category))
        other_value = safe_float(other_scores.get(category))
        if value is not None and other_value is not None and value > other_value:
            leads.append(CATEGORY_SHORT_LABELS[category])

    if not leads:
        return "Balanced profile with no clear category lead."
    if len(leads) == 1:
        return f"Strongest relative advantage: {leads[0]}."
    return f"Leads on {', '.join(leads[:-1])} and {leads[-1]}."


def render_suburb_card(suburb: dict, other: dict, status: str) -> None:
    suburb_title = f"{suburb['name']}, {suburb.get('state', '')}".strip().rstrip(",")
    overall_score = compute_overall_score(suburb)
    insight = build_suburb_insight(suburb, other)

    st.markdown(
        f"""
<div class="suburb-card">
    <div class="suburb-card-header">
        <div class="suburb-name">{escape(suburb_title)}</div>
        <div class="suburb-score-line">{escape(format_score_value(overall_score))} overall · {escape(insight)}</div>
        <div class="status-pill">{escape(format_status(status))}</div>
    </div>
    <div class="suburb-card-body">
        <div class="section-kicker">Profile</div>
        """,
        unsafe_allow_html=True,
    )

    render_category_score_bands(suburb, other)

    st.markdown('<br><div class="section-kicker">Overview</div>', unsafe_allow_html=True)
    render_score_block(suburb, other)

    st.markdown('<br><div class="section-kicker">Local context</div>', unsafe_allow_html=True)
    render_context_block(suburb, other)

    with st.expander("Data reference", expanded=False):
        st.json(suburb)

    with st.expander("Metric values", expanded=False):
        st.dataframe(pd.DataFrame(build_raw_metric_rows(suburb)), use_container_width=True, hide_index=True)

    st.markdown("</div></div>", unsafe_allow_html=True)


def build_summary_rows(result1: dict, result2: dict) -> List[dict]:
    summary_rows = []

    suburb1_label = build_suburb_key(result1["name"], result1["state"])
    suburb2_label = build_suburb_key(result2["name"], result2["state"])

    result1_scaled = build_scaled_metrics(result1)
    result2_scaled = build_scaled_metrics(result2)

    overall1 = compute_overall_score(result1)
    overall2 = compute_overall_score(result2)

    if overall1 is None or overall2 is None:
        better_suburb = "N/A"
    elif overall1 > overall2:
        better_suburb = suburb1_label
    elif overall2 > overall1:
        better_suburb = suburb2_label
    else:
        better_suburb = "Tie"

    summary_rows.append({
        "Metric": "Overall score",
        "Better suburb": better_suburb,
    })

    category_scores_1 = compute_category_scores(result1)
    category_scores_2 = compute_category_scores(result2)

    for category in score_keys_for_output():
        value1 = safe_float(category_scores_1.get(category))
        value2 = safe_float(category_scores_2.get(category))

        if value1 is None or value2 is None:
            better_suburb = "N/A"
        elif value1 > value2:
            better_suburb = suburb1_label
        elif value2 > value1:
            better_suburb = suburb2_label
        else:
            better_suburb = "Tie"

        summary_rows.append({
            "Metric": f"{CATEGORY_SHORT_LABELS[category]} score",
            "Better suburb": better_suburb,
        })

    for metric_name, config in METRICS.items():
        value1 = result1_scaled.get(metric_name)
        value2 = result2_scaled.get(metric_name)

        if value1 is None or value2 is None:
            better_suburb = "N/A"
        elif value1 > value2:
            better_suburb = suburb1_label
        elif value2 > value1:
            better_suburb = suburb2_label
        else:
            better_suburb = "Tie"

        summary_rows.append({
            "Metric": config["label"],
            "Better suburb": better_suburb,
        })

    for metric_name, config in TRAVEL_METRICS.items():
        value1 = safe_float(result1.get(metric_name))
        value2 = safe_float(result2.get(metric_name))

        if value1 is None or value2 is None:
            better_suburb = "N/A"
        elif value1 < value2:
            better_suburb = suburb1_label
        elif value2 < value1:
            better_suburb = suburb2_label
        else:
            better_suburb = "Tie"

        summary_rows.append({
            "Metric": config["label"],
            "Better suburb": better_suburb,
        })

    return summary_rows


def get_comparison_winner(result1: dict, result2: dict) -> Tuple[str, Optional[float], Optional[float]]:
    suburb1_label = build_suburb_key(result1["name"], result1["state"])
    suburb2_label = build_suburb_key(result2["name"], result2["state"])
    overall1 = compute_overall_score(result1)
    overall2 = compute_overall_score(result2)

    if overall1 is None or overall2 is None:
        return "Not enough data for an overall winner", overall1, overall2
    if overall1 > overall2:
        return suburb1_label, overall1, overall2
    if overall2 > overall1:
        return suburb2_label, overall1, overall2
    return "Tie", overall1, overall2


def build_category_comparison_rows(result1: dict, result2: dict) -> List[dict]:
    suburb1_label = build_suburb_key(result1["name"], result1["state"])
    suburb2_label = build_suburb_key(result2["name"], result2["state"])
    scores1 = compute_category_scores(result1)
    scores2 = compute_category_scores(result2)

    rows = []
    for category in score_keys_for_output():
        value1 = safe_float(scores1.get(category))
        value2 = safe_float(scores2.get(category))

        if value1 is None or value2 is None:
            leader = "N/A"
        elif abs(value1 - value2) < 1e-9:
            leader = "Tie"
        elif value1 > value2:
            leader = suburb1_label
        else:
            leader = suburb2_label

        rows.append({
            "Category": CATEGORY_SHORT_LABELS[category],
            suburb1_label: format_score_value(value1),
            suburb2_label: format_score_value(value2),
            "Leader": leader,
        })

    return rows


def get_category_leaders(result1: dict, result2: dict) -> Tuple[List[str], List[str]]:
    suburb1_label = build_suburb_key(result1["name"], result1["state"])
    suburb2_label = build_suburb_key(result2["name"], result2["state"])
    rows = build_category_comparison_rows(result1, result2)
    leads1 = [row["Category"] for row in rows if row["Leader"] == suburb1_label]
    leads2 = [row["Category"] for row in rows if row["Leader"] == suburb2_label]
    return leads1, leads2


def render_winner_summary(result1: dict, result2: dict) -> None:
    suburb1_label = build_suburb_key(result1["name"], result1["state"])
    suburb2_label = build_suburb_key(result2["name"], result2["state"])
    winner, overall1, overall2 = get_comparison_winner(result1, result2)
    leads1, leads2 = get_category_leaders(result1, result2)

    if winner == "Tie":
        title = "This one is almost dead even."
    elif winner.startswith("Not enough"):
        title = winner
    else:
        title = f"{winner} has the stronger overall profile."

    score_gap = None
    if overall1 is not None and overall2 is not None:
        score_gap = abs(overall1 - overall2)

    score_line = f"{suburb1_label}: {format_score_value(overall1)} · {suburb2_label}: {format_score_value(overall2)}"
    lead1_text = ", ".join(leads1) if leads1 else "No category lead"
    lead2_text = ", ".join(leads2) if leads2 else "No category lead"
    gap_text = f"Score gap: {score_gap:.2f}" if score_gap is not None else "Score gap: N/A"

    st.markdown(
        f"""
<div class="result-card">
    <div class="section-kicker">At a glance</div>
    <div class="winner-title">{escape(title)}</div>
    <div class="winner-subtext">{escape(score_line)} · {escape(gap_text)}</div>
    <div class="score-strip">
        <div class="score-strip-tile">
            <div class="tile-label">{escape(suburb1_label)}</div>
            <div class="tile-value">{escape(format_score_value(overall1))}</div>
            <div class="tile-sub">Leads: {escape(lead1_text)}</div>
        </div>
        <div class="score-strip-tile">
            <div class="tile-label">{escape(suburb2_label)}</div>
            <div class="tile-value">{escape(format_score_value(overall2))}</div>
            <div class="tile-sub">Leads: {escape(lead2_text)}</div>
        </div>
    </div>
</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="comparison-table-card"><div class="section-kicker">Category view</div>', unsafe_allow_html=True)
    st.dataframe(
        pd.DataFrame(build_category_comparison_rows(result1, result2)),
        use_container_width=True,
        hide_index=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)


def render_scoring_explanation() -> None:
    with st.expander("About the score"):
        st.markdown(
            """
**Overall score** combines six 0–10 components: Social, Outdoor, Mobility, Essentials, Education and Affordability.

**Weights**  
Social: 20% · Outdoor: 15% · Mobility: 20% · Essentials: 15% · Education: 10% · Affordability: 20%

**Amenity metrics**  
Social, outdoor and mobility stop metrics are scaled per km². Essentials and education/family metrics are scaled per 1,000 residents. Those values are converted into benchmark-based 0–10 scores.

**Travel metrics**  
Lower is better. Distance and travel time to the CBD are converted into 0–10 using best-to-worst bounds.

**Affordability**  
Based on ABS median weekly rent. Lower rent gives a higher affordability score.

**Data sources**  
Places data API, Google Geocoding API, Google Routes API and ABS 2021 Census reference data.
            """
        )


# --------------------------------------------------
# UI
# --------------------------------------------------

apply_custom_styles()
render_hero()

reference_df = load_reference_data()
if reference_df.empty:
    st.warning(
        "Reference CSV not found. Create a file named 'pipeline/data/suburb_reference.csv' with columns: "
        "name, state, population, suburb_area_sq_km, median_rent_weekly. Until then, density metrics that depend "
        "on population/area and the affordability metric may show as N/A."
    )
else:
    st.markdown(
        f"""
<div class="hero-meta-row" style="margin-top:-0.35rem;margin-bottom:1rem;">
    <div class="hero-pill">Reference data loaded: {len(reference_df):,} suburbs</div>
    <div class="hero-pill">Fast repeat searches</div>
    <div class="hero-pill">Suburb scorecards</div>
</div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    """
<div class="input-card">
    <div class="section-kicker">Compare</div>
    <div class="section-heading">Choose two suburbs and see how they stack up.</div>
    <div class="section-copy">
        Start with the big picture, then open up the detail when you need it.
        Existing suburbs load from cache; missing metrics are fetched and saved.
    </div>
</div>
    """,
    unsafe_allow_html=True,
)

with st.form("compare_form"):
    left_col, middle_col, right_col = st.columns([1, 0.12, 1])

    with left_col:
        suburb1 = st.text_input("First suburb", placeholder="e.g. Richmond")
        state1 = st.selectbox("First state/territory", AUSTRALIAN_STATES, index=1)

    with middle_col:
        st.markdown("<br><br><div style='text-align:center;color:#F8D57E;font-weight:900;letter-spacing:0.12em;'>VS</div>", unsafe_allow_html=True)

    with right_col:
        suburb2 = st.text_input("Second suburb", placeholder="e.g. New Farm")
        state2 = st.selectbox("Second state/territory", AUSTRALIAN_STATES, index=2)

    submitted = st.form_submit_button("Compare suburbs")

if submitted:
    if not suburb1 or not suburb2:
        st.warning("Please enter both suburbs.")
    else:
        suburb1_clean = normalize_suburb_name(suburb1)
        suburb2_clean = normalize_suburb_name(suburb2)
        state1_clean = normalize_state_code(state1)
        state2_clean = normalize_state_code(state2)

        if suburb1_clean == suburb2_clean and state1_clean == state2_clean:
            st.warning("Please enter two different suburb/state combinations.")
        else:
            try:
                with st.spinner("Building comparison brief..."):
                    result1, status1 = get_or_create_suburb(suburb1_clean, state1_clean)
                    result2, status2 = get_or_create_suburb(suburb2_clean, state2_clean)

                render_winner_summary(result1, result2)

                st.markdown(
                    """
<div class="method-card">
    <div class="section-kicker">Method note</div>
    <div class="section-copy" style="margin-bottom:0;">
        Density metrics are normalised before scoring so the comparison does not become a simple suburb-size contest.
        Lifestyle and transport stop metrics are shown per km², essentials and family services are shown per 1,000 residents,
        travel metrics stay lower-is-better, and affordability uses median weekly rent converted into a 0–10 score.
    </div>
</div>
                    """,
                    unsafe_allow_html=True,
                )

                left, right = st.columns(2, gap="large")
                with left:
                    render_suburb_card(result1, result2, status1)
                with right:
                    render_suburb_card(result2, result1, status2)

                with st.expander("Full comparison summary", expanded=False):
                    st.dataframe(pd.DataFrame(build_summary_rows(result1, result2)), use_container_width=True, hide_index=True)

                render_scoring_explanation()

            except requests.HTTPError as e:
                st.error("Google API request failed.")
                try:
                    st.json(e.response.json())
                except Exception:
                    st.write(str(e))

            except Exception as e:
                st.error("Connection or query failed.")
                st.write(str(e))
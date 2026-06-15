"""SQLite / Postgres storage layer.

Two tables:
  - garmin_daily : one row per calendar date of Garmin-sourced metrics
  - weight       : one row per calendar date of manually entered body weight

Both are keyed by an ISO date string ("YYYY-MM-DD"). Writes are upserts so
re-syncing a day or re-entering a weight just overwrites the existing row.

Backend is chosen at runtime:
  - If DATABASE_URL is set (e.g. a Supabase Postgres pooler URL) -> Postgres.
  - Otherwise -> a local SQLite file (config.DB_PATH).

The SQL is identical across both engines (TEXT/INTEGER/REAL and
`ON CONFLICT(...) DO UPDATE` are supported by each); only the connection and the
parameter placeholder differ.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime

import pandas as pd
from dotenv import load_dotenv

from config import DB_PATH

# Load .env before reading DATABASE_URL so the backend choice is correct
# regardless of import order. (On Streamlit Cloud there is no .env; app.py
# bridges st.secrets into the environment before importing this module.)
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
IS_POSTGRES = bool(DATABASE_URL)


def _q(sql: str) -> str:
    """Translate '?' placeholders to '%s' for Postgres; leave as-is for SQLite."""
    return sql.replace("?", "%s") if IS_POSTGRES else sql


@contextmanager
def _connect():
    if IS_POSTGRES:
        import psycopg

        conn = psycopg.connect(DATABASE_URL, autocommit=False)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def _query_df(sql: str) -> pd.DataFrame:
    """Run a SELECT and return a DataFrame, backend-agnostic."""
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=cols)


def init_db():
    """Create tables if they don't exist. Safe to call on every launch."""
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS garmin_daily (
                date              TEXT PRIMARY KEY,
                total_calories    INTEGER,
                active_calories   INTEGER,
                resting_hr        INTEGER,
                sleep_seconds     INTEGER,
                sleep_deep        INTEGER,
                sleep_light       INTEGER,
                sleep_rem         INTEGER,
                sleep_awake       INTEGER,
                body_battery_high INTEGER,
                body_battery_low  INTEGER,
                steps             INTEGER,
                updated_at        TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS weight (
                date       TEXT PRIMARY KEY,
                weight_kg  REAL,
                updated_at TEXT
            )
            """
        )


# --- Garmin daily metrics -----------------------------------------------

GARMIN_COLUMNS = [
    "total_calories",
    "active_calories",
    "resting_hr",
    "sleep_seconds",
    "sleep_deep",
    "sleep_light",
    "sleep_rem",
    "sleep_awake",
    "body_battery_high",
    "body_battery_low",
    "steps",
]


def upsert_garmin_day(day: str, metrics: dict):
    """Insert or replace one day's Garmin metrics.

    `metrics` may contain any subset of GARMIN_COLUMNS; missing keys store NULL.
    """
    cols = ", ".join(GARMIN_COLUMNS)
    placeholders = ", ".join(["?"] * len(GARMIN_COLUMNS))
    values = [metrics.get(c) for c in GARMIN_COLUMNS]
    sql = f"""
        INSERT INTO garmin_daily (date, {cols}, updated_at)
        VALUES (?, {placeholders}, ?)
        ON CONFLICT(date) DO UPDATE SET
            {", ".join(f"{c}=excluded.{c}" for c in GARMIN_COLUMNS)},
            updated_at=excluded.updated_at
    """
    with _connect() as conn:
        conn.cursor().execute(
            _q(sql), [day, *values, datetime.now().isoformat(timespec="seconds")]
        )


def get_existing_garmin_dates() -> set:
    df = _query_df("SELECT date FROM garmin_daily")
    return set(df["date"].tolist()) if not df.empty else set()


def latest_garmin_date() -> str | None:
    df = _query_df("SELECT MAX(date) AS d FROM garmin_daily")
    if df.empty or pd.isna(df["d"].iloc[0]):
        return None
    return str(df["d"].iloc[0])


# --- Weight --------------------------------------------------------------

def upsert_weight(day: str, weight_kg: float):
    sql = """
        INSERT INTO weight (date, weight_kg, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
            weight_kg=excluded.weight_kg,
            updated_at=excluded.updated_at
    """
    with _connect() as conn:
        conn.cursor().execute(
            _q(sql),
            [day, float(weight_kg), datetime.now().isoformat(timespec="seconds")],
        )


def latest_weight() -> float | None:
    df = _query_df("SELECT weight_kg FROM weight ORDER BY date DESC LIMIT 1")
    if df.empty:
        return None
    return float(df["weight_kg"].iloc[0])


# --- Combined read for the dashboard ------------------------------------

def load_dataframe() -> pd.DataFrame:
    """Return one row per date with all Garmin metrics + weight, joined.

    The date axis spans from the earliest record (in either table) to today,
    with no gaps, so charts and moving averages handle missing days cleanly.
    """
    garmin = _query_df("SELECT * FROM garmin_daily")
    weight = _query_df("SELECT date, weight_kg FROM weight")

    if garmin.empty and weight.empty:
        return pd.DataFrame()

    dates = pd.concat([garmin.get("date", pd.Series(dtype=str)),
                       weight.get("date", pd.Series(dtype=str))])
    dates = pd.to_datetime(dates)
    start = dates.min()
    end = pd.Timestamp(date.today())
    full = pd.DataFrame({"date": pd.date_range(start, end, freq="D")})

    if not garmin.empty:
        garmin["date"] = pd.to_datetime(garmin["date"])
    if not weight.empty:
        weight["date"] = pd.to_datetime(weight["date"])

    df = full.merge(garmin, on="date", how="left").merge(weight, on="date", how="left")
    df = df.sort_values("date").reset_index(drop=True)
    return df

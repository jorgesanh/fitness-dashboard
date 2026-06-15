"""SQLite storage layer.

Two tables:
  - garmin_daily : one row per calendar date of Garmin-sourced metrics
  - weight       : one row per calendar date of manually entered body weight

Both are keyed by an ISO date string ("YYYY-MM-DD"). Writes are upserts so
re-syncing a day or re-entering a weight just overwrites the existing row.
"""

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime

import pandas as pd

from config import DB_PATH


@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist. Safe to call on every launch."""
    with _connect() as conn:
        conn.execute(
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
        conn.execute(
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
    with _connect() as conn:
        conn.execute(
            f"""
            INSERT INTO garmin_daily (date, {cols}, updated_at)
            VALUES (?, {placeholders}, ?)
            ON CONFLICT(date) DO UPDATE SET
                {", ".join(f"{c}=excluded.{c}" for c in GARMIN_COLUMNS)},
                updated_at=excluded.updated_at
            """,
            [day, *values, datetime.now().isoformat(timespec="seconds")],
        )


def get_existing_garmin_dates() -> set:
    with _connect() as conn:
        rows = conn.execute("SELECT date FROM garmin_daily").fetchall()
    return {r["date"] for r in rows}


def latest_garmin_date() -> str | None:
    with _connect() as conn:
        row = conn.execute("SELECT MAX(date) AS d FROM garmin_daily").fetchone()
    return row["d"] if row and row["d"] else None


# --- Weight --------------------------------------------------------------

def upsert_weight(day: str, weight_kg: float):
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO weight (date, weight_kg, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                weight_kg=excluded.weight_kg,
                updated_at=excluded.updated_at
            """,
            [day, float(weight_kg), datetime.now().isoformat(timespec="seconds")],
        )


def latest_weight() -> float | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT weight_kg FROM weight ORDER BY date DESC LIMIT 1"
        ).fetchone()
    return row["weight_kg"] if row else None


# --- Combined read for the dashboard ------------------------------------

def load_dataframe() -> pd.DataFrame:
    """Return one row per date with all Garmin metrics + weight, joined.

    The date axis spans from the earliest record (in either table) to today,
    with no gaps, so charts and moving averages handle missing days cleanly.
    """
    with _connect() as conn:
        garmin = pd.read_sql_query("SELECT * FROM garmin_daily", conn)
        weight = pd.read_sql_query("SELECT date, weight_kg FROM weight", conn)

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

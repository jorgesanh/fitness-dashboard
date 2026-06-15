"""Derived metrics: moving averages, trend rates, recovery flags, status reads.

All functions take the joined dataframe from db.load_dataframe() (one row per
date, ascending) and are pure — no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from config import (
    AGGRESSIVE_RATE,
    KCAL_PER_KG,
    STALL_BAND_KG,
    TARGET_RATE_HIGH,
    TARGET_RATE_LOW,
)


def add_weight_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Add a 7-day centered-ish moving average of weight.

    Uses a trailing 7-day mean over available points (min 2) so the line
    starts early and isn't blanked by the occasional skipped weigh-in.
    """
    df = df.copy()
    if "weight_kg" in df:
        df["weight_ma7"] = (
            df["weight_kg"].rolling(window=7, min_periods=2).mean()
        )
    return df


def _slope_per_day(series: pd.Series) -> float | None:
    """Least-squares slope (units per day) of a series indexed 0..n-1,
    ignoring NaNs. Returns None if fewer than 2 points."""
    y = series.dropna()
    if len(y) < 2:
        return None
    x = np.arange(len(series))[series.notna().to_numpy()]
    slope = np.polyfit(x, y.to_numpy(), 1)[0]
    return float(slope)


@dataclass
class Headline:
    avg_weight: float | None          # current 7-day average weight (kg)
    rate_kg_per_week: float | None    # signed: negative = losing weight
    avg_expenditure: float | None     # mean daily total calories over window
    implied_deficit: float | None     # kcal/day implied by the weight trend
    window_days: int


def headline(df: pd.DataFrame, window_days: int = 14) -> Headline:
    """Compute the headline panel over the trailing `window_days`."""
    if df.empty:
        return Headline(None, None, None, None, window_days)

    window = df.tail(window_days)

    ma = window["weight_ma7"].dropna() if "weight_ma7" in window else pd.Series(dtype=float)
    avg_weight = float(ma.iloc[-1]) if not ma.empty else None

    # Rate from the moving-average slope, scaled to kg/week.
    slope = _slope_per_day(window["weight_ma7"]) if "weight_ma7" in window else None
    rate = slope * 7 if slope is not None else None

    expenditure = None
    if "total_calories" in window:
        exp = window["total_calories"].dropna()
        if not exp.empty:
            expenditure = float(exp.mean())

    # Implied daily energy deficit from the weight trend.
    # losing X kg/week -> X * 7700 kcal / 7 days deficit per day.
    implied_deficit = None
    if rate is not None:
        implied_deficit = (-rate) * KCAL_PER_KG / 7  # positive when losing

    return Headline(avg_weight, rate, expenditure, implied_deficit, window_days)


@dataclass
class Status:
    key: str       # "on_target" | "aggressive" | "stalled" | "slow" | "gaining" | "unknown"
    label: str
    nudge: str


def status_read(df: pd.DataFrame, head: Headline) -> Status:
    """Interpret the rate of change into a status + one-line nudge."""
    if head.rate_kg_per_week is None:
        return Status("unknown", "Not enough data",
                      "Log a few more days of weight to establish a trend.")

    loss = -head.rate_kg_per_week  # positive = losing

    # Stalled: 14-day moving-average barely moved.
    if _is_stalled(df):
        return Status(
            "stalled", "Stalled",
            "Trend has been flat for 2+ weeks — tighten intake ~150–200 kcal "
            "or add a little activity to restart the loss.",
        )

    if loss > AGGRESSIVE_RATE:
        return Status(
            "aggressive", "Too aggressive",
            f"Losing {loss:.2f} kg/wk risks muscle and recovery — eat a bit "
            "more and aim for 0.4–0.7 kg/wk.",
        )

    if TARGET_RATE_LOW <= loss <= AGGRESSIVE_RATE:
        return Status(
            "on_target", "On target",
            f"{loss:.2f} kg/wk is right in the fat-loss sweet spot — hold this.",
        )

    if 0 < loss < TARGET_RATE_LOW:
        return Status(
            "slow", "Slow but steady",
            f"Losing {loss:.2f} kg/wk — fine if intentional, otherwise trim "
            "~150 kcal to reach 0.4–0.7 kg/wk.",
        )

    return Status(
        "gaining", "Gaining",
        f"Trend is up ~{abs(loss):.2f} kg/wk — recheck intake if you're "
        "still trying to cut.",
    )


def _is_stalled(df: pd.DataFrame) -> bool:
    if "weight_ma7" not in df:
        return False
    ma = df[["date", "weight_ma7"]].dropna()
    if len(ma) < 2:
        return False
    last_date = ma["date"].iloc[-1]
    window = ma[ma["date"] >= last_date - pd.Timedelta(days=14)]
    if len(window) < 2:
        return False
    change = window["weight_ma7"].iloc[-1] - window["weight_ma7"].iloc[0]
    span_days = (window["date"].iloc[-1] - window["date"].iloc[0]).days
    return span_days >= 12 and abs(change) < STALL_BAND_KG


@dataclass
class Recovery:
    rhr_slope: float | None        # bpm per day
    sleep_slope: float | None      # hours per day
    bb_slope: float | None         # body battery points per day
    under_recovering: bool
    note: str


def recovery_read(df: pd.DataFrame, window_days: int = 14) -> Recovery:
    """Trend resting HR, sleep, and Body Battery; flag under-recovery when RHR
    trends up while sleep and Body Battery trend down."""
    window = df.tail(window_days)

    rhr_slope = _slope_per_day(window["resting_hr"]) if "resting_hr" in window else None

    sleep_slope = None
    if "sleep_seconds" in window:
        sleep_hours = window["sleep_seconds"] / 3600.0
        sleep_slope = _slope_per_day(sleep_hours)

    bb_slope = _slope_per_day(window["body_battery_high"]) if "body_battery_high" in window else None

    have_rhr = rhr_slope is not None
    have_bb = bb_slope is not None
    have_sleep = sleep_slope is not None

    # Full signal: RHR rising while sleep AND Body Battery fall.
    under = (
        have_rhr and rhr_slope > 0
        and have_sleep and sleep_slope < 0
        and have_bb and bb_slope < 0
    )

    if under:
        note = ("Resting HR is rising while sleep and Body Battery fall — a "
                "classic under-recovery signal. Ease the deficit or training "
                "load for a few days.")
    elif not have_rhr and not have_bb and not have_sleep:
        note = "No recovery data yet — sync Garmin to populate this."
    elif not have_rhr and not have_bb:
        # Device isn't reporting heart rate / Body Battery — sleep-only read.
        if have_sleep and sleep_slope < -0.05:  # losing >~3 min/night over window
            under = True
            note = ("Sleep is trending down. Your device isn't reporting heart "
                    "rate or Body Battery, so protect sleep and watch training "
                    "load as your under-recovery early-warning.")
        else:
            note = ("Sleep looks steady. Note: this device isn't reporting "
                    "heart rate or Body Battery, so recovery is sleep-only.")
    else:
        note = "Recovery markers look stable."

    return Recovery(rhr_slope, sleep_slope, bb_slope, under, note)

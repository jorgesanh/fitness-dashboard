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

# A weekly rate of weight change is only meaningful once there are enough
# weigh-ins over enough days — otherwise day-to-day water/food noise (e.g. a
# 0.5 kg jump overnight) gets extrapolated into a nonsense "kg/week".
MIN_RATE_WEIGHINS = 6
MIN_RATE_SPAN_DAYS = 10


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

    # Rate from the moving-average slope, scaled to kg/week — but only once
    # there are enough weigh-ins spanning enough days to be meaningful.
    rate = None
    if "weight_kg" in window:
        weighed = window.dropna(subset=["weight_kg"])
        n_weigh = len(weighed)
        span = ((weighed["date"].iloc[-1] - weighed["date"].iloc[0]).days
                if n_weigh else 0)
        if n_weigh >= MIN_RATE_WEIGHINS and span >= MIN_RATE_SPAN_DAYS:
            slope = _slope_per_day(window["weight_ma7"])
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
        return Status("unknown", "Building your trend",
                      "A reliable weekly rate needs ~10+ days of regular weigh-ins — "
                      "keep logging daily and it'll appear here.")

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


# Recovery thresholds. We judge on ABSOLUTE levels, not bare slopes — a
# downward sleep slope from a 12h outlier to a healthy 8h is not a problem.
MIN_TREND_POINTS = 5        # need this many days before trusting a slope
SLEEP_LOW_H = 6.5           # avg below this is genuinely insufficient
RHR_RISE_PER_DAY = 0.2      # bpm/day rise that counts as meaningful
BB_FALL_PER_DAY = 0.8       # Body Battery points/day fall that counts


@dataclass
class Recovery:
    rhr_slope: float | None        # bpm per day (None until enough data)
    sleep_slope: float | None      # hours per day
    bb_slope: float | None         # body battery points per day
    avg_sleep_h: float | None      # recent average nightly sleep (hours)
    under_recovering: bool
    note: str


def _trend_slope(window: pd.DataFrame, col: str, transform=None) -> float | None:
    """Slope per day, but only once there are enough points to be meaningful."""
    if col not in window:
        return None
    series = window[col]
    if transform is not None:
        series = transform(series)
    if series.dropna().shape[0] < MIN_TREND_POINTS:
        return None
    return _slope_per_day(series)


def recovery_read(df: pd.DataFrame, window_days: int = 14) -> Recovery:
    """Read recovery from resting HR, sleep, and Body Battery.

    Under-recovery is flagged only when at least TWO signals are genuinely
    adverse in absolute terms (RHR meaningfully rising, sleep actually low,
    Body Battery meaningfully falling) — not when a single metric merely
    trends down while still in a healthy range.
    """
    window = df.tail(window_days)

    rhr_slope = _trend_slope(window, "resting_hr")
    sleep_slope = _trend_slope(window, "sleep_seconds", transform=lambda s: s / 3600.0)
    bb_slope = _trend_slope(window, "body_battery_high")

    sleep_h = (window["sleep_seconds"].dropna() / 3600.0) if "sleep_seconds" in window else pd.Series(dtype=float)
    avg_sleep = float(sleep_h.tail(7).mean()) if not sleep_h.empty else None

    have_any = any(
        (window[c].notna().any() if c in window else False)
        for c in ("resting_hr", "sleep_seconds", "body_battery_high")
    )

    # Adverse signals, each requiring a genuinely concerning absolute state.
    signals = []
    if rhr_slope is not None and rhr_slope > RHR_RISE_PER_DAY:
        signals.append("resting HR trending up")
    if avg_sleep is not None and avg_sleep < SLEEP_LOW_H:
        signals.append(f"sleep averaging {avg_sleep:.1f}h")
    if bb_slope is not None and bb_slope < -BB_FALL_PER_DAY:
        signals.append("Body Battery trending down")

    under = len(signals) >= 2

    if under:
        note = ("Watch recovery — " + ", ".join(signals) +
                ". Consider easing the deficit or training load for a few days.")
    elif avg_sleep is not None and avg_sleep < SLEEP_LOW_H:
        note = (f"Sleep is on the low side ({avg_sleep:.1f}h avg). Prioritise it "
                "to protect recovery while cutting.")
    elif avg_sleep is not None:
        note = f"Recovery looks solid — averaging {avg_sleep:.1f}h sleep."
    elif not have_any:
        note = "No recovery data yet — sync Garmin to populate this."
    else:
        note = "Recovery markers look stable."

    return Recovery(rhr_slope, sleep_slope, bb_slope, avg_sleep, under, note)

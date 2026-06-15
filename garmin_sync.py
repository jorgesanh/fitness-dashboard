"""Garmin Connect integration.

Uses the `python-garminconnect` library's native auth engine (the official
Connect mobile SSO flow). We do NOT touch `garth` directly. Tokens are cached
on disk (config.TOKEN_STORE) so we don't re-login every run — which also avoids
Garmin's aggressive login rate-limiting (HTTP 429).

Login can require MFA. Because Streamlit reruns the script top-to-bottom, we
can't block on input(). Instead `login()` returns a status and, when MFA is
needed, the opaque client state, which the caller stashes in session_state and
feeds back to `resume_mfa()` once the user types their code.

Two non-obvious details this module works around (both verified against
garminconnect 0.3.6):
  - With return_on_mfa=True, a *successful* (no-MFA) login returns early WITHOUT
    persisting the token or loading the profile. So after any fresh login we
    explicitly dump the token and ensure the display name is loaded.
  - Several daily endpoints (stats, steps, resting HR) build their URL from the
    account's display name; if it isn't loaded those calls fail with
    "Display name is not set". _ensure_display_name() backfills it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

from config import BACKFILL_DAYS, TOKEN_STORE
import db

load_dotenv()


# --- Login result types --------------------------------------------------

@dataclass
class LoginOk:
    client: object


@dataclass
class LoginNeedsMFA:
    client: object
    state: object


@dataclass
class LoginFailed:
    message: str


def _new_garmin(email=None, password=None):
    # Imported lazily so the app can still start (and show cached data) even
    # if the garmin libraries aren't importable for some reason.
    from garminconnect import Garmin

    if email is None:
        return Garmin()
    return Garmin(email=email, password=password, return_on_mfa=True)


def _token_path() -> str:
    return str(Path(TOKEN_STORE).expanduser())


def login():
    """Attempt login, preferring the cached token.

    Returns LoginOk | LoginNeedsMFA | LoginFailed. Never raises.
    """
    # 1) Cached-token path: no credentials, no SSO, no MFA, no 429.
    try:
        client = _new_garmin()
        client.login(_token_path())  # loads token + profile if present
        _ensure_display_name(client)
        if getattr(client, "display_name", None):
            return LoginOk(client)
    except Exception:
        pass  # no/invalid cached token — fall through to credential login

    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")
    if not email or not password:
        return LoginFailed(
            "No cached session and GARMIN_EMAIL / GARMIN_PASSWORD are not set. "
            "Copy .env.example to .env and fill in your credentials."
        )

    # 2) Fresh credential login, detecting MFA without blocking.
    try:
        client = _new_garmin(email, password)
        mfa_status, state = client.login(_token_path())
    except Exception as exc:
        msg = str(exc)
        if "429" in msg or "Too many" in msg:
            return LoginFailed(
                "Garmin is rate-limiting logins (HTTP 429). Wait a few minutes "
                "and try syncing again — once a token is cached this won't recur."
            )
        return LoginFailed(f"Garmin login failed: {exc}")

    if mfa_status == "needs_mfa":
        return LoginNeedsMFA(client=client, state=state)

    _finalize(client)
    return LoginOk(client)


def resume_mfa(client, state, code: str):
    """Complete an MFA login with the user-supplied code."""
    try:
        client.resume_login(state, code.strip())
    except Exception as exc:
        return LoginFailed(f"MFA verification failed: {exc}")
    _finalize(client)
    return LoginOk(client)


# --- Post-login finalisation --------------------------------------------

def _finalize(client):
    """After a fresh (non-cached) login: persist the token and make sure the
    display name is loaded. The library skips both when return_on_mfa is set."""
    _dump_token(client)
    _ensure_display_name(client)


def _dump_token(client):
    try:
        path = _token_path()
        os.makedirs(path, exist_ok=True)
        client.client.dump(path)  # garth client lives at client.client
    except Exception:
        # Non-fatal: we just won't have a cached token next time.
        pass


def _ensure_display_name(client):
    """Several endpoints need client.display_name. Populate it if missing."""
    if getattr(client, "display_name", None):
        return
    try:
        client._load_profile_and_settings()
    except Exception:
        try:
            sp = client.connectapi("/userprofile-service/socialProfile") or {}
            client.display_name = sp.get("displayName")
        except Exception:
            pass


# --- Per-day metric extraction ------------------------------------------

def _fetch_day(client, day: str) -> dict:
    """Pull all tracked metrics for one ISO date. Each metric is guarded so a
    single missing/failed field doesn't lose the whole day."""
    _ensure_display_name(client)
    metrics: dict = {}

    # Daily summary: calories, resting HR, steps.
    try:
        stats = client.get_stats(day) or {}
        metrics["total_calories"] = _as_int(stats.get("totalKilocalories"))
        metrics["active_calories"] = _as_int(stats.get("activeKilocalories"))
        metrics["resting_hr"] = _as_int(stats.get("restingHeartRate"))
        metrics["steps"] = _as_int(stats.get("totalSteps"))
    except Exception:
        pass

    # Resting HR often isn't in the daily summary — use the dedicated endpoint.
    if metrics.get("resting_hr") is None:
        metrics["resting_hr"] = _rhr_from_day(client, day)

    # Steps fallback if the summary didn't carry them.
    if metrics.get("steps") is None:
        try:
            steps_data = client.get_steps_data(day) or []
            total = sum(s.get("steps", 0) or 0 for s in steps_data)
            if total:
                metrics["steps"] = int(total)
        except Exception:
            pass

    # Sleep duration + stages.
    try:
        sleep = client.get_sleep_data(day) or {}
        dto = sleep.get("dailySleepDTO") or {}
        metrics["sleep_seconds"] = _as_int(dto.get("sleepTimeSeconds"))
        metrics["sleep_deep"] = _as_int(dto.get("deepSleepSeconds"))
        metrics["sleep_light"] = _as_int(dto.get("lightSleepSeconds"))
        metrics["sleep_rem"] = _as_int(dto.get("remSleepSeconds"))
        metrics["sleep_awake"] = _as_int(dto.get("awakeSleepSeconds"))
    except Exception:
        pass

    # Body Battery: store the day's peak (high) and trough (low).
    try:
        bb = client.get_body_battery(day, day) or []
        high, low = _body_battery_range(bb)
        metrics["body_battery_high"] = high
        metrics["body_battery_low"] = low
    except Exception:
        pass

    return metrics


def _rhr_from_day(client, day):
    """Resting HR from the dedicated endpoint:
    allMetrics.metricsMap.WELLNESS_RESTING_HEART_RATE[].value"""
    try:
        data = client.get_rhr_day(day) or {}
        metrics_map = (data.get("allMetrics") or {}).get("metricsMap") or {}
        for item in metrics_map.get("WELLNESS_RESTING_HEART_RATE", []) or []:
            if item.get("value") is not None:
                return _as_int(item["value"])
    except Exception:
        pass
    return None


def _body_battery_range(bb_list):
    """bodyBatteryValuesArray rows look like [timestamp_ms, level] (the level
    may be null when nothing was recorded). Older payloads use
    [timestamp_ms, "MEASURED", level]. Grab the first numeric 0–100 per row."""
    levels = []
    for entry in bb_list or []:
        for row in entry.get("bodyBatteryValuesArray", []) or []:
            for v in row[1:]:
                if isinstance(v, (int, float)) and 0 <= v <= 100:
                    levels.append(int(v))
                    break
    if not levels:
        return None, None
    return max(levels), min(levels)


def _as_int(value):
    if value is None:
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


# --- Sync orchestration --------------------------------------------------

def sync(client, full_backfill: bool = False, progress=None) -> int:
    """Fetch and store any missing days.

    On first run (or full_backfill=True) covers the last BACKFILL_DAYS. On
    later runs only fills dates we don't already have, up to today. Today is
    always re-fetched since its numbers are still accumulating.

    Returns the number of days fetched. `progress` is an optional callback
    (fraction_0_to_1, label) for a UI progress bar.
    """
    today = date.today()
    existing = db.get_existing_garmin_dates()

    if full_backfill or not existing:
        start = today - timedelta(days=BACKFILL_DAYS)
    else:
        latest = db.latest_garmin_date()
        start = date.fromisoformat(latest) if latest else today - timedelta(days=BACKFILL_DAYS)

    days = []
    d = start
    while d <= today:
        iso = d.isoformat()
        # Re-fetch today (still accumulating) and any gap days.
        if d == today or iso not in existing:
            days.append(iso)
        d += timedelta(days=1)

    for i, iso in enumerate(days):
        metrics = _fetch_day(client, iso)
        if metrics:
            db.upsert_garmin_day(iso, metrics)
        if progress:
            progress((i + 1) / len(days), iso)

    return len(days)

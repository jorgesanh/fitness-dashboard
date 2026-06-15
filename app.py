"""Personal fat-loss & recovery dashboard.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import os
from datetime import date, datetime

import pandas as pd
import streamlit as st

# Bridge Streamlit Cloud secrets -> environment BEFORE importing db/garmin_sync,
# which read DATABASE_URL / GARMIN_* from os.environ at import time. Locally this
# is a no-op (values come from .env); on Streamlit Cloud the secrets you paste in
# the dashboard land here.
try:
    for _k in ("DATABASE_URL", "GARMIN_EMAIL", "GARMIN_PASSWORD"):
        if _k not in os.environ and _k in st.secrets:
            os.environ[_k] = str(st.secrets[_k])
except Exception:
    pass

import db
import garmin_sync
import metrics
import ui
from config import TRAINING_TYPES, WEEKLY_SESSION_TARGET

st.set_page_config(page_title="Health Dashboard", page_icon="🩺", layout="wide")
ui.inject_css()

# Create tables once per session, not on every rerun (avoids needless DB calls).
if "db_inited" not in st.session_state:
    db.init_db()
    st.session_state["db_inited"] = True


# --- Cached data reads ---------------------------------------------------
# Streamlit reruns the whole script on every interaction; without caching that
# means re-querying Supabase each time (the lag you saw). Cache the reads and
# clear the cache only after a write (see _refresh).

@st.cache_data(ttl=600, show_spinner=False)
def load_data():
    return metrics.add_weight_trend(db.load_dataframe())


@st.cache_data(ttl=600, show_spinner=False)
def load_workouts():
    return db.get_workouts()


def _refresh():
    """Invalidate cached reads after a write, then rerun."""
    load_data.clear()
    load_workouts.clear()
    st.rerun()


# --- Range selector ------------------------------------------------------

RANGES = {"1w": 7, "2w": 14, "4w": 28, "8w": 56, "All": None}


def filter_range(df: pd.DataFrame, days: int | None) -> pd.DataFrame:
    if df.empty or days is None:
        return df
    cutoff = pd.Timestamp(date.today()) - pd.Timedelta(days=days)
    return df[df["date"] >= cutoff]


# --- Garmin sync ---------------------------------------------------------

def run_sync(full_backfill: bool = False):
    """Drive a login + sync, surfacing MFA / errors without crashing."""
    result = garmin_sync.login()

    if isinstance(result, garmin_sync.LoginNeedsMFA):
        st.session_state["mfa_client"] = result.client
        st.session_state["mfa_state"] = result.state
        st.session_state["mfa_pending"] = True
        st.warning("Garmin needs an MFA code. Enter it in the sidebar to finish signing in.")
        return

    if isinstance(result, garmin_sync.LoginFailed):
        st.session_state["sync_error"] = result.message
        st.error(result.message)
        return

    _do_sync(result.client, full_backfill)


def _do_sync(client, full_backfill: bool):
    bar = st.progress(0.0, text="Syncing Garmin…")
    try:
        n = garmin_sync.sync(
            client,
            full_backfill=full_backfill,
            progress=lambda frac, label: bar.progress(frac, text=f"Syncing {label}…"),
        )
        bar.empty()
        st.session_state["sync_error"] = None
        load_data.clear()
        load_workouts.clear()
        st.toast(f"Synced {n} day(s) from Garmin.", icon="✅")
    except Exception as exc:
        bar.empty()
        st.session_state["sync_error"] = str(exc)
        st.error(f"Sync failed (showing cached data): {exc}")


# --- Auto-sync once per session -----------------------------------------

GARMIN_AVAILABLE = garmin_sync.is_available()

if GARMIN_AVAILABLE and "did_initial_sync" not in st.session_state:
    st.session_state["did_initial_sync"] = True
    with st.spinner("Checking Garmin for new data…"):
        run_sync(full_backfill=not db.get_existing_garmin_dates())


# --- Sidebar -------------------------------------------------------------

with st.sidebar:
    st.markdown("### 🏃 Controls")

    if GARMIN_AVAILABLE:
        if st.button("🔄 Sync Garmin now", width="stretch", type="primary"):
            run_sync(full_backfill=False)
        with st.expander("Backfill last 90 days"):
            if st.button("Run full backfill", width="stretch"):
                run_sync(full_backfill=True)
    else:
        st.info(
            "Garmin syncing runs from your local machine (`sync_job.py`), not "
            "from here. This dashboard shows the latest synced data and lets you "
            "log weight."
        )

    if st.session_state.get("mfa_pending"):
        st.divider()
        st.subheader("Garmin MFA")
        code = st.text_input("6-digit code", max_chars=10)
        if st.button("Submit code", width="stretch"):
            res = garmin_sync.resume_mfa(
                st.session_state["mfa_client"], st.session_state["mfa_state"], code
            )
            if isinstance(res, garmin_sync.LoginOk):
                st.session_state["mfa_pending"] = False
                _do_sync(res.client, full_backfill=not db.get_existing_garmin_dates())
            else:
                st.error(res.message)

    if st.session_state.get("sync_error"):
        st.divider()
        st.caption(f"⚠️ Last sync issue: {st.session_state['sync_error']}")


# --- Data (cached) -------------------------------------------------------

df = load_data()
workouts_all = load_workouts()


def _col_latest(frame, col):
    s = frame[col].dropna() if (not frame.empty and col in frame) else pd.Series(dtype=float)
    return s.iloc[-1] if not s.empty else None


# Most recent weight / Garmin date, derived from the cached frame (no extra queries).
last_weight = _col_latest(df, "weight_kg")
last_weight = float(last_weight) if last_weight is not None else None
prefill = last_weight if last_weight is not None else 87.0

latest_garmin = None
if not df.empty:
    gcols = [c for c in ["total_calories", "steps", "sleep_seconds"] if c in df]
    if gcols:
        gmask = df[gcols].notna().any(axis=1)
        if gmask.any():
            latest_garmin = df.loc[gmask, "date"].iloc[-1].date().isoformat()
synced_txt = f"Garmin synced through {latest_garmin}" if latest_garmin else "No Garmin data yet"

today_iso = date.today().isoformat()
today_ts = pd.Timestamp(date.today())


# --- Header: title · range · compact weight logger ----------------------

hcol1, hcol2, hcol3 = st.columns([2.6, 1.5, 1], vertical_alignment="bottom")
with hcol1:
    ui.header("Health Dashboard",
              "Weight, recovery & training at a glance · cutting on ~2,850 kcal maintenance")
with hcol2:
    range_label = st.segmented_control(
        "Range", list(RANGES.keys()), default="4w",
        selection_mode="single", label_visibility="collapsed",
    ) or "4w"
with hcol3:
    with st.popover("⚖️ Log weight", width="stretch"):
        w_log_date = st.session_state.get("w_date", date.today())
        if w_log_date > date.today():
            w_log_date = date.today()
        w_is_today = w_log_date == date.today()

        weight_in = st.number_input(
            "Weight (kg)", min_value=30.0, max_value=300.0,
            value=float(round(prefill, 1)), step=0.1, format="%.1f", key="w_val",
        )
        if st.button(f"💾 Save for {'today' if w_is_today else w_log_date.isoformat()}",
                     width="stretch", type="primary"):
            db.upsert_weight(w_log_date.isoformat(), weight_in)
            st.session_state["w_date"] = date.today()
            st.toast(f"Saved {weight_in:.1f} kg for {w_log_date.isoformat()}.", icon="✅")
            _refresh()
        st.date_input("Log for a different day", max_value=date.today(), key="w_date")
        if last_weight is not None:
            st.caption(f"Last logged: {last_weight:.1f} kg")

st.caption(synced_txt)

if df.empty:
    ui.section("Getting started")
    ui.empty_state("📭", "No data yet — use **Log weight** above, and Garmin "
                        "metrics will appear once a sync runs.")
    st.stop()


# --- Today strip ---------------------------------------------------------

today_row = df[df["date"] == today_ts]
tr = today_row.iloc[0] if not today_row.empty else None


def _today_val(col, transform=None):
    if tr is None or col not in today_row or pd.isna(tr[col]):
        return None
    v = tr[col]
    return transform(v) if transform else v


todays_sessions = []
if not workouts_all.empty:
    todays_sessions = sorted(workouts_all[workouts_all["date"] == today_ts]["type"].tolist())
_labels = {t["key"]: t["label"] for t in TRAINING_TYPES}
sessions_str = " · ".join(_labels.get(k, k) for k in todays_sessions) if todays_sessions else None

_steps = _today_val("steps")
_cals = _today_val("total_calories")
_sleep = _today_val("sleep_seconds", transform=lambda v: v / 3600.0)
_bb = _today_val("body_battery_high")
_rhr = _today_val("resting_hr")
_w_today = _today_val("weight_kg")

with st.container(border=True):
    _t = date.today()
    ui.today_card(
        f"{_t:%a · %b} {_t.day}",
        [
            ("Weight", f"{_w_today:.1f}" if _w_today is not None else
                       (f"{last_weight:.1f}" if last_weight is not None else None),
             "kg"),
            ("Sleep", f"{_sleep:.1f}" if _sleep is not None else None, "h"),
            ("Steps", f"{_steps:,.0f}" if _steps is not None else None, ""),
            ("Burned", f"{_cals:,.0f}" if _cals is not None else None, "kcal"),
            ("Resting HR", f"{_rhr:.0f}" if _rhr is not None else None, "bpm"),
            ("Body Battery", f"{_bb:.0f}" if _bb is not None else None, "peak"),
            ("Sessions", sessions_str if sessions_str else None, ""),
        ],
    )


# --- Headline KPIs -------------------------------------------------------

head = metrics.headline(df, window_days=14)
status = metrics.status_read(df, head)

ui.section("This week at a glance")
k1, k2, k3, k4 = st.columns(4)

with k1:
    if head.avg_weight is not None:
        ui.kpi("7-day avg weight", f"{head.avg_weight:.1f}", unit="kg")
    else:
        ui.kpi("7-day avg weight", "—", empty=True, sub="log weight to populate")

with k2:
    if head.rate_kg_per_week is not None:
        rate = head.rate_kg_per_week
        col = ui.ACCENT if rate < 0 else (ui.RED if rate > 0 else ui.MUTED)
        arrow = "▼" if rate < 0 else ("▲" if rate > 0 else "→")
        ui.kpi("Weekly rate",
               f'<span style="color:{col}">{arrow} {abs(rate):.2f}</span>',
               unit="kg/wk",
               sub=("losing" if rate < 0 else "gaining" if rate > 0 else "flat"),
               sub_color=col)
    else:
        ui.kpi("Weekly rate", "—", empty=True, sub="needs a few weigh-ins")

with k3:
    if head.avg_expenditure is not None:
        ui.kpi("Maintenance est.", f"{head.avg_expenditure:,.0f}", unit="kcal",
               sub="live, from Garmin", sub_color=ui.MUTED,
               help="Average daily Garmin expenditure over the window. "
                    "An estimate, not ground truth.")
    else:
        ui.kpi("Maintenance est.", "—", empty=True)

with k4:
    if head.implied_deficit is not None:
        d = head.implied_deficit
        label = "daily deficit" if d >= 0 else "daily surplus"
        col = ui.ACCENT if d >= 0 else ui.RED
        ui.kpi("Implied deficit", f"{abs(d):,.0f}", unit="kcal",
               sub=f"{label} · from trend", sub_color=col,
               help="Energy balance implied by the weight trend (≈7700 kcal/kg).")
    else:
        ui.kpi("Implied deficit", "—", empty=True, sub="needs a trend")

st.write("")
ui.status_banner(status.key, status.label, status.nudge)

wdf = filter_range(df, RANGES[range_label])


# --- Training ------------------------------------------------------------

ui.section("Training")
with st.container(border=True):
    tcol1, tcol2 = st.columns([3, 1], vertical_alignment="center")

    # Sessions logged in the last 7 days, per type.
    week_cut = pd.Timestamp(date.today()) - pd.Timedelta(days=6)
    recent = (workouts_all[workouts_all["date"] >= week_cut]
              if not workouts_all.empty else workouts_all)
    counts = (recent["type"].value_counts().to_dict()
              if not recent.empty else {})
    total_week = int(sum(counts.values()))

    with tcol1:
        if total_week:
            ui.chips([(t["label"], counts.get(t["key"], 0), t["color"])
                      for t in TRAINING_TYPES if counts.get(t["key"], 0)])
            st.caption(f"{total_week} session(s) in the last 7 days "
                       f"· target {WEEKLY_SESSION_TARGET}/week")
        else:
            st.caption("No sessions logged in the last 7 days — log one →")

    with tcol2:
        with st.popover("➕ Log session", width="stretch"):
            wk_log_date = st.session_state.get("wk_date", date.today())
            if wk_log_date > date.today():
                wk_log_date = date.today()
            iso = wk_log_date.isoformat()
            wk_is_today = wk_log_date == date.today()
            existing = set(
                workouts_all[workouts_all["date"] == pd.Timestamp(iso)]["type"]
            ) if not workouts_all.empty else set()
            labels = {t["key"]: t["label"] for t in TRAINING_TYPES}

            st.markdown(f"**Logging for {'today' if wk_is_today else iso}**")
            bcols = st.columns(len(TRAINING_TYPES))
            for i, t in enumerate(TRAINING_TYPES):
                with bcols[i]:
                    if st.button(t["label"], key=f"add_{t['key']}", width="stretch",
                                 disabled=t["key"] in existing):
                        db.add_workout(iso, t["key"])
                        st.session_state["wk_date"] = date.today()
                        st.toast(f"Logged {t['label']} for {iso}.", icon="✅")
                        _refresh()

            if existing:
                st.caption("Logged that day — tap to remove")
                rcols = st.columns(len(existing))
                for i, k in enumerate(sorted(existing)):
                    with rcols[i]:
                        if st.button(f"✕ {labels.get(k, k)}", key=f"rm_{k}",
                                     width="stretch"):
                            db.remove_workout(iso, k)
                            st.session_state["wk_date"] = date.today()
                            st.toast(f"Removed {labels.get(k, k)}.", icon="🗑️")
                            _refresh()

            st.date_input("Log a different day", max_value=date.today(), key="wk_date")

    # Session log over the selected range, most recent first.
    wk = filter_range(workouts_all, RANGES[range_label])
    if workouts_all.empty:
        ui.empty_state("🏋️", "Tap **Log session** to record your F1/F2/F3, ultimate "
                            "and runs — they'll appear here as a dated log.")
    elif wk.empty:
        st.caption("No sessions logged in this range — widen it or log one above.")
    else:
        ui.session_log(wk, TRAINING_TYPES)


# --- Recovery ------------------------------------------------------------

ui.section("Recovery")

rec = metrics.recovery_read(df, window_days=14)
if rec.under_recovering:
    ui.status_banner("aggressive", "Under-recovery signal", rec.note)
else:
    st.caption(rec.note)


def _latest(frame: pd.DataFrame, col: str, transform=None):
    s = frame[col].dropna() if col in frame else pd.Series(dtype=float)
    if s.empty:
        return None
    v = s.iloc[-1]
    return transform(v) if transform else v


def _arrow(slope, good_down=False, deadband=0.0):
    """Direction arrow only when the slope is meaningful. Emerald if the
    direction is good for you, soft amber if not, muted when flat/unknown."""
    if slope is None or abs(slope) <= deadband:
        return None, ui.MUTED
    up = slope > 0
    good = (not up) if good_down else up
    return ("▲" if up else "▼"), (ui.ACCENT if good else ui.AMBER)


def _recovery_card(label, col, color, unit, *, fmt="{:.0f}", slope=None,
                   good_down=False, deadband=0.0, transform=None,
                   spark_transform=None, spark_fmt=".0f"):
    with st.container(border=True):
        val = _latest(wdf, col, transform=transform)
        arr, acol = _arrow(slope, good_down=good_down, deadband=deadband)
        ui.recovery_header(
            label, fmt.format(val) if val is not None else "—",
            unit=unit if val is not None else "",
            trend=f"{arr} 14d" if arr else None, trend_color=acol,
        )
        chart = ui.spark(wdf, col, color, fmt=spark_fmt, transform=spark_transform)
        if chart is not None:
            st.altair_chart(chart, width="stretch")
        elif val is not None:
            st.caption("Building baseline — a couple more days for a trend.")
        else:
            st.caption("No data in range yet.")


r1, r2, r3 = st.columns(3)
with r1:
    _recovery_card("Resting HR", "resting_hr", ui.AMBER, "bpm",
                   slope=rec.rhr_slope, good_down=True, deadband=0.1)
with r2:
    _recovery_card("Sleep", "sleep_seconds", ui.INDIGO, "h", fmt="{:.1f}",
                   slope=rec.sleep_slope, good_down=False, deadband=0.1,
                   transform=lambda v: v / 3600.0,
                   spark_transform=lambda s: s / 3600.0, spark_fmt=".1f")
with r3:
    _recovery_card("Body Battery", "body_battery_high", ui.TEAL, "peak",
                   slope=rec.bb_slope, good_down=False, deadband=0.5)


# --- Activity context ----------------------------------------------------

ui.section("Activity")
a1, a2 = st.columns(2)
with a1:
    with st.container(border=True):
        val = _latest(wdf, "total_calories")
        ui.recovery_header("Calories burned", f"{val:,.0f}" if val is not None else "—",
                           unit="kcal" if val is not None else "")
        chart = ui.spark(wdf, "total_calories", ui.AMBER, fmt=",.0f")
        if chart is not None:
            st.altair_chart(chart, width="stretch")
        else:
            ui.empty_state("🔥", "No calorie data in range.")
with a2:
    with st.container(border=True):
        val = _latest(wdf, "steps")
        ui.recovery_header("Steps", f"{val:,.0f}" if val is not None else "—")
        chart = ui.spark(wdf, "steps", ui.BLUE, fmt=",.0f")
        if chart is not None:
            st.altair_chart(chart, width="stretch")
        else:
            ui.empty_state("👟", "No step data in range.")


# --- Weight trend (full detail, at the bottom) --------------------------

ui.section("Weight trend")
with st.container(border=True):
    has_weight = wdf["weight_kg"].notna().any() if "weight_kg" in wdf else False
    if has_weight:
        st.altair_chart(ui.weight_chart(wdf), width="stretch")
        st.caption("Faint dots are daily weigh-ins (noise). The green line is the "
                   "7-day moving average — your real trend.")
    else:
        ui.empty_state("⚖️", "Use **Log weight** in the header to record a few days "
                            "and the trend line will appear here.")

st.caption("Data stored in your database. If Garmin is unreachable, the dashboard "
           "keeps showing the last synced data.")

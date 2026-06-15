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
db.init_db()


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


# --- Data ----------------------------------------------------------------

df = db.load_dataframe()
df = metrics.add_weight_trend(df)
workouts_all = db.get_workouts()

latest_garmin = db.latest_garmin_date()
synced_txt = f"Garmin synced through {latest_garmin}" if latest_garmin else "No Garmin data yet"


# --- Header: title · range · compact weight logger ----------------------

today_iso = date.today().isoformat()
last_weight = db.latest_weight()
prefill = last_weight if last_weight is not None else 87.0

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
        weight_in = st.number_input(
            "Today's weight (kg)", min_value=30.0, max_value=300.0,
            value=float(round(prefill, 1)), step=0.1, format="%.1f",
        )
        if st.button("💾 Save today", width="stretch", type="primary"):
            db.upsert_weight(today_iso, weight_in)
            st.toast(f"Saved {weight_in:.1f} kg for today.", icon="✅")
            st.rerun()
        st.divider()
        st.caption("Backfill a past date")
        past_date = st.date_input("Date", value=date.today(),
                                  max_value=date.today(), key="backfill_date",
                                  label_visibility="collapsed")
        past_weight = st.number_input(
            "Weight (kg)", min_value=30.0, max_value=300.0,
            value=float(round(prefill, 1)), step=0.1, format="%.1f",
            key="backfill_weight", label_visibility="collapsed",
        )
        if st.button("Save past date", width="stretch", key="save_past"):
            db.upsert_weight(past_date.isoformat(), past_weight)
            st.toast(f"Saved {past_weight:.1f} kg for {past_date.isoformat()}.", icon="✅")
            st.rerun()
        if last_weight is not None:
            st.caption(f"Last logged: {last_weight:.1f} kg")

st.caption(synced_txt)

if df.empty:
    ui.section("Getting started")
    ui.empty_state("📭", "No data yet — use **Log weight** above, and Garmin "
                        "metrics will appear once a sync runs.")
    st.stop()


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
            w_date = st.date_input("Date", value=date.today(),
                                   max_value=date.today(), key="wk_date")
            iso = w_date.isoformat()
            existing = set(
                workouts_all[workouts_all["date"] == pd.Timestamp(iso)]["type"]
            ) if not workouts_all.empty else set()
            keys = [t["key"] for t in TRAINING_TYPES]
            labels = {t["key"]: t["label"] for t in TRAINING_TYPES}
            chosen = st.multiselect(
                "Sessions that day", keys,
                default=[k for k in keys if k in existing],
                format_func=lambda k: labels[k], key="wk_sel",
            )
            if st.button("Save sessions", width="stretch", type="primary", key="wk_save"):
                chosen_set = set(chosen)
                for k in keys:
                    if k in chosen_set and k not in existing:
                        db.add_workout(iso, k)
                    elif k not in chosen_set and k in existing:
                        db.remove_workout(iso, k)
                st.toast("Sessions updated.", icon="✅")
                st.rerun()

    wk = filter_range(workouts_all, RANGES[range_label])
    chart = ui.training_chart(wk, TRAINING_TYPES)
    if chart is not None:
        st.altair_chart(chart, width="stretch")
    else:
        ui.empty_state("🏋️", "Log your F1/F2/F3, ultimate and runs to see weekly "
                            "training volume build up here.")


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

"""Personal fat-loss & recovery dashboard.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import os
from datetime import date, timedelta

import altair as alt
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
from config import REFERENCE_MAINTENANCE_KCAL

st.set_page_config(page_title="Fitness Dashboard", page_icon="🏃", layout="wide")

db.init_db()


# --- Range selector ------------------------------------------------------

RANGES = {"2w": 14, "4w": 28, "8w": 56, "All": None}


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
        st.success(f"Synced {n} day(s) from Garmin.")
    except Exception as exc:
        bar.empty()
        st.session_state["sync_error"] = str(exc)
        st.error(f"Sync failed (showing cached data): {exc}")


# --- Auto-sync once per session -----------------------------------------

if "did_initial_sync" not in st.session_state:
    st.session_state["did_initial_sync"] = True
    with st.spinner("Checking Garmin for new data…"):
        run_sync(full_backfill=not db.get_existing_garmin_dates())


# --- Sidebar -------------------------------------------------------------

with st.sidebar:
    st.header("Controls")

    selected_range = st.radio("Chart range", list(RANGES.keys()), index=1, horizontal=True)

    if st.button("🔄 Sync Garmin now", use_container_width=True):
        run_sync(full_backfill=False)

    with st.expander("Backfill last 90 days"):
        if st.button("Run full backfill", use_container_width=True):
            run_sync(full_backfill=True)

    # MFA completion flow (only shows when a login is mid-MFA).
    if st.session_state.get("mfa_pending"):
        st.divider()
        st.subheader("Garmin MFA")
        code = st.text_input("6-digit code", max_chars=10)
        if st.button("Submit code", use_container_width=True):
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


# --- Weight entry (top, frictionless) -----------------------------------

st.title("🏃 Fat-loss & Recovery")

today_iso = date.today().isoformat()
last_weight = db.latest_weight()
prefill = last_weight if last_weight is not None else 87.0

entry = st.container()
with entry:
    c1, c2, c3 = st.columns([2, 1, 3])
    with c1:
        weight_in = st.number_input(
            "Today's weight (kg)", min_value=30.0, max_value=300.0,
            value=float(round(prefill, 1)), step=0.1, format="%.1f",
        )
    with c2:
        st.write("")
        st.write("")
        if st.button("💾 Save today's weight", use_container_width=True):
            db.upsert_weight(today_iso, weight_in)
            st.success(f"Saved {weight_in:.1f} kg for today.")
            st.rerun()
    with c3:
        with st.expander("Edit / backfill a past date"):
            past_date = st.date_input(
                "Date", value=date.today(), max_value=date.today(),
                key="backfill_date",
            )
            past_weight = st.number_input(
                "Weight (kg)", min_value=30.0, max_value=300.0,
                value=float(round(prefill, 1)), step=0.1, format="%.1f",
                key="backfill_weight",
            )
            if st.button("Save weight for date"):
                db.upsert_weight(past_date.isoformat(), past_weight)
                st.success(f"Saved {past_weight:.1f} kg for {past_date.isoformat()}.")
                st.rerun()

if df.empty:
    st.info("No data yet. Save a weight above and sync Garmin from the sidebar.")
    st.stop()


# --- Headline panel ------------------------------------------------------

head = metrics.headline(df, window_days=14)
status = metrics.status_read(df, head)

st.subheader("This week at a glance")
m1, m2, m3, m4 = st.columns(4)

m1.metric(
    "7-day avg weight",
    f"{head.avg_weight:.1f} kg" if head.avg_weight is not None else "—",
)

if head.rate_kg_per_week is not None:
    m2.metric(
        "Weekly rate",
        f"{head.rate_kg_per_week:+.2f} kg/wk",
        help="From the 7-day moving-average slope. Negative = losing.",
    )
else:
    m2.metric("Weekly rate", "—")

m3.metric(
    "Maintenance ESTIMATE",
    f"{head.avg_expenditure:,.0f} kcal" if head.avg_expenditure is not None
    else f"~{REFERENCE_MAINTENANCE_KCAL:,} kcal",
    help="Live estimate = avg daily Garmin expenditure over the window. "
         "An estimate, not ground truth.",
)

m4.metric(
    "Implied daily deficit",
    f"{head.implied_deficit:,.0f} kcal" if head.implied_deficit is not None else "—",
    help="Derived from the weight trend (≈7700 kcal per kg).",
)

# Status banner.
status_style = {
    "on_target": st.success,
    "aggressive": st.warning,
    "stalled": st.warning,
    "slow": st.info,
    "gaining": st.warning,
    "unknown": st.info,
}.get(status.key, st.info)
status_style(f"**{status.label}** — {status.nudge}")


# --- Weight chart --------------------------------------------------------

st.subheader("Weight trend")

wdf = filter_range(df, RANGES[selected_range])
weight_long = wdf[["date", "weight_kg", "weight_ma7"]].copy()

points = (
    alt.Chart(weight_long.dropna(subset=["weight_kg"]))
    .mark_circle(size=45, opacity=0.45, color="#7aa2ff")
    .encode(
        x=alt.X("date:T", title=None),
        y=alt.Y("weight_kg:Q", title="kg", scale=alt.Scale(zero=False)),
        tooltip=[alt.Tooltip("date:T"), alt.Tooltip("weight_kg:Q", format=".1f")],
    )
)
line = (
    alt.Chart(weight_long.dropna(subset=["weight_ma7"]))
    .mark_line(strokeWidth=3, color="#ff7a7a")
    .encode(
        x="date:T",
        y=alt.Y("weight_ma7:Q", scale=alt.Scale(zero=False)),
        tooltip=[alt.Tooltip("date:T"), alt.Tooltip("weight_ma7:Q", format=".2f", title="7-day avg")],
    )
)
st.altair_chart((points + line).properties(height=320), use_container_width=True)
st.caption("Dots are daily weigh-ins (noise). The red line is the 7-day moving average (the real trend).")


# --- Recovery row --------------------------------------------------------

st.subheader("Recovery")

rec = metrics.recovery_read(df, window_days=14)
if rec.under_recovering:
    st.warning(f"⚠️ {rec.note}")
else:
    st.caption(rec.note)


def trend_chart(frame: pd.DataFrame, col: str, title: str, color: str, transform=None):
    sub = frame[["date", col]].dropna()
    if sub.empty:
        st.caption(f"No {title.lower()} data.")
        return
    sub = sub.copy()
    if transform:
        sub[col] = transform(sub[col])
    chart = (
        alt.Chart(sub)
        .mark_line(point=True, strokeWidth=2, color=color)
        .encode(
            x=alt.X("date:T", title=None),
            y=alt.Y(f"{col}:Q", title=title, scale=alt.Scale(zero=False)),
            tooltip=[alt.Tooltip("date:T"), alt.Tooltip(f"{col}:Q", format=".1f")],
        )
        .properties(height=200)
    )
    st.altair_chart(chart, use_container_width=True)


r1, r2, r3 = st.columns(3)
with r1:
    st.markdown("**Resting HR** (bpm)")
    trend_chart(wdf, "resting_hr", "Resting HR", "#ff9f43")
with r2:
    st.markdown("**Sleep** (hours)")
    trend_chart(wdf, "sleep_seconds", "Sleep h", "#54a0ff",
                transform=lambda s: s / 3600.0)
with r3:
    st.markdown("**Body Battery** (daily high)")
    trend_chart(wdf, "body_battery_high", "Body Battery", "#1dd1a1")


# --- Activity context ----------------------------------------------------

with st.expander("Calories & steps"):
    a1, a2 = st.columns(2)
    with a1:
        st.markdown("**Total calories burned**")
        trend_chart(wdf, "total_calories", "kcal", "#feca57")
    with a2:
        st.markdown("**Steps**")
        trend_chart(wdf, "steps", "steps", "#5f27cd")

st.caption(
    "Data cached locally in SQLite. If Garmin is unreachable, the dashboard "
    "keeps showing the last synced data."
)

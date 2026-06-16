"""Presentation layer: design system (CSS), reusable HTML components, and a
shared Altair chart theme. Keeps app.py focused on data + layout.
"""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

# --- Palette (kept in sync with .streamlit/config.toml) -----------------
BG = "#0d1117"
SURFACE = "#161b22"
BORDER = "rgba(255,255,255,0.08)"
TEXT = "#e6edf3"
MUTED = "#9aa4b2"
FAINT = "#6b7480"

ACCENT = "#10b981"   # emerald
BLUE = "#60a5fa"
INDIGO = "#818cf8"
TEAL = "#2dd4bf"
AMBER = "#fbbf24"
RED = "#f87171"
SLATE = "#64748b"

# Status key -> (css class, icon, accent colour)
STATUS_STYLE = {
    "on_target":  ("s-success", "✓", ACCENT),
    "aggressive": ("s-danger",  "⚡", RED),
    "stalled":    ("s-warning", "⏸", AMBER),
    "slow":       ("s-info",    "→", BLUE),
    "gaining":    ("s-warning", "▲", AMBER),
    "unknown":    ("s-neutral", "•", SLATE),
}


def inject_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, .stApp, [data-testid="stAppViewContainer"],
        [data-testid="stSidebar"], button, input, textarea, select {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        }

        .block-container { padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1200px; }

        /* Hide Streamlit's default chrome */
        [data-testid="stHeader"] { background: transparent; }
        #MainMenu, footer { visibility: hidden; }

        /* Hero header */
        .app-head { display:flex; align-items:flex-end; justify-content:space-between;
                    gap:1rem; margin-bottom:1.4rem; flex-wrap:wrap; }
        .app-title { font-size:1.85rem; font-weight:800; letter-spacing:-.02em; margin:0;
                     line-height:1.1; }
        .app-sub { color:#9aa4b2; font-size:.9rem; margin-top:.25rem; }
        .app-meta { color:#6b7480; font-size:.82rem; text-align:right; }

        /* Section label */
        .section-title { font-size:.78rem; font-weight:600; letter-spacing:.08em;
            text-transform:uppercase; color:#9aa4b2; margin:1.8rem 0 .7rem; }

        /* KPI cards */
        .kpi { background:#161b22; border:1px solid rgba(255,255,255,.08); border-radius:16px;
               padding:1.05rem 1.15rem; height:100%; }
        .kpi-label { font-size:.78rem; color:#9aa4b2; font-weight:500; margin-bottom:.45rem;
                     display:flex; align-items:center; gap:.3rem; }
        .kpi-value { font-size:1.85rem; font-weight:700; color:#e6edf3; line-height:1.05;
                     letter-spacing:-.01em; }
        .kpi-unit { font-size:.95rem; font-weight:500; color:#6b7480; margin-left:.28rem; }
        .kpi-sub { font-size:.82rem; font-weight:600; margin-top:.5rem; color:#9aa4b2; }
        .kpi-empty .kpi-value { color:#39424f; font-weight:600; }

        /* Status callout */
        .status { border-radius:16px; padding:1rem 1.2rem; display:flex; gap:.85rem;
                  align-items:flex-start; border:1px solid; margin:.1rem 0 .2rem; }
        .status-ic { font-size:1.15rem; line-height:1.4; }
        .status-title { font-weight:700; font-size:.98rem; }
        .status-text { font-size:.88rem; color:#c2cad4; margin-top:.12rem; line-height:1.4; }
        .s-success { background:rgba(16,185,129,.10); border-color:rgba(16,185,129,.32); }
        .s-success .status-title { color:#34d399; }
        .s-warning { background:rgba(245,158,11,.10); border-color:rgba(245,158,11,.32); }
        .s-warning .status-title { color:#fbbf24; }
        .s-danger  { background:rgba(239,68,68,.10);  border-color:rgba(239,68,68,.32); }
        .s-danger  .status-title { color:#f87171; }
        .s-info    { background:rgba(96,165,250,.10); border-color:rgba(96,165,250,.30); }
        .s-info    .status-title { color:#60a5fa; }
        .s-neutral { background:rgba(100,116,139,.10); border-color:rgba(100,116,139,.30); }
        .s-neutral .status-title { color:#94a3b8; }

        /* Recovery card header */
        .rec-top { display:flex; justify-content:space-between; align-items:baseline; }
        .rec-label { font-size:.8rem; color:#9aa4b2; font-weight:600; }
        .rec-value { font-size:1.45rem; font-weight:700; color:#e6edf3; }
        .rec-value .u { font-size:.85rem; color:#6b7480; font-weight:500; margin-left:.15rem; }
        .rec-trend { font-size:.78rem; font-weight:600; }

        /* Empty state */
        .empty { text-align:center; padding:2.6rem 1rem; color:#6b7480;
                 border:1px dashed rgba(255,255,255,.10); border-radius:16px; background:rgba(255,255,255,.012); }
        .empty-ic { font-size:1.9rem; opacity:.55; margin-bottom:.5rem; }
        .empty-tx { font-size:.92rem; }

        /* Today strip */
        .today { display:grid; align-items:stretch; }
        .today-date { padding:.15rem 1.3rem .15rem .3rem; display:flex;
                      flex-direction:column; justify-content:center; }
        .today-date .d1 { font-size:.64rem; color:#10b981; text-transform:uppercase;
                          letter-spacing:.12em; font-weight:700; }
        .today-date .d2 { font-size:1.05rem; font-weight:700; color:#e6edf3;
                          margin-top:.25rem; white-space:nowrap; }
        .tstat { padding:.2rem .6rem; border-left:1px solid rgba(255,255,255,.07);
                 display:flex; flex-direction:column; align-items:center;
                 justify-content:center; text-align:center; gap:.35rem; }
        .tstat-l { font-size:.63rem; color:#9aa4b2; text-transform:uppercase;
                   letter-spacing:.07em; font-weight:600; }
        .tstat-v { font-size:1.28rem; font-weight:700; color:#e6edf3; line-height:1;
                   letter-spacing:-.01em; white-space:nowrap; }
        .tstat-v .u { font-size:.72rem; color:#6b7480; font-weight:500; margin-left:.12rem; }
        .tstat-v.muted { color:#4a5260; font-size:1.1rem; font-weight:700; }

        /* Session log */
        .slog { display:flex; flex-direction:column; max-height:340px; overflow-y:auto; }
        .slog-row { display:flex; align-items:center; gap:1rem; padding:.6rem .15rem;
                    border-bottom:1px solid rgba(255,255,255,.05); }
        .slog-row:last-child { border-bottom:none; }
        .slog-date { font-size:.85rem; color:#c2cad4; font-weight:600; width:130px;
                     flex-shrink:0; }
        .slog-date .dim { color:#6b7480; font-weight:500; }
        .slog-chips { display:flex; flex-wrap:wrap; gap:.45rem; }
        .tchip { display:inline-flex; align-items:center; gap:.4rem; border-radius:999px;
                 padding:.28rem .7rem; font-size:.8rem; font-weight:600; color:#e6edf3;
                 background:rgba(255,255,255,.04); border:1px solid transparent; }
        .tchip .dot { width:8px; height:8px; border-radius:50%; }

        /* Soften native bordered containers */
        div[data-testid="stVerticalBlockBorderWrapper"] { border-radius:16px; }

        /* Primary button polish */
        .stButton button[kind="primary"] { font-weight:600; border-radius:12px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def header(title: str, subtitle: str, meta: str = ""):
    st.markdown(
        f"""
        <div class="app-head">
          <div>
            <div class="app-title">{title}</div>
            <div class="app-sub">{subtitle}</div>
          </div>
          <div class="app-meta">{meta}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title: str):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


def today_card(date_label: str, items: list[tuple]):
    """A glanceable, evenly-distributed strip of today's stats.
    items = [(label, value, unit), ...]; value None renders a muted dash."""
    cells = [f'<div class="today-date"><div class="d1">Today</div>'
             f'<div class="d2">{date_label}</div></div>']
    for label, value, unit in items:
        if value is None:
            v = '<span class="tstat-v muted">—</span>'
        else:
            u = f'<span class="u">{unit}</span>' if unit else ""
            v = f'<span class="tstat-v">{value}{u}</span>'
        cells.append(f'<div class="tstat"><div class="tstat-l">{label}</div>{v}</div>')
    cols = f"max-content repeat({len(items)}, minmax(0, 1fr))"
    st.markdown(
        f'<div class="today" style="grid-template-columns:{cols};">{"".join(cells)}</div>',
        unsafe_allow_html=True,
    )


def kpi(label: str, value: str, unit: str | None = None, sub: str | None = None,
        sub_color: str | None = None, help: str | None = None, empty: bool = False):
    """Render one KPI card. `value` is the big number; `empty` mutes it."""
    unit_html = f'<span class="kpi-unit">{unit}</span>' if unit else ""
    hint = f'<span title="{help}" style="cursor:help;color:#5b6573;">ⓘ</span>' if help else ""
    sub_html = ""
    if sub:
        color = f"color:{sub_color};" if sub_color else ""
        sub_html = f'<div class="kpi-sub" style="{color}">{sub}</div>'
    cls = "kpi kpi-empty" if empty else "kpi"
    st.markdown(
        f"""
        <div class="{cls}">
          <div class="kpi-label">{label} {hint}</div>
          <div class="kpi-value">{value}{unit_html}</div>
          {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_banner(key: str, title: str, text: str):
    cls, icon, _ = STATUS_STYLE.get(key, STATUS_STYLE["unknown"])
    st.markdown(
        f"""
        <div class="status {cls}">
          <div class="status-ic">{icon}</div>
          <div>
            <div class="status-title">{title}</div>
            <div class="status-text">{text}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def recovery_header(label: str, value: str, unit: str = "",
                    trend: str | None = None, trend_color: str = MUTED):
    u = f'<span class="u">{unit}</span>' if unit else ""
    t = f'<span class="rec-trend" style="color:{trend_color}">{trend}</span>' if trend else ""
    st.markdown(
        f"""
        <div class="rec-top">
          <span class="rec-label">{label}</span>
          {t}
        </div>
        <div class="rec-value">{value}{u}</div>
        """,
        unsafe_allow_html=True,
    )


def empty_state(icon: str, text: str):
    st.markdown(
        f'<div class="empty"><div class="empty-ic">{icon}</div>'
        f'<div class="empty-tx">{text}</div></div>',
        unsafe_allow_html=True,
    )


# --- Charts --------------------------------------------------------------

def _base_theme(chart, y_grid=True):
    return (
        chart.configure_view(strokeWidth=0)
        .configure(background="transparent")
        .configure_axis(
            labelColor=FAINT, titleColor=MUTED, labelFont="Inter", titleFont="Inter",
            labelFontSize=11, domainColor="rgba(255,255,255,.12)",
            tickColor="rgba(255,255,255,.12)",
            gridColor="rgba(255,255,255,.05)",
        )
        .configure_axisX(grid=False)
        .configure_axisY(grid=y_grid)
    )


def weight_chart(df: pd.DataFrame):
    """Daily weigh-ins (faint dots) + 7-day moving-average line with area fill."""
    data = df[["date", "weight_kg", "weight_ma7"]].copy()
    x = alt.X("date:T", title=None, axis=alt.Axis(format="%b %d", tickCount=6))

    area = (
        alt.Chart(data.dropna(subset=["weight_ma7"]))
        .mark_area(
            line=False,
            color=alt.Gradient(
                gradient="linear",
                stops=[alt.GradientStop(color="rgba(16,185,129,0)", offset=0),
                       alt.GradientStop(color="rgba(16,185,129,0.22)", offset=1)],
                x1=1, x2=1, y1=1, y2=0,
            ),
        )
        .encode(x=x, y=alt.Y("weight_ma7:Q", title="kg", scale=alt.Scale(zero=False)))
    )
    points = (
        alt.Chart(data.dropna(subset=["weight_kg"]))
        .mark_circle(size=34, opacity=0.35, color=SLATE)
        .encode(
            x=x, y=alt.Y("weight_kg:Q", scale=alt.Scale(zero=False)),
            tooltip=[alt.Tooltip("date:T", title="Date"),
                     alt.Tooltip("weight_kg:Q", title="Weight", format=".1f")],
        )
    )
    line = (
        alt.Chart(data.dropna(subset=["weight_ma7"]))
        .mark_line(strokeWidth=2.5, color=ACCENT)
        .encode(
            x=x, y=alt.Y("weight_ma7:Q", scale=alt.Scale(zero=False)),
            tooltip=[alt.Tooltip("date:T", title="Date"),
                     alt.Tooltip("weight_ma7:Q", title="7-day avg", format=".2f")],
        )
    )
    chart = (area + points + line).properties(height=300)
    return _base_theme(chart)


def session_log(workouts: pd.DataFrame, types: list[dict], limit: int = 60) -> bool:
    """A dated list of training sessions, most recent first, with colour-coded
    type chips. Robust and readable with sparse or dense data. Returns False if
    there's nothing to show."""
    if workouts is None or workouts.empty:
        return False
    key_to_label = {t["key"]: t["label"] for t in types}
    color = {t["key"]: t["color"] for t in types}
    rank = {t["key"]: i for i, t in enumerate(types)}

    w = workouts.copy()
    w["rank"] = w["type"].map(rank).fillna(99)
    rows_html = []
    dates = sorted(w["date"].unique(), reverse=True)[: limit]
    for d in dates:
        ts = pd.Timestamp(d)
        day = w[w["date"] == ts].sort_values("rank")
        chips = "".join(
            f'<span class="tchip" style="border-color:{color.get(k, "#888")}55;">'
            f'<span class="dot" style="background:{color.get(k, "#888")};"></span>'
            f'{key_to_label.get(k, k)}</span>'
            for k in day["type"]
        )
        label = f'{ts:%a} <span class="dim">· {ts:%b} {ts.day}</span>'
        rows_html.append(
            f'<div class="slog-row"><div class="slog-date">{label}</div>'
            f'<div class="slog-chips">{chips}</div></div>'
        )
    st.markdown(f'<div class="slog">{"".join(rows_html)}</div>', unsafe_allow_html=True)
    return True


def chips(items: list[tuple]):
    """Render small coloured count chips: items = [(label, count, color), ...]."""
    html = '<div style="display:flex;flex-wrap:wrap;gap:.5rem;margin:.2rem 0 .4rem;">'
    for label, count, color in items:
        html += (
            f'<span style="display:inline-flex;align-items:center;gap:.4rem;'
            f'background:rgba(255,255,255,.04);border:1px solid {color}55;'
            f'border-radius:999px;padding:.3rem .7rem;font-size:.82rem;font-weight:600;">'
            f'<span style="width:8px;height:8px;border-radius:50%;background:{color};"></span>'
            f'{label}<span style="color:{MUTED};font-weight:500;">{count}</span></span>'
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def spark(df: pd.DataFrame, col: str, color: str, fmt: str = ".0f",
          transform=None, height: int = 120):
    """Compact trend chart for a recovery/activity metric.

    Honest about gaps: keeps every day in range (missing days stay null) so the
    line BREAKS at unrecorded days instead of bridging them with a fabricated
    straight segment. A dot marks each day that was actually measured.
    """
    if col not in df:
        return None
    meas = df[["date", col]].dropna().copy()
    if transform is not None:
        meas[col] = transform(meas[col])
    if len(meas) < 2:  # need at least two real measurements
        return None
    meas = meas.sort_values("date")

    # Split into runs of consecutive days: the line only connects days that are
    # actually adjacent, so a gap of missing days breaks the line rather than
    # being bridged by a fabricated straight segment.
    day_num = (meas["date"] - meas["date"].min()).dt.days
    meas["seg"] = (day_num.diff().fillna(1) > 1).cumsum()

    x = alt.X("date:T", title=None, axis=alt.Axis(format="%b %d", tickCount=4))
    y = alt.Y(f"{col}:Q", title=None, scale=alt.Scale(zero=False))
    tip = [alt.Tooltip("date:T", title="Date"),
           alt.Tooltip(f"{col}:Q", title=col, format=fmt)]

    line = alt.Chart(meas).mark_line(strokeWidth=2, color=color).encode(
        x=x, y=y, detail="seg:N")
    pts = alt.Chart(meas).mark_circle(size=28, color=color, opacity=0.9).encode(
        x=x, y=y, tooltip=tip)
    chart = (line + pts).properties(height=height)
    return _base_theme(chart, y_grid=False)

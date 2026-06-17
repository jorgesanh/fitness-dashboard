"""Presentation layer: design system (CSS), reusable HTML components, and a
shared Altair chart theme. Keeps app.py focused on data + layout.
"""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

# --- Palette (kept in sync with .streamlit/config.toml and inject_css) ---
BG = "#0a0c10"
SURFACE = "#13171e"
BORDER = "rgba(255,255,255,0.07)"
TEXT = "#eef1f5"
MUTED = "#98a2b1"
FAINT = "#646e7d"

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

        :root {
            --bg:#0a0c10; --surface:#13171e; --surface-2:#171c24;
            --line:rgba(255,255,255,.07); --line-soft:rgba(255,255,255,.05);
            --text:#eef1f5; --muted:#98a2b1; --faint:#646e7d; --accent:#10b981;
            --shadow:0 1px 2px rgba(0,0,0,.35), 0 6px 20px -8px rgba(0,0,0,.55);
            --radius:18px;
        }

        html, body, .stApp, [data-testid="stAppViewContainer"],
        [data-testid="stSidebar"], button, input, textarea, select {
            font-family:'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
            -webkit-font-smoothing:antialiased; -moz-osx-font-smoothing:grayscale;
        }
        .stApp { background:
            radial-gradient(1200px 600px at 50% -200px, rgba(16,185,129,.06), transparent 70%),
            var(--bg); }

        .block-container { padding-top:2.4rem; padding-bottom:5rem; max-width:1180px; }
        [data-testid="stHeader"] { background:transparent; }
        #MainMenu, footer { visibility:hidden; }

        /* Hero header */
        .app-head { display:flex; align-items:flex-end; justify-content:space-between;
                    gap:1rem; margin-bottom:1.1rem; flex-wrap:wrap; }
        .app-title { font-size:1.95rem; font-weight:800; letter-spacing:-.03em; margin:0;
                     line-height:1.08; color:var(--text); }
        .app-sub { color:var(--muted); font-size:.9rem; margin-top:.3rem; font-weight:450; }
        .app-meta { color:var(--faint); font-size:.82rem; text-align:right; }

        /* Section label */
        .section-title { font-size:.74rem; font-weight:600; letter-spacing:.11em;
            text-transform:uppercase; color:var(--faint); margin:2.1rem 0 .8rem; }

        /* Card surface shared by KPI / today tiles / native containers */
        .kpi, .tstat,
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background:linear-gradient(180deg, var(--surface-2), var(--surface));
            border:1px solid var(--line) !important; border-radius:var(--radius) !important;
            box-shadow:var(--shadow);
        }
        div[data-testid="stVerticalBlockBorderWrapper"] { padding:.15rem; }

        /* KPI cards */
        .kpi { padding:1.15rem 1.25rem; height:100%; transition:border-color .2s ease; }
        .kpi:hover { border-color:rgba(255,255,255,.13) !important; }
        .kpi-label { font-size:.76rem; color:var(--muted); font-weight:500; margin-bottom:.55rem;
                     display:flex; align-items:center; gap:.3rem; }
        .kpi-value { font-size:2rem; font-weight:700; color:var(--text); line-height:1;
                     letter-spacing:-.025em; }
        .kpi-unit { font-size:.95rem; font-weight:500; color:var(--faint); margin-left:.3rem;
                    letter-spacing:0; }
        .kpi-sub { font-size:.8rem; font-weight:600; margin-top:.6rem; color:var(--muted); }
        .kpi-empty .kpi-value { color:#39424f; font-weight:600; }

        /* Status callout */
        .status { border-radius:var(--radius); padding:1rem 1.25rem; display:flex; gap:.85rem;
                  align-items:flex-start; border:1px solid; margin:.1rem 0 .2rem;
                  box-shadow:var(--shadow); }
        .status-ic { font-size:1.15rem; line-height:1.4; }
        .status-title { font-weight:700; font-size:.97rem; letter-spacing:-.01em; }
        .status-text { font-size:.88rem; color:#c2cad4; margin-top:.15rem; line-height:1.45; }
        .s-success { background:rgba(16,185,129,.09); border-color:rgba(16,185,129,.30); }
        .s-success .status-title { color:#34d399; }
        .s-warning { background:rgba(245,158,11,.09); border-color:rgba(245,158,11,.30); }
        .s-warning .status-title { color:#fbbf24; }
        .s-danger  { background:rgba(239,68,68,.09);  border-color:rgba(239,68,68,.30); }
        .s-danger  .status-title { color:#f87171; }
        .s-info    { background:rgba(96,165,250,.09); border-color:rgba(96,165,250,.28); }
        .s-info    .status-title { color:#60a5fa; }
        .s-neutral { background:rgba(100,116,139,.09); border-color:rgba(100,116,139,.28); }
        .s-neutral .status-title { color:#94a3b8; }

        /* Recovery card header */
        .rec-top { display:flex; justify-content:space-between; align-items:baseline;
                   margin-bottom:.15rem; }
        .rec-label { font-size:.78rem; color:var(--muted); font-weight:600; }
        .rec-value { font-size:1.5rem; font-weight:700; color:var(--text); letter-spacing:-.02em; }
        .rec-value .u { font-size:.82rem; color:var(--faint); font-weight:500; margin-left:.18rem; }
        .rec-trend { font-size:.76rem; font-weight:600; }

        /* Empty state */
        .empty { text-align:center; padding:2.6rem 1rem; color:var(--faint);
                 border:1px dashed rgba(255,255,255,.10); border-radius:14px;
                 background:rgba(255,255,255,.012); }
        .empty-ic { font-size:1.9rem; opacity:.5; margin-bottom:.5rem; }
        .empty-tx { font-size:.92rem; line-height:1.5; }

        /* Today strip */
        .today-head { display:flex; align-items:baseline; gap:.6rem; margin-bottom:.9rem; }
        .today-head .d1 { font-size:.64rem; color:var(--accent); text-transform:uppercase;
                          letter-spacing:.14em; font-weight:700; }
        .today-head .d2 { font-size:1.05rem; font-weight:700; color:var(--text);
                          letter-spacing:-.01em; }
        .today-grid { display:grid; gap:.6rem;
                      grid-template-columns:repeat(auto-fit, minmax(94px, 1fr)); }
        .tstat { padding:.7rem .5rem; text-align:center; box-shadow:none;
                 display:flex; flex-direction:column; align-items:center; gap:.4rem; }
        .tstat-l { font-size:.62rem; color:var(--muted); text-transform:uppercase;
                   letter-spacing:.06em; font-weight:600; }
        .tstat-v { font-size:1.24rem; font-weight:700; color:var(--text); line-height:1;
                   letter-spacing:-.02em; white-space:nowrap; }
        .tstat-v .u { font-size:.7rem; color:var(--faint); font-weight:500; margin-left:.1rem; }
        .tstat-v.muted { color:#414b59; font-size:1.05rem; font-weight:700; }

        /* KPI grid (responsive: 4-up desktop, 2-up phone) */
        .kpi-grid { display:grid; gap:.8rem;
                    grid-template-columns:repeat(auto-fit, minmax(150px, 1fr)); }

        /* Session log */
        .slog { display:flex; flex-direction:column; max-height:340px; overflow-y:auto; }
        .slog-row { display:flex; align-items:center; gap:1rem; padding:.65rem .15rem;
                    border-bottom:1px solid var(--line-soft); }
        .slog-row:last-child { border-bottom:none; }
        .slog-date { font-size:.86rem; color:#c8cfd9; font-weight:600; width:130px; flex-shrink:0; }
        .slog-date .dim { color:var(--faint); font-weight:500; }
        .slog-chips { display:flex; flex-wrap:wrap; gap:.45rem; }
        .tchip { display:inline-flex; align-items:center; gap:.4rem; border-radius:999px;
                 padding:.3rem .72rem; font-size:.8rem; font-weight:600; color:var(--text);
                 background:rgba(255,255,255,.04); border:1px solid transparent; }
        .tchip .dot { width:8px; height:8px; border-radius:50%; }

        /* Buttons */
        .stButton button { border-radius:11px !important; font-weight:600 !important;
                           transition:transform .05s ease, border-color .2s ease; }
        .stButton button:active { transform:translateY(1px); }
        .stButton button[kind="primary"] { box-shadow:0 4px 14px -4px rgba(16,185,129,.45); }

        /* Mobile */
        @media (max-width: 640px) {
            .block-container { padding-left:.85rem; padding-right:.85rem; padding-top:1.5rem; }
            .app-title { font-size:1.5rem; }
            .app-sub { font-size:.84rem; }
            .today-grid { grid-template-columns:repeat(auto-fit, minmax(82px, 1fr)); }
            .kpi-grid { grid-template-columns:repeat(2, 1fr); }
            .kpi-value { font-size:1.75rem; }
            .tstat-v { font-size:1.12rem; }
            .slog-date { width:104px; font-size:.82rem; }
        }
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


def hm(hours) -> str:
    """Format a number of hours as 'Hh Mm' (e.g. 8.2 -> '8h 12m')."""
    if hours is None or pd.isna(hours):
        return "—"
    total = int(round(float(hours) * 60))
    h, m = divmod(total, 60)
    return f"{h}h {m}m" if m else f"{h}h"


def today_card(date_label: str, items: list[tuple]):
    """A glanceable, responsive grid of today's stats (reflows to 2-up on
    mobile). items = [(label, value, unit), ...]; value None renders a muted dash."""
    head = (f'<div class="today-head"><span class="d1">Today</span>'
            f'<span class="d2">{date_label}</span></div>')
    tiles = []
    for label, value, unit in items:
        if value is None:
            v = '<span class="tstat-v muted">—</span>'
        else:
            u = f'<span class="u">{unit}</span>' if unit else ""
            v = f'<span class="tstat-v">{value}{u}</span>'
        tiles.append(f'<div class="tstat"><div class="tstat-l">{label}</div>{v}</div>')
    st.markdown(f'{head}<div class="today-grid">{"".join(tiles)}</div>',
                unsafe_allow_html=True)


def kpi(label: str, value: str, unit: str | None = None, sub: str | None = None,
        sub_color: str | None = None, help: str | None = None, empty: bool = False) -> str:
    """Return the HTML for one KPI card. `value` is the big number; `empty` mutes it."""
    unit_html = f'<span class="kpi-unit">{unit}</span>' if unit else ""
    hint = f'<span title="{help}" style="cursor:help;color:#5b6573;">ⓘ</span>' if help else ""
    sub_html = ""
    if sub:
        color = f"color:{sub_color};" if sub_color else ""
        sub_html = f'<div class="kpi-sub" style="{color}">{sub}</div>'
    cls = "kpi kpi-empty" if empty else "kpi"
    return (f'<div class="{cls}"><div class="kpi-label">{label} {hint}</div>'
            f'<div class="kpi-value">{value}{unit_html}</div>{sub_html}</div>')


def kpi_grid(cards: list[str]):
    """Render KPI card HTML strings in a responsive grid (4-up desktop, 2-up phone)."""
    st.markdown(f'<div class="kpi-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


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
    x = alt.X("date:T", title=None, axis=alt.Axis(format="%a %b %d", tickCount=6))

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
        .encode(x=x, y=alt.Y("weight_kg:Q", scale=alt.Scale(zero=False)))
    )
    line = (
        alt.Chart(data.dropna(subset=["weight_ma7"]))
        .mark_line(strokeWidth=2.5, color=ACCENT)
        .encode(x=x, y=alt.Y("weight_ma7:Q", scale=alt.Scale(zero=False)))
    )
    # Full-height hover rule that snaps to the nearest day (big hit target).
    nearest = alt.selection_point(fields=["date"], nearest=True, on="pointerover",
                                  empty=False, clear="pointerout")
    rule = (
        alt.Chart(data).mark_rule(color="rgba(255,255,255,0.28)", strokeWidth=1)
        .encode(
            x=x,
            opacity=alt.condition(nearest, alt.value(1), alt.value(0)),
            tooltip=[alt.Tooltip("date:T", title="Date", format="%a %b %d"),
                     alt.Tooltip("weight_kg:Q", title="Weight", format=".1f"),
                     alt.Tooltip("weight_ma7:Q", title="7-day avg", format=".2f")],
        )
        .add_params(nearest)
    )
    chart = (area + line + points + rule).properties(height=300)
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
          transform=None, height: int = 120, label: str | None = None,
          tip_hm: bool = False):
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

    x = alt.X("date:T", title=None, axis=alt.Axis(format="%a %b %d", tickCount=3))
    y = alt.Y(f"{col}:Q", title=None, scale=alt.Scale(zero=False))
    if tip_hm:
        meas["__tip"] = meas[col].map(hm)
        value_tip = alt.Tooltip("__tip:N", title=label or col)
    else:
        value_tip = alt.Tooltip(f"{col}:Q", title=label or col, format=fmt)
    tip = [alt.Tooltip("date:T", title="Date", format="%a %b %d"), value_tip]

    line = alt.Chart(meas).mark_line(strokeWidth=2, color=color).encode(
        x=x, y=y, detail="seg:N")
    pts = alt.Chart(meas).mark_circle(size=28, color=color, opacity=0.9).encode(x=x, y=y)
    # Full-height hover rule snapping to nearest day (large hit target).
    nearest = alt.selection_point(fields=["date"], nearest=True, on="pointerover",
                                  empty=False, clear="pointerout")
    rule = (
        alt.Chart(meas).mark_rule(color="rgba(255,255,255,0.25)", strokeWidth=1)
        .encode(x=x, opacity=alt.condition(nearest, alt.value(1), alt.value(0)), tooltip=tip)
        .add_params(nearest)
    )
    chart = (line + pts + rule).properties(height=height)
    return _base_theme(chart, y_grid=False)

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

# Apple system colours (dark variants).
ACCENT = "#30d158"   # green
BLUE = "#0a84ff"
INDIGO = "#5e5ce6"
TEAL = "#64d2ff"
AMBER = "#ff9f0a"
RED = "#ff453a"
SLATE = "#8e8e93"

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
            --bg:#000000; --surface:#1c1c1e; --surface-2:#2c2c2e;
            --line:rgba(255,255,255,.06); --sep:rgba(84,84,88,.45);
            --text:#f5f5f7; --muted:rgba(235,235,245,.62); --faint:rgba(235,235,245,.32);
            --accent:#30d158; --radius:20px;
        }

        html, body, .stApp, [data-testid="stAppViewContainer"],
        [data-testid="stSidebar"], button, input, textarea, select {
            font-family:-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text',
                        'Inter', 'Segoe UI', sans-serif !important;
            -webkit-font-smoothing:antialiased; -moz-osx-font-smoothing:grayscale;
        }
        .stApp { background:var(--bg); }

        .block-container { padding-top:2.2rem; padding-bottom:5rem; max-width:1100px; }
        [data-testid="stHeader"] { background:transparent; }
        #MainMenu, footer { visibility:hidden; }

        /* Large navigation-style header */
        .app-head { display:flex; align-items:flex-end; justify-content:space-between;
                    gap:1rem; margin-bottom:1.2rem; flex-wrap:wrap; }
        .app-title { font-size:2.05rem; font-weight:700; letter-spacing:-.03em; margin:0;
                     line-height:1.05; color:var(--text); }
        .app-sub { color:var(--muted); font-size:.92rem; margin-top:.35rem; font-weight:400; }
        .app-meta { color:var(--faint); font-size:.82rem; text-align:right; }

        /* Section header (Apple "title3": bold, sentence case) */
        .section-title { font-size:1.16rem; font-weight:700; letter-spacing:-.02em;
            color:var(--text); margin:2.1rem 0 .85rem; }

        /* Flat grouped cards — no border, no heavy shadow (iOS look) */
        .kpi, .sum-card,
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background:var(--surface) !important; border:none !important;
            border-radius:var(--radius) !important; box-shadow:none !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] { padding:.2rem; }

        /* KPI / trend cards */
        .kpi { padding:1.15rem 1.25rem; height:100%; }
        .kpi-label { font-size:.82rem; color:var(--muted); font-weight:500; margin-bottom:.55rem;
                     display:flex; align-items:center; gap:.3rem; }
        .kpi-value { font-size:2.05rem; font-weight:700; color:var(--text); line-height:1;
                     letter-spacing:-.03em; }
        .kpi-unit { font-size:.95rem; font-weight:500; color:var(--faint); margin-left:.3rem;
                    letter-spacing:0; }
        .kpi-sub { font-size:.82rem; font-weight:500; margin-top:.6rem; color:var(--muted); }
        .kpi-empty .kpi-value { color:#48484a; font-weight:600; }

        /* Status callout */
        .status { border-radius:var(--radius); padding:1rem 1.2rem; display:flex; gap:.8rem;
                  align-items:flex-start; background:var(--surface); }
        .status-ic { font-size:1.1rem; line-height:1.45; }
        .status-title { font-weight:600; font-size:.97rem; letter-spacing:-.01em; }
        .status-text { font-size:.88rem; color:var(--muted); margin-top:.15rem; line-height:1.45; }
        .s-success .status-title { color:#30d158; }
        .s-warning .status-title { color:#ffd60a; }
        .s-danger  .status-title { color:#ff453a; }
        .s-info    .status-title { color:#0a84ff; }
        .s-neutral .status-title { color:#98a2b1; }
        .status::before { content:""; width:3px; align-self:stretch; border-radius:3px;
                          background:currentColor; flex-shrink:0; }
        .s-success { color:#30d158; } .s-warning { color:#ffd60a; }
        .s-danger { color:#ff453a; } .s-info { color:#0a84ff; } .s-neutral { color:#98a2b1; }
        .status > .status-ic, .status > div { color:var(--text); }

        /* Recovery card header */
        .rec-top { display:flex; justify-content:space-between; align-items:baseline;
                   margin-bottom:.15rem; }
        .rec-label { font-size:.84rem; color:var(--muted); font-weight:500; }
        .rec-value { font-size:1.55rem; font-weight:700; color:var(--text); letter-spacing:-.025em; }
        .rec-value .u { font-size:.82rem; color:var(--faint); font-weight:500; margin-left:.18rem; }
        .rec-trend { font-size:.78rem; font-weight:600; }

        /* Empty state */
        .empty { text-align:center; padding:2.4rem 1rem; color:var(--faint); }
        .empty-ic { font-size:1.9rem; opacity:.5; margin-bottom:.5rem; }
        .empty-tx { font-size:.92rem; line-height:1.5; }

        /* Summary (Apple Health "favorites") cards */
        .sum-head { display:flex; align-items:baseline; gap:.6rem; margin-bottom:.95rem; }
        .sum-head .d1 { font-size:.66rem; color:var(--accent); text-transform:uppercase;
                        letter-spacing:.12em; font-weight:700; }
        .sum-head .d2 { font-size:1.1rem; font-weight:700; color:var(--text); letter-spacing:-.02em; }
        .sum-grid { display:grid; gap:.7rem;
                    grid-template-columns:repeat(auto-fit, minmax(158px, 1fr)); }
        .sum-card { padding:1.05rem 1.1rem; display:flex; flex-direction:column; }
        .sum-top { display:flex; align-items:center; gap:.45rem; margin-bottom:.75rem; }
        .sum-ic { width:25px; height:25px; border-radius:7px; display:inline-flex;
                  align-items:center; justify-content:center; flex-shrink:0; }
        .sum-name { font-size:.85rem; font-weight:600; letter-spacing:-.01em; }
        .sum-val { font-size:1.6rem; font-weight:700; color:var(--text); line-height:1;
                   letter-spacing:-.03em; }
        .sum-val .u { font-size:.8rem; color:var(--faint); font-weight:500; margin-left:.14rem; }
        .sum-val.muted { color:#48484a; font-size:1.05rem; font-weight:600; }
        .sum-sub { font-size:.76rem; color:var(--faint); margin-top:.5rem; font-weight:500; }

        /* KPI grid (responsive) */
        .kpi-grid { display:grid; gap:.7rem;
                    grid-template-columns:repeat(auto-fit, minmax(158px, 1fr)); }

        /* Session log */
        .slog { display:flex; flex-direction:column; max-height:360px; overflow-y:auto; }
        .slog-row { display:flex; align-items:center; gap:1rem; padding:.7rem .15rem;
                    border-bottom:1px solid var(--line); }
        .slog-row:last-child { border-bottom:none; }
        .slog-date { font-size:.88rem; color:var(--text); font-weight:500; width:130px; flex-shrink:0; }
        .slog-date .dim { color:var(--faint); font-weight:400; }
        .slog-chips { display:flex; flex-wrap:wrap; gap:.45rem; }
        .tchip { display:inline-flex; align-items:center; gap:.4rem; border-radius:999px;
                 padding:.32rem .75rem; font-size:.82rem; font-weight:600; color:var(--text);
                 background:var(--surface-2); }
        .tchip .dot { width:8px; height:8px; border-radius:50%; }

        /* Buttons — pill, Apple-tinted */
        .stButton button { border-radius:12px !important; font-weight:600 !important;
                           transition:transform .06s ease, opacity .2s ease; }
        .stButton button:active { transform:scale(.985); }

        /* Mobile */
        @media (max-width: 640px) {
            .block-container { padding-left:.9rem; padding-right:.9rem; padding-top:1.4rem; }
            .app-title { font-size:1.7rem; }
            .app-sub { font-size:.85rem; }
            .sum-grid, .kpi-grid { grid-template-columns:repeat(2, 1fr); gap:.6rem; }
            .kpi-value { font-size:1.8rem; }
            .sum-val { font-size:1.42rem; }
            .slog-date { width:100px; font-size:.83rem; }
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


# Apple-system metric colours.
METRIC_COLORS = {
    "weight": "#5e5ce6",   # indigo
    "sleep": "#64d2ff",    # cyan
    "steps": "#ff9f0a",    # orange
    "calories": "#ff453a", # red
    "heart": "#ff375f",    # pink
    "battery": "#30d158",  # green
    "sessions": "#0a84ff", # blue
}

# Lucide-style stroke icons (clean, SF-Symbol-adjacent).
_ICONS = {
    "weight": '<circle cx="12" cy="5" r="3"/><path d="M6.5 8a2 2 0 0 0-1.9 1.46L2.1 18.5A2 2 0 0 0 4 21h16a2 2 0 0 0 1.9-2.54L19.4 9.5A2 2 0 0 0 17.5 8Z"/>',
    "sleep": '<path d="M12 3a6.4 6.4 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
    "steps": '<ellipse cx="8" cy="8.5" rx="2.4" ry="4"/><ellipse cx="15.5" cy="14.5" rx="2.4" ry="4"/>',
    "calories": '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.07-2.14-.22-4.05 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.15.43-2.29 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
    "heart": '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.29 1.51 4.04 3 5.5l7 7Z"/>',
    "battery": '<rect x="2" y="7" width="16" height="10" rx="2.5"/><line x1="22" y1="11" x2="22" y2="13"/>',
    "sessions": '<path d="m6.5 6.5 11 11"/><path d="m21 21-1-1"/><path d="m3 3 1 1"/><path d="m18 22 4-4"/><path d="m2 6 4-4"/><path d="m3 10 7-7"/><path d="m14 21 7-7"/>',
}


def _icon(key: str, color: str, size: int = 16) -> str:
    inner = _ICONS.get(key, "")
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="2.1" stroke-linecap="round" '
            f'stroke-linejoin="round">{inner}</svg>')


def summary_cards(date_label: str, items: list[dict]):
    """Apple-Health-style favourites grid. Each item:
    {icon, name, value, unit, sub}; value None -> 'No Data'."""
    head = (f'<div class="sum-head"><span class="d1">Today</span>'
            f'<span class="d2">{date_label}</span></div>')
    cards = []
    for it in items:
        color = METRIC_COLORS.get(it["icon"], "#8e8e93")
        if it.get("value") is None:
            val = '<span class="sum-val muted">No Data</span>'
        else:
            u = f'<span class="u">{it["unit"]}</span>' if it.get("unit") else ""
            val = f'<span class="sum-val">{it["value"]}{u}</span>'
        sub = f'<div class="sum-sub">{it["sub"]}</div>' if it.get("sub") else ""
        cards.append(
            f'<div class="sum-card"><div class="sum-top">'
            f'<span class="sum-ic" style="background:{color}26;">{_icon(it["icon"], color)}</span>'
            f'<span class="sum-name" style="color:{color};">{it["name"]}</span></div>'
            f'{val}{sub}</div>'
        )
    st.markdown(f'{head}<div class="sum-grid">{"".join(cards)}</div>',
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
    """Daily weigh-ins (faint dots) + 7-day moving-average line with area fill.

    The x-axis fits the actual weigh-in dates (with a little padding) rather than
    the whole selected range, so a couple of early weigh-ins don't float in a
    huge empty chart."""
    data = df[["date", "weight_kg", "weight_ma7"]].copy()

    weighed = data.dropna(subset=["weight_kg"])
    if not weighed.empty:
        pad = pd.Timedelta(days=1)
        dmin, dmax = weighed["date"].min() - pad, weighed["date"].max() + pad
        xscale = alt.Scale(domain=[dmin, dmax])
    else:
        xscale = alt.Scale()
    n_pts = weighed["date"].nunique()
    x = alt.X("date:T", title=None, scale=xscale,
              axis=alt.Axis(format="%a %b %d", tickCount=min(max(n_pts, 2), 6)))

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

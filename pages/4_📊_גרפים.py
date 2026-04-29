import json
import config
import common
from datetime import date, timedelta
from collections import Counter, defaultdict
import streamlit as st
import plotly.graph_objects as go
import supabase_client as db

NUTRIENT_LABELS = common.NUTRIENT_LABELS

st.set_page_config(page_title="גרפים", page_icon="📊", layout="centered")
common.page_setup()

if st.button("🏠 בית"): st.switch_page("app.py")
st.title("📊 גרפים ומגמות")

# ── shared chart settings ─────────────────────────────────────────────────────
# staticPlot=True → no toolbar, no zoom/pan, finger scrolls the page normally
PLOTLY_CONFIG = {"staticPlot": True}

MONTH_HE = ["", "ינו", "פבר", "מרץ", "אפר", "מאי", "יוני",
            "יולי", "אוג", "ספט", "אוק", "נוב", "דצמ"]

def short_date(iso: str) -> str:
    """'2026-03-21' → 'מרץ 21'"""
    try:
        _, m, d = iso.split("-")
        return f"{MONTH_HE[int(m)]} {int(d)}"
    except Exception:
        return iso

# Cream + sage chart palette (matches common.SHARED_CSS)
SAGE_DEEP = "#4F6B52"
SAGE      = "#6B8E6F"
SAGE_SOFT = "#A8C0A0"
CLAY      = "#B4805E"
CORAL     = "#C36A55"
HONEY     = "#B8923A"
MAUVE     = "#8E6E7F"
TEXT_DARK = "#2A3829"
GRID_SOFT = "rgba(107, 142, 111, 0.18)"

BASE_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Assistant, Arial, sans-serif", size=13, color=TEXT_DARK),
    height=220,
    margin=dict(l=50, r=50, t=15, b=35),
    xaxis=dict(showgrid=True, gridcolor=GRID_SOFT, linecolor=GRID_SOFT,
               tickfont=dict(color=TEXT_DARK)),
    yaxis=dict(showgrid=True, gridcolor=GRID_SOFT, zeroline=False,
               linecolor=GRID_SOFT, tickfont=dict(color=TEXT_DARK)),
    showlegend=False,
)

# ── Weight chart ──────────────────────────────────────────────────────────────
st.markdown("### ⚖️ מגמת משקל")

weight_rows = db.select("weight_log", order="log_date.asc")

if len(weight_rows) < 2:
    st.info("יש לרשום לפחות שתי שקילות כדי לראות גרף. שלחי את משקלך בשיחה!")
else:
    dates   = [short_date(r["log_date"]) for r in weight_rows]
    weights = [float(r["weight_kg"])    for r in weight_rows]

    first_w, last_w = weights[0], weights[-1]
    delta = last_w - first_w
    delta_str = f"{'↓' if delta < 0 else '↑'} {abs(delta):.1f} ק״ג"

    col1, col2, col3 = st.columns(3)
    col1.metric("משקל נוכחי",  f"{last_w:.1f} ק״ג", delta_str)
    col2.metric("משקל התחלתי", f"{first_w:.1f} ק״ג")
    col3.metric("מדידות",      len(weight_rows))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=weights,
        mode="lines+markers",
        line=dict(color=SAGE, width=3),
        marker=dict(size=8, color=SAGE_DEEP),
        hoverinfo="skip",
    ))
    # trend line (linear regression) — only when ≥3 points
    if len(weights) >= 3:
        n = len(weights)
        xi = list(range(n))
        mx, my = sum(xi)/n, sum(weights)/n
        slope = sum((xi[i]-mx)*(weights[i]-my) for i in range(n)) / \
                sum((xi[i]-mx)**2 for i in range(n))
        intercept = my - slope * mx
        trend = [intercept + slope * i for i in xi]
        fig.add_trace(go.Scatter(
            x=dates, y=trend,
            mode="lines",
            line=dict(color=CLAY, width=2, dash="dash"),
            hoverinfo="skip",
        ))

    y_pad = max((max(weights) - min(weights)) * 0.25, 0.5)
    fig.update_layout(**BASE_LAYOUT)
    fig.update_yaxes(range=[min(weights) - y_pad, max(weights) + y_pad])
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
    st.caption("קו ירוק — משקל בפועל  |  קו חימר — מגמה")

st.divider()

# ── Blood sugar chart ─────────────────────────────────────────────────────────
st.markdown("### 🩸 מגמת סוכר בדם")

try:
    bs_rows = db.select("blood_sugar_log", order="log_date.asc")
except Exception:
    bs_rows = []

if len(bs_rows) < 2:
    st.info("יש לרשום לפחות שתי מדידות סוכר כדי לראות גרף. ספרי לעוזרת את הסוכר שלך בשיחה!")
else:
    bs_dates  = [short_date(r["log_date"]) for r in bs_rows]
    bs_values = [float(r["value_mgdl"])    for r in bs_rows]

    last_bs = bs_values[-1]
    avg_bs  = sum(bs_values) / len(bs_values)

    col1, col2, col3 = st.columns(3)
    col1.metric("מדידה אחרונה", f"{last_bs:.0f} mg/dL")
    col2.metric("ממוצע", f"{avg_bs:.0f} mg/dL")
    col3.metric("מדידות", len(bs_rows))

    fig_bs = go.Figure()
    fig_bs.add_trace(go.Scatter(
        x=bs_dates, y=bs_values,
        mode="lines+markers",
        line=dict(color=CORAL, width=3),
        marker=dict(size=8, color=CORAL),
        hoverinfo="skip",
    ))
    # trend line when ≥3 points
    if len(bs_values) >= 3:
        n = len(bs_values)
        xi = list(range(n))
        mx, my = sum(xi)/n, sum(bs_values)/n
        slope = sum((xi[i]-mx)*(bs_values[i]-my) for i in range(n)) / \
                sum((xi[i]-mx)**2 for i in range(n))
        intercept = my - slope * mx
        trend = [intercept + slope * i for i in xi]
        fig_bs.add_trace(go.Scatter(
            x=bs_dates, y=trend,
            mode="lines",
            line=dict(color=CLAY, width=2, dash="dash"),
            hoverinfo="skip",
        ))

    y_pad = max((max(bs_values) - min(bs_values)) * 0.25, 5)
    fig_bs.update_layout(**BASE_LAYOUT)
    fig_bs.update_yaxes(range=[min(bs_values) - y_pad, max(bs_values) + y_pad])
    st.plotly_chart(fig_bs, use_container_width=True, config=PLOTLY_CONFIG)
    st.caption("קו אלמוג — סוכר בפועל  |  קו חימר — מגמה")

st.divider()

# ── Nutrient trend (user-selectable) ──────────────────────────────────────────
st.markdown("### 🍽️ מגמת רכיב תזונתי ב-14 הימים האחרונים")

goals = common.get_daily_goals()
from_date    = (date.today() - timedelta(days=13)).isoformat()
all_meals    = db.select("meal_log", order="meal_date.asc")
recent_meals = [m for m in all_meals if m.get("meal_date", "") >= from_date]

# Collect all nutrient keys that appear in recent meals
available_keys: set[str] = set()
for m in recent_meals:
    n = m.get("nutrients")
    if isinstance(n, str):
        try:
            n = json.loads(n)
        except Exception:
            n = None
    if isinstance(n, dict):
        available_keys.update(n.keys())

# Prefer keys that also have a goal; fall back to any that appear in meals
pickable = sorted(available_keys | set(goals.keys()))

if not pickable:
    st.info("עוד אין נתוני תזונה. לאחר הגדרת יעדים ורישום ארוחות — מגמות יופיעו כאן.")
else:
    # Display labels for the selector
    def _label(k: str) -> str:
        name, unit = NUTRIENT_LABELS.get(k, (k, ""))
        return f"{name} ({unit})" if unit else name

    choice = st.selectbox("בחרי רכיב לתצוגה:", pickable, format_func=_label, index=0)

    day_labels   = [(date.today() - timedelta(days=i)).isoformat() for i in range(13, -1, -1)]
    short_labels = [short_date(d) for d in day_labels]

    by_day: dict[str, float] = defaultdict(float)
    for m in recent_meals:
        n = m.get("nutrients")
        if isinstance(n, str):
            try:
                n = json.loads(n)
            except Exception:
                continue
        if not isinstance(n, dict):
            continue
        val = n.get(choice)
        if val is None:
            continue
        try:
            by_day[m["meal_date"]] += float(val)
        except (TypeError, ValueError):
            pass

    vals = [by_day.get(d, 0) for d in day_labels]
    has_data = [v for v in vals if v > 0]

    if not has_data:
        st.info("אין עדיין נתונים לרכיב זה ב-14 הימים האחרונים.")
    else:
        avg_val = sum(has_data) / len(has_data)
        _, unit = NUTRIENT_LABELS.get(choice, (choice, ""))
        goal_val = goals.get(choice)

        col1, col2, col3 = st.columns(3)
        col1.metric("ממוצע יומי", f"{avg_val:.0f} {unit}".strip())
        col2.metric("ימים עם נתונים", len(has_data))
        if goal_val:
            col3.metric("יעד יומי", f"{float(goal_val):.0f} {unit}".strip())

        bar_colors = [SAGE if v > 0 else "#E4ECDD" for v in vals]
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=short_labels, y=vals,
            marker_color=bar_colors,
            hoverinfo="skip",
        ))
        if goal_val:
            try:
                gv = float(goal_val)
                fig2.add_hline(y=gv, line_dash="dash", line_color=CLAY, line_width=2)
            except (TypeError, ValueError):
                pass
        fig2.update_layout(**BASE_LAYOUT)
        fig2.update_layout(height=260, margin=dict(l=50, r=50, t=15, b=50))
        fig2.update_yaxes(tickformat="d")
        st.plotly_chart(fig2, use_container_width=True, config=PLOTLY_CONFIG)
        caption = "הערכות גסות בלבד."
        if goal_val:
            caption += " הקו בצבע חימר — יעד יומי."
        st.caption(caption)

st.divider()

# ── Sleep chart ───────────────────────────────────────────────────────────────
st.markdown("### 😴 מגמת שינה")

try:
    sleep_rows = db.select("sleep_log", order="log_date.asc")
except Exception:
    sleep_rows = []

QUALITY_SCORE = {"גרוע מאוד": 1, "גרוע": 2, "בינוני": 3, "טוב": 4, "מעולה": 5}

if len(sleep_rows) < 2:
    st.info("יש לרשום לפחות שני לילות כדי לראות גרף. ספרי לעוזרת בבוקר איך ישנת!")
else:
    s_dates = [short_date(r["log_date"]) for r in sleep_rows]
    s_hours = [float(r["duration_hours"]) if r.get("duration_hours") is not None else None
               for r in sleep_rows]
    s_scores = [QUALITY_SCORE.get(r.get("quality", ""), None) for r in sleep_rows]

    valid_hours = [h for h in s_hours if h is not None]
    valid_scores = [s for s in s_scores if s is not None]

    col1, col2, col3 = st.columns(3)
    if valid_hours:
        col1.metric("ממוצע שעות", f"{sum(valid_hours)/len(valid_hours):.1f}")
    if valid_scores:
        col2.metric("ממוצע איכות", f"{sum(valid_scores)/len(valid_scores):.1f}/5")
    col3.metric("לילות", len(sleep_rows))

    # Duration bars
    fig_s = go.Figure()
    fig_s.add_trace(go.Bar(
        x=s_dates,
        y=[h if h is not None else 0 for h in s_hours],
        marker_color=MAUVE,
        name="שעות",
        hoverinfo="skip",
    ))
    # Quality dots on a secondary y-axis
    quality_x = [d for d, s in zip(s_dates, s_scores) if s is not None]
    quality_y = [s for s in s_scores if s is not None]
    if quality_y:
        fig_s.add_trace(go.Scatter(
            x=quality_x, y=quality_y,
            mode="markers",
            marker=dict(size=11, color=HONEY,
                        line=dict(color=TEXT_DARK, width=1)),
            yaxis="y2",
            name="איכות",
            hoverinfo="skip",
        ))
        fig_s.update_layout(
            yaxis2=dict(overlaying="y", side="right", range=[0.5, 5.5],
                        tickvals=[1,2,3,4,5], gridcolor="rgba(0,0,0,0)"),
        )
    fig_s.update_layout(**BASE_LAYOUT)
    fig_s.update_layout(height=260, margin=dict(l=50, r=50, t=15, b=50))
    st.plotly_chart(fig_s, use_container_width=True, config=PLOTLY_CONFIG)
    st.caption("עמודות — שעות שינה  |  נקודות — איכות (1=גרוע מאוד, 5=מעולה)")

st.divider()

# ── Blood markers over time ───────────────────────────────────────────────────
st.markdown("### 🩸 מגמות בדיקות דם לאורך זמן")

blood_rows = db.select("blood_results", order="test_date.asc")

if not blood_rows:
    st.info("טרם הועלו בדיקות דם. העלי בדיקה בדף 'בדיקות דם'!")
else:
    marker_timeseries: dict[str, list[tuple[str, float]]] = defaultdict(list)

    for row in blood_rows:
        test_date_str = row.get("test_date", "")
        markers_raw   = row.get("markers")
        if not markers_raw or not test_date_str:
            continue
        try:
            markers = json.loads(markers_raw) if isinstance(markers_raw, str) else markers_raw
            for marker_name, value in markers.items():
                try:
                    marker_timeseries[marker_name].append((test_date_str, float(value)))
                except (TypeError, ValueError):
                    pass
        except Exception:
            pass

    min_points = 2 if len(blood_rows) >= 2 else 1
    plottable  = {k: v for k, v in marker_timeseries.items() if len(v) >= min_points}

    if not plottable:
        st.info("צברי לפחות 2 בדיקות דם כדי לראות מגמות.")
    else:
        BLOOD_COLORS = [SAGE_DEEP, CLAY, MAUVE, CORAL, HONEY, SAGE, "#7E8AAB", "#A86B59"]

        for idx, (marker_name, data_points) in enumerate(sorted(plottable.items())):
            pts = sorted(data_points, key=lambda x: x[0])
            xs  = [short_date(p[0]) for p in pts]
            ys  = [p[1] for p in pts]
            color = BLOOD_COLORS[idx % len(BLOOD_COLORS)]

            # Title above the chart (avoids RTL/Plotly clash)
            st.markdown(f"**{marker_name}**")

            fig_b = go.Figure()
            fig_b.add_trace(go.Scatter(
                x=xs, y=ys,
                mode="lines+markers",
                line=dict(color=color, width=2.5),
                marker=dict(size=9, color=color),
                hoverinfo="skip",
            ))
            y_pad = max((max(ys) - min(ys)) * 0.25, max(ys) * 0.05, 1)
            fig_b.update_layout(**BASE_LAYOUT)
            fig_b.update_yaxes(range=[min(ys) - y_pad, max(ys) + y_pad])
            st.plotly_chart(fig_b, use_container_width=True, config=PLOTLY_CONFIG)

        st.caption(f"מוצגים {len(plottable)} סמנים מתוך {len(blood_rows)} בדיקות")

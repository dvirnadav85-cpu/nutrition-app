import json
import config
import common
from datetime import date, timedelta
from collections import Counter, defaultdict
import streamlit as st
import plotly.graph_objects as go
import supabase_client as db

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

BASE_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Arial, sans-serif", size=13),
    height=220,
    margin=dict(l=50, r=50, t=15, b=35),   # equal L/R, small top (no Plotly title)
    xaxis=dict(showgrid=True, gridcolor="#e5e5e5"),
    yaxis=dict(showgrid=True, gridcolor="#e5e5e5", zeroline=False),
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
        line=dict(color="#4CAF50", width=3),
        marker=dict(size=8, color="#4CAF50"),
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
            line=dict(color="#FF9800", width=2, dash="dash"),
            hoverinfo="skip",
        ))

    y_pad = max((max(weights) - min(weights)) * 0.25, 0.5)
    fig.update_layout(**BASE_LAYOUT)
    fig.update_yaxes(range=[min(weights) - y_pad, max(weights) + y_pad])
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
    st.caption("🟢 קו ירוק — משקל בפועל  |  🟠 קו כתום — מגמה")

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
        line=dict(color="#E53935", width=3),
        marker=dict(size=8, color="#E53935"),
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
            line=dict(color="#FF9800", width=2, dash="dash"),
            hoverinfo="skip",
        ))

    y_pad = max((max(bs_values) - min(bs_values)) * 0.25, 5)
    fig_bs.update_layout(**BASE_LAYOUT)
    fig_bs.update_yaxes(range=[min(bs_values) - y_pad, max(bs_values) + y_pad])
    st.plotly_chart(fig_bs, use_container_width=True, config=PLOTLY_CONFIG)
    st.caption("🔴 קו אדום — סוכר בפועל  |  🟠 קו כתום — מגמה")

st.divider()

# ── Meals per day ─────────────────────────────────────────────────────────────
st.markdown("### 🍽️ ארוחות ב-14 הימים האחרונים")

from_date    = (date.today() - timedelta(days=13)).isoformat()
all_meals    = db.select("meal_log", order="meal_date.asc")
recent_meals = [m for m in all_meals if m.get("meal_date", "") >= from_date]

if not recent_meals:
    st.info("טרם נרשמו ארוחות. ספרי לעוזרת מה אכלת בשיחה!")
else:
    day_labels   = [(date.today() - timedelta(days=i)).isoformat() for i in range(13, -1, -1)]
    short_labels = [d[5:] for d in day_labels]   # MM-DD

    type_by_day: dict[str, list[int]] = defaultdict(lambda: [0] * 14)
    for m in recent_meals:
        if m["meal_date"] in day_labels:
            idx = day_labels.index(m["meal_date"])
            type_by_day[m.get("meal_type", "אחר")][idx] += 1

    COLORS = ["#4CAF50", "#2196F3", "#FF9800", "#E91E63", "#9C27B0", "#00BCD4"]
    fig2 = go.Figure()
    for i, (mtype, vals) in enumerate(type_by_day.items()):
        fig2.add_trace(go.Bar(
            x=short_labels, y=vals,
            name=mtype,
            marker_color=COLORS[i % len(COLORS)],
            hoverinfo="skip",
        ))

    fig2.update_layout(**BASE_LAYOUT)
    fig2.update_layout(
        height=300,
        margin=dict(l=50, r=50, t=15, b=90),   # extra bottom for legend
        showlegend=True,
        legend=dict(orientation="h", x=0.5, y=-0.35, xanchor="center", font=dict(size=12)),
        barmode="stack",
    )
    fig2.update_yaxes(tickformat="d")
    st.plotly_chart(fig2, use_container_width=True, config=PLOTLY_CONFIG)
    st.caption(f"סה״כ {len(recent_meals)} ארוחות ב-14 הימים האחרונים")

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
        BLOOD_COLORS = ["#E53935", "#8E24AA", "#1E88E5", "#43A047",
                        "#FB8C00", "#00ACC1", "#F4511E", "#6D4C41"]

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

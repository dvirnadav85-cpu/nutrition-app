import config
from datetime import date, timedelta
from collections import Counter
import streamlit as st
import supabase_client as db

st.set_page_config(page_title="גרפים", page_icon="📊", layout="centered")

st.markdown("""
    <style>* { direction: rtl; text-align: right; }</style>
""", unsafe_allow_html=True)

if not st.session_state.get("authenticated"):
    st.warning("אנא התחברי מהדף הראשי תחילה.")
    st.stop()

st.title("📊 גרפים ומגמות")

# --- Weight chart ---
st.markdown("### ⚖️ מגמת משקל")

weight_rows = db.select("weight_log", order="log_date.asc")

if len(weight_rows) < 2:
    st.info("יש לרשום לפחות שתי שקילות כדי לראות גרף. שלחי את משקלך בשיחה!")
elif weight_rows:
    dates = [r["log_date"] for r in weight_rows]
    weights = [float(r["weight_kg"]) for r in weight_rows]

    first_w, last_w = weights[0], weights[-1]
    delta = last_w - first_w
    delta_str = f"{'↓' if delta < 0 else '↑'} {abs(delta):.1f} ק״ג מאז ההתחלה"

    col1, col2 = st.columns(2)
    col1.metric("משקל נוכחי", f"{last_w} ק״ג", delta_str)
    col2.metric("מדידות", len(weight_rows))

    st.line_chart({"משקל (ק״ג)": weights}, x_label="מדידה", y_label="ק״ג")

st.divider()

# --- Meals per day ---
st.markdown("### 🍽️ ארוחות ב-14 הימים האחרונים")

from_date = (date.today() - timedelta(days=13)).isoformat()
all_meals = db.select("meal_log", order="meal_date.asc")
recent_meals = [m for m in all_meals if m.get("meal_date", "") >= from_date]

if not recent_meals:
    st.info("טרם נרשמו ארוחות. ספרי לעוזרת מה אכלת בשיחה!")
else:
    # Build last 14 days with counts
    day_labels = [(date.today() - timedelta(days=i)).isoformat() for i in range(13, -1, -1)]
    counts = Counter(m["meal_date"] for m in recent_meals)
    meal_counts = [counts.get(d, 0) for d in day_labels]
    short_labels = [d[5:] for d in day_labels]  # MM-DD format

    st.bar_chart({"ארוחות": meal_counts}, x_label="תאריך", y_label="מספר ארוחות")
    st.caption(f"סה״כ {len(recent_meals)} ארוחות ב-14 הימים האחרונים")

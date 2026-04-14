import config
from datetime import date
import streamlit as st
import supabase_client as db

st.set_page_config(page_title="יומן תזונה", page_icon="📋", layout="centered")

st.markdown("""
    <style>* { direction: rtl; text-align: right; }</style>
""", unsafe_allow_html=True)

if not st.session_state.get("authenticated"):
    st.warning("אנא התחברי מהדף הראשי תחילה.")
    st.stop()

if st.button("🏠 בית"): st.switch_page("app.py")
st.title("📋 יומן תזונה")

selected_date = st.date_input("בחרי תאריך", value=date.today(), max_value=date.today())

meals = db.select("meal_log", filters={"meal_date": selected_date.isoformat()}, order="created_at.asc")

if not meals:
    st.info(f"לא נרשמו ארוחות בתאריך {selected_date.strftime('%d/%m/%Y')} 🍽️")
else:
    st.markdown(f"#### ארוחות ב-{selected_date.strftime('%d/%m/%Y')} ({len(meals)} רשומות)")
    for meal in meals:
        time_str = meal["created_at"][11:16] if meal.get("created_at") else ""
        with st.container():
            st.markdown(f"**{meal['meal_type']}** {f'· {time_str}' if time_str else ''}")
            st.markdown(f"📝 {meal['description']}")
            if meal.get("raw_input") and meal["raw_input"] != meal["description"]:
                st.caption(f"מה הקלדת: {meal['raw_input']}")
            st.divider()

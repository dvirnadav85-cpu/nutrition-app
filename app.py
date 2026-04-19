import config
import common
import streamlit as st

st.set_page_config(
    page_title="עוזרת תזונה אישית",
    page_icon="🥗",
    layout="centered",
)

common.page_setup()

st.title("🥗 עוזרת תזונה אישית")
st.markdown("### מה תרצי לעשות?")
st.markdown("---")

if st.button("💬  שיחה עם העוזרת", use_container_width=True):
    st.switch_page("pages/1_💬_שיחה.py")
if st.button("👤  הפרופיל שלי", use_container_width=True):
    st.switch_page("pages/2_👤_פרופיל.py")
if st.button("📋  יומן ארוחות", use_container_width=True):
    st.switch_page("pages/3_📋_יומן.py")
if st.button("📊  גרפים ומגמות", use_container_width=True):
    st.switch_page("pages/4_📊_גרפים.py")
if st.button("🩸  בדיקות דם", use_container_width=True):
    st.switch_page("pages/5_🩸_בדיקות_דם.py")
if st.button("📈  תובנות שבועיות", use_container_width=True):
    st.switch_page("pages/6_📈_תובנות.py")

st.markdown("---")
common.show_nutrition_table()

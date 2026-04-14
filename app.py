import os
import config
import streamlit as st

st.set_page_config(
    page_title="עוזר תזונה אישי",
    page_icon="🥗",
    layout="centered",
)

st.markdown("""
    <style>
        * { direction: rtl; text-align: right; }

        /* Hide sidebar completely */
        section[data-testid="stSidebar"] { display: none !important; }
        [data-testid="collapsedControl"] { display: none !important; }

        /* Full width content */
        .main .block-container {
            padding: 1.5rem 1rem 5rem 1rem !important;
            max-width: 100% !important;
        }

        /* Big nav buttons */
        .stButton > button {
            width: 100%;
            padding: 1rem !important;
            font-size: 1.2rem !important;
            border-radius: 12px !important;
            margin-bottom: 0.5rem;
        }

        /* Hide Streamlit branding */
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
    </style>
""", unsafe_allow_html=True)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🥗 עוזר תזונה אישי")
    st.markdown("### ברוכה הבאה!")

    with st.form("login_form"):
        password = st.text_input("סיסמה", type="password", placeholder="הזיני סיסמה...")
        submitted = st.form_submit_button("כניסה", use_container_width=True)

    if submitted:
        if password == os.getenv("APP_PASSWORD"):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("סיסמה שגויה. נסי שוב.")
else:
    st.title("🥗 עוזר תזונה אישי")
    st.markdown("### לאן תרצי לעבור?")
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

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
    </style>
""", unsafe_allow_html=True)

# --- Password gate ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🥗 עוזר תזונה אישי")
    st.markdown("### ברוכה הבאה! אנא הזיני את הסיסמה כדי להמשיך")

    with st.form("login_form"):
        password = st.text_input("סיסמה", type="password", placeholder="הזיני סיסמה...")
        submitted = st.form_submit_button("כניסה")

    if submitted:
        if password == os.getenv("APP_PASSWORD"):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("סיסמה שגויה. נסי שוב.")
else:
    st.title("🥗 עוזר תזונה אישי")
    st.success("התחברת בהצלחה! השתמשי בתפריט משמאל לניווט.")
    st.markdown("""
    ### מה תרצי לעשות?
    - 💬 **שיחה** — דברי עם העוזרת שלך
    - 👤 **פרופיל** — עדכני את הפרטים שלך
    - 📋 **יומן** — ראי מה אכלת היום
    """)

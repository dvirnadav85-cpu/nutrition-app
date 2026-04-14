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
        /* RTL base */
        * { direction: rtl; text-align: right; }

        /* Move sidebar to the right for RTL */
        section[data-testid="stSidebar"] {
            right: 0;
            left: auto;
        }

        /* Mobile: make content full width and improve spacing */
        @media (max-width: 768px) {
            .main .block-container {
                padding: 1rem 1rem 5rem 1rem !important;
                max-width: 100% !important;
            }
            /* Larger tap targets for buttons */
            .stButton > button {
                width: 100%;
                padding: 0.75rem !important;
                font-size: 1.1rem !important;
            }
            /* Bigger text inputs on mobile */
            .stTextInput input, .stTextArea textarea {
                font-size: 1rem !important;
            }
            /* Chat input bigger on mobile */
            .stChatInputContainer {
                padding: 0.5rem !important;
            }
        }

        /* Hide Streamlit branding */
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
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
    st.success("התחברת בהצלחה! השתמשי בתפריט לניווט בין הדפים.")
    st.markdown("""
    ### מה תרצי לעשות?
    - 💬 **שיחה** — דברי עם העוזרת שלך
    - 👤 **פרופיל** — עדכני את הפרטים שלך
    - 📋 **יומן** — ראי מה אכלת היום
    """)

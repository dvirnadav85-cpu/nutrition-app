import streamlit as st

SHARED_CSS = """
<style>
    * { direction: rtl; text-align: right; }

    /* Hide sidebar completely */
    section[data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }

    /* Hide the Streamlit top toolbar (GitHub/Share/edit icons) */
    header[data-testid="stHeader"] { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }

    /* Full width content */
    .main .block-container {
        padding: 1.5rem 1rem 5rem 1rem !important;
        max-width: 100% !important;
    }

    /* Big nav buttons (home page) */
    .stButton > button {
        width: 100%;
        padding: 1rem !important;
        font-size: 1.2rem !important;
        border-radius: 12px !important;
        margin-bottom: 0.5rem;
    }

    /* 🏠 Home button — smaller, pill style, sits top-right */
    [data-testid="stButton"]:first-of-type > button {
        width: auto !important;
        padding: 0.4rem 1.2rem !important;
        font-size: 1rem !important;
        border-radius: 20px !important;
        background-color: #f0f0f0 !important;
        color: #333 !important;
        border: 1px solid #ddd !important;
        margin-bottom: 1rem;
    }

    /* Hide Streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    /* Chat messages RTL */
    .stChatMessage { direction: rtl; }
</style>
"""

def page_setup():
    """Apply shared styles and mark user as authenticated (no password required)."""
    st.markdown(SHARED_CSS, unsafe_allow_html=True)
    st.session_state.authenticated = True

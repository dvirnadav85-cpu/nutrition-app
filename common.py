import streamlit as st

SHARED_CSS = """
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

    /* Chat messages RTL */
    .stChatMessage { direction: rtl; }
</style>
"""

def page_setup():
    """Apply shared styles and mark user as authenticated (no password required)."""
    st.markdown(SHARED_CSS, unsafe_allow_html=True)
    st.session_state.authenticated = True

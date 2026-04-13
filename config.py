"""
Unified config loader — works both locally (.env) and on Streamlit Cloud (st.secrets).
Import this module at the top of any file that needs environment variables.
"""
import os
from dotenv import load_dotenv

# Load from .env file (works locally, silently ignored when file doesn't exist)
load_dotenv()

# On Streamlit Cloud, secrets are in st.secrets — copy them to os.environ
try:
    import streamlit as st
    for k, v in st.secrets.items():
        os.environ.setdefault(k, str(v))
except Exception:
    pass  # Running locally — .env already loaded above

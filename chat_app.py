import os
from dotenv import load_dotenv
import anthropic
import streamlit as st

# Load API key from .env file
load_dotenv()

# Page configuration - must be the first Streamlit command
st.set_page_config(
    page_title="עוזר תזונה אישי",
    page_icon="🥗",
    layout="centered",
)

# RTL and Hebrew font styling
st.markdown("""
    <style>
        * { direction: rtl; text-align: right; }
        .stChatMessage { direction: rtl; }
        .stChatInputContainer { direction: rtl; }
        body { font-family: 'Segoe UI', Arial, sans-serif; }
    </style>
""", unsafe_allow_html=True)

st.title("🥗 עוזר תזונה אישי")
st.caption("שאלי אותי כל שאלה בנושא תזונה ובריאות")

# Initialize the Anthropic client
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# System prompt - defines Claude's personality and role
SYSTEM_PROMPT = """את עוזרת תזונה אישית חמה ומעודדת. את מדברת עברית בלבד.
את עוזרת למשתמשת לעקוב אחר התזונה שלה, מעודדת אותה, ומספקת מידע תזונתי שימושי.
תמיד תהיי חיובית ולא שיפוטית.
כשמדובר בהחלטות רפואיות, תמיד הפני לרופא או דיאטנית מוסמכת.
ענה בצורה קצרה וברורה."""

# Store chat history across re-runs using session_state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display all previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input box at the bottom
if prompt := st.chat_input("כתבי הודעה..."):

    # Add user message to history and display it
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call Claude and display the response
    with st.chat_message("assistant"):
        with st.spinner("חושבת..."):
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=st.session_state.messages,
            )
            reply = response.content[0].text

        st.markdown(reply)

    # Save assistant response to history
    st.session_state.messages.append({"role": "assistant", "content": reply})

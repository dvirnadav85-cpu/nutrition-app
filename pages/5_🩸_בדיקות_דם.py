import os
import re
import json
import base64
from datetime import date
import config
import anthropic
import streamlit as st
from pypdf import PdfReader
import io
import supabase_client as db

st.set_page_config(page_title="בדיקות דם", page_icon="🩸", layout="centered")

st.markdown("""
    <style>* { direction: rtl; text-align: right; }</style>
""", unsafe_allow_html=True)

if not st.session_state.get("authenticated"):
    st.warning("אנא התחברי מהדף הראשי תחילה.")
    st.stop()

if st.button("🏠 בית"): st.switch_page("app.py")
st.title("🩸 בדיקות דם")

claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

EXTRACTION_PROMPT = """קראי את תוצאות בדיקת הדם וענו על שני דברים:

1. כתבי סיכום ידידותי בעברית (3-4 משפטים). היי מעודדת וחיובית. אל תשפטי.
   אם ערך מחוץ לטווח התקין — ציינו בעדינות וציינו שכדאי לדון בזה עם הרופא.

2. חלצי את הערכים המספריים שמצאת. בסוף תגובתך הוסיפי בדיוק:
<!--MARKERS:{"שם_בדיקה": ערך_מספרי, ...}-->

השתמשי בשמות עבריים (גלוקוז, המוגלובין, כולסטרול כללי, טריגליצרידים, HDL, LDL, קריאטינין, TSH וכדומה).
אם לא ניתן לחלץ ערכים מספריים — כתבי <!--MARKERS:{}-->"""

IMAGE_TYPES = ["png", "jpg", "jpeg", "webp", "gif"]
MEDIA_TYPE_MAP = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
}

def parse_markers(text: str) -> tuple[str, dict]:
    match = re.search(r'<!--MARKERS:(\{.*?\})-->', text, re.DOTALL)
    if match:
        try:
            markers = json.loads(match.group(1))
            clean = text[:match.start()].rstrip()
            return clean, markers
        except json.JSONDecodeError:
            pass
    return text, {}

def process_pdf(uploaded_file) -> tuple[str, dict]:
    """Extract text from PDF, send to Claude as text."""
    reader = PdfReader(io.BytesIO(uploaded_file.read()))
    pdf_text = ""
    for page in reader.pages:
        pdf_text += page.extract_text() or ""

    if not pdf_text.strip():
        st.error("לא הצלחתי לחלץ טקסט מה-PDF. נסי להעלות תמונה של הבדיקה במקום.")
        st.stop()

    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": EXTRACTION_PROMPT + "\n\nטקסט הבדיקה:\n" + pdf_text[:8000]}]
    )
    return pdf_text[:5000], parse_markers(response.content[0].text)

def process_image(uploaded_file) -> tuple[str, dict]:
    """Send image directly to Claude vision."""
    ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
    media_type = MEDIA_TYPE_MAP.get(ext, "image/jpeg")
    image_data = base64.standard_b64encode(uploaded_file.read()).decode("utf-8")

    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
                {"type": "text", "text": EXTRACTION_PROMPT}
            ]
        }]
    )
    return "", parse_markers(response.content[0].text)

# --- Upload section ---
st.markdown("### העלאת בדיקת דם חדשה")
st.caption("ניתן להעלות קובץ PDF או תמונה (צילום של הבדיקה)")

uploaded = st.file_uploader(
    "בחרי קובץ",
    type=["pdf"] + IMAGE_TYPES,
    help="PDF, PNG, JPG, JPEG, WEBP"
)
test_date = st.date_input("תאריך הבדיקה", value=date.today(), max_value=date.today())

if uploaded and st.button("📤 עבדי את הבדיקה", type="primary"):
    with st.spinner("קוראת את הבדיקה... זה עשוי לקחת כ-20 שניות"):
        ext = uploaded.name.rsplit(".", 1)[-1].lower()
        if ext == "pdf":
            raw_text, (summary, markers) = process_pdf(uploaded)
        else:
            raw_text, (summary, markers) = process_image(uploaded)

        db.insert("blood_results", {
            "test_date": test_date.isoformat(),
            "source_filename": uploaded.name,
            "raw_text": raw_text,
            "summary": summary,
            "markers": json.dumps(markers, ensure_ascii=False),
        })

    st.success("הבדיקה עובדה ונשמרה! ✅")
    st.markdown("#### סיכום הבדיקה")
    st.markdown(summary)

    if markers:
        st.markdown("#### ערכים שנמצאו")
        cols = st.columns(3)
        for i, (name, val) in enumerate(markers.items()):
            cols[i % 3].metric(name, val)

st.divider()

# --- Past results ---
st.markdown("### בדיקות קודמות")

past = db.select("blood_results", order="test_date.desc")

if not past:
    st.info("טרם הועלו בדיקות.")
else:
    for result in past:
        label = f"{result.get('test_date', '')} — {result.get('source_filename', 'בדיקה')}"
        with st.expander(label):
            st.markdown(result.get("summary", ""))
            markers_raw = result.get("markers")
            if markers_raw:
                try:
                    markers = json.loads(markers_raw) if isinstance(markers_raw, str) else markers_raw
                    if markers:
                        st.markdown("**ערכים:**")
                        cols = st.columns(3)
                        for i, (name, val) in enumerate(markers.items()):
                            cols[i % 3].metric(name, val)
                except Exception:
                    pass

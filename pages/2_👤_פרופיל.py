import config
import streamlit as st
import supabase_client as db

st.set_page_config(page_title="פרופיל", page_icon="👤", layout="centered")

st.markdown("""
    <style>* { direction: rtl; text-align: right; }</style>
""", unsafe_allow_html=True)

if not st.session_state.get("authenticated"):
    st.warning("אנא התחברי מהדף הראשי תחילה.")
    st.stop()

st.title("👤 הפרופיל שלי")

# Load current profile
rows = db.select("profile", filters={"is_current": "true"}, order="created_at.desc", limit=1)
current = rows[0] if rows else {}

st.markdown("#### מלאי את הפרטים שלך — המידע הזה עוזר לעוזרת להכיר אותך טוב יותר")

with st.form("profile_form"):
    name = st.text_input("שם", value=current.get("name", ""))
    birth_year = st.number_input("שנת לידה", min_value=1920, max_value=2010,
                                  value=current.get("birth_year") or 1960, step=1)
    col1, col2 = st.columns(2)
    with col1:
        height = st.number_input("גובה (ס״מ)", min_value=100.0, max_value=220.0,
                                  value=float(current.get("height_cm") or 160.0), step=0.5)
    with col2:
        weight = st.number_input("משקל (ק״ג)", min_value=30.0, max_value=250.0,
                                  value=float(current.get("weight_kg") or 65.0), step=0.5)

    health_goals = st.text_area("מטרות בריאות",
                                 value=current.get("health_goals", ""),
                                 placeholder="לדוגמה: ירידה במשקל, שמירה על רמת סוכר תקינה...")
    medical_conditions = st.text_area("מצבים רפואיים",
                                       value=current.get("medical_conditions", ""),
                                       placeholder="לדוגמה: סכרת סוג 2, יתר לחץ דם...")
    medications = st.text_area("תרופות ותוספים",
                                value=current.get("medications", ""),
                                placeholder="לדוגמה: מטפורמין 500מ״ג, ויטמין D...")
    additional_notes = st.text_area("הערות נוספות",
                                     value=current.get("additional_notes", ""),
                                     placeholder="כל מידע נוסף שחשוב שהעוזרת תדע...")

    submitted = st.form_submit_button("💾 שמירה")

if submitted:
    if current.get("id"):
        db.update("profile", {"is_current": False}, {"id": current["id"]})

    db.insert("profile", {
        "name": name,
        "birth_year": int(birth_year),
        "height_cm": height,
        "weight_kg": weight,
        "health_goals": health_goals,
        "medical_conditions": medical_conditions,
        "medications": medications,
        "additional_notes": additional_notes,
        "is_current": True,
    })

    st.success("הפרופיל נשמר בהצלחה! ✅")
    st.rerun()

import os
import re
import json
import base64
from datetime import date
import config
import common
import anthropic
import streamlit as st
import supabase_client as db

st.set_page_config(page_title="שיחה", page_icon="💬", layout="centered")
common.page_setup()

if st.button("🏠 בית"): st.switch_page("app.py")
st.title("💬 שיחה עם העוזרת")

claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def load_profile_context() -> str:
    rows = db.select("profile", filters={"is_current": "true"}, order="created_at.desc", limit=1)
    if not rows:
        return "אין עדיין פרופיל שמור למשתמשת."
    p = rows[0]
    parts = []
    if p.get("name"):               parts.append(f"שם: {p['name']}")
    if p.get("birth_year"):         parts.append(f"גיל: {date.today().year - p['birth_year']}")
    if p.get("height_cm"):          parts.append(f"גובה: {p['height_cm']} ס״מ")
    if p.get("weight_kg"):          parts.append(f"משקל אחרון בפרופיל: {p['weight_kg']} ק״ג")
    if p.get("health_goals"):       parts.append(f"מטרות בריאות: {p['health_goals']}")
    if p.get("medical_conditions"): parts.append(f"מצבים רפואיים: {p['medical_conditions']}")
    if p.get("medications"):        parts.append(f"תרופות ותוספים: {p['medications']}")
    if p.get("daily_activity"):     parts.append(f"פעילות גופנית: {p['daily_activity']}")
    if p.get("additional_notes"):   parts.append(f"הערות: {p['additional_notes']}")
    return "\n".join(parts)

SYSTEM_PROMPT = """את עוזרת תזונה אישית חמה ומעודדת. את מדברת עברית בלבד.
את עוזרת למשתמשת לעקוב אחר התזונה שלה, מעודדת אותה, ומספקת מידע תזונתי שימושי.
תמיד תהיי חיובית ולא שיפוטית.
כשמדובר בהחלטות רפואיות, תמיד הפני לרופא או דיאטנית מוסמכת.

פרטי המשתמשת:
{profile}

---
**רישום ארוחות:**
כאשר המשתמשת מספרת שאכלה משהו (בטקסט או בתמונה), תגיבי בחום ובסוף הוסיפי:
<!--MEAL:{{"type":"סוג הארוחה","description":"תיאור קצר"}}-->
סוגים: ארוחת בוקר, ארוחת צהריים, ארוחת ערב, חטיף, שתייה

**רישום משקל:**
כאשר המשתמשת מציינת את משקלה, תגיבי בחום ובסוף הוסיפי:
<!--WEIGHT:{{"kg": 68.0}}-->

**עדכון פעילות גופנית:**
כאשר המשתמשת מתארת את הפעילות הגופנית הקבועה שלה (כמה פעמים בשבוע, סוג פעילות), תגיבי בחום ובסוף הוסיפי:
<!--ACTIVITY:{{"description":"תיאור קצר של הפעילות הקבועה"}}-->

אל תכתבי תגיות אם לא צוין מידע רלוונטי."""

def parse_tags(text: str) -> tuple[str, dict | None, dict | None, dict | None]:
    meal_data = None
    weight_data = None
    activity_data = None

    meal_match = re.search(r'<!--MEAL:(\{.*?\})-->', text, re.DOTALL)
    if meal_match:
        try:
            meal_data = json.loads(meal_match.group(1))
            text = text[:meal_match.start()].rstrip() + text[meal_match.end():]
        except json.JSONDecodeError:
            pass

    weight_match = re.search(r'<!--WEIGHT:(\{.*?\})-->', text, re.DOTALL)
    if weight_match:
        try:
            weight_data = json.loads(weight_match.group(1))
            text = text[:weight_match.start()].rstrip() + text[weight_match.end():]
        except json.JSONDecodeError:
            pass

    activity_match = re.search(r'<!--ACTIVITY:(\{.*?\})-->', text, re.DOTALL)
    if activity_match:
        try:
            activity_data = json.loads(activity_match.group(1))
            text = text[:activity_match.start()].rstrip() + text[activity_match.end():]
        except json.JSONDecodeError:
            pass

    return text.strip(), meal_data, weight_data, activity_data

def save_meal(raw_input: str, meal_type: str, description: str):
    db.insert("meal_log", {
        "meal_date": date.today().isoformat(),
        "meal_type": meal_type,
        "description": description,
        "raw_input": raw_input,
    })

def save_weight(kg: float):
    db.insert("weight_log", {
        "log_date": date.today().isoformat(),
        "weight_kg": kg,
    })

def update_activity(description: str):
    """Update daily_activity on the current profile row (in-place, no versioning needed)."""
    rows = db.select("profile", filters={"is_current": "true"}, order="created_at.desc", limit=1)
    if rows:
        db.update("profile", {"daily_activity": description}, {"id": rows[0]["id"]})
        st.session_state.cached_profile = None   # invalidate cache so next message picks it up

def get_system(force_reload: bool = False) -> str:
    """Return system prompt, using session-cached profile to avoid repeated DB calls."""
    if force_reload or not st.session_state.get("cached_profile"):
        st.session_state.cached_profile = load_profile_context()
    return SYSTEM_PROMPT.format(profile=st.session_state.cached_profile)

def cached_system_param(system: str) -> list:
    """Wrap system prompt for Anthropic prompt caching (cache_control=ephemeral).
    On repeated calls within 5 min, Anthropic charges only ~10% for the cached part."""
    return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]

def analyze_photo(image_bytes: bytes, media_type: str = "image/jpeg") -> str:
    """Send a meal photo to Claude and get back a response with MEAL tag."""
    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")
    system = get_system()

    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=cached_system_param(system),
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
                {"type": "text", "text": "מה רואים בצלחת? תארי את האוכל ורשמי אותו כארוחה."}
            ]
        }]
    )
    return response.content[0].text

MAX_HISTORY = 10   # messages sent to Claude (older ones stay visible but not re-sent)

# Chat history + cached profile (reload from DB only when session starts)
if "messages" not in st.session_state:
    st.session_state.messages = []
if "cached_profile" not in st.session_state:
    st.session_state.cached_profile = None

# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message.get("is_image"):
            st.image(message["image_bytes"], width=200)
        st.markdown(message["content"])

# --- Photo input ---
with st.expander("📷 צלמי או העלי תמונה של הארוחה"):
    photo = st.camera_input("צלמי עכשיו")
    uploaded_photo = st.file_uploader("או העלי תמונה מהגלריה", type=["jpg", "jpeg", "png", "webp"])
    active_photo = photo or uploaded_photo

if active_photo and not st.session_state.get("_last_photo") == active_photo.name + str(active_photo.size):
    st.session_state["_last_photo"] = active_photo.name + str(active_photo.size)
    image_bytes = active_photo.getvalue()

    st.session_state.messages.append({
        "role": "user",
        "content": "📷 [תמונת ארוחה]",
        "is_image": True,
        "image_bytes": image_bytes,
    })

    with st.chat_message("user"):
        st.image(image_bytes, width=200)
        st.markdown("📷 [תמונת ארוחה]")

    with st.chat_message("assistant"):
        with st.spinner("מזהה את האוכל בתמונה..."):
            raw_reply = analyze_photo(image_bytes)

        clean_reply, meal_data, weight_data, activity_data = parse_tags(raw_reply)

        if meal_data:
            save_meal(
                raw_input="[תמונה]",
                meal_type=meal_data.get("type", "ארוחה"),
                description=meal_data.get("description", ""),
            )
            clean_reply += "\n\n*✅ הארוחה נרשמה ביומן*"

        st.markdown(clean_reply)

    st.session_state.messages.append({"role": "assistant", "content": clean_reply})

# --- Text chat input ---
if prompt := st.chat_input("כתבי הודעה..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("חושבת..."):
            system = get_system()
            # send only the last MAX_HISTORY text messages to save tokens
            text_messages = [m for m in st.session_state.messages if not m.get("is_image")]
            recent = text_messages[-MAX_HISTORY:]

            response = claude.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=cached_system_param(system),
                messages=recent,
            )
            raw_reply = response.content[0].text

        clean_reply, meal_data, weight_data, activity_data = parse_tags(raw_reply)

        if meal_data:
            save_meal(
                raw_input=prompt,
                meal_type=meal_data.get("type", "ארוחה"),
                description=meal_data.get("description", ""),
            )
            clean_reply += "\n\n*✅ הארוחה נרשמה ביומן*"

        if weight_data:
            save_weight(float(weight_data.get("kg", 0)))
            clean_reply += f"\n\n*✅ המשקל נרשם: {weight_data.get('kg')} ק״ג*"

        if activity_data:
            update_activity(activity_data.get("description", ""))
            clean_reply += f"\n\n*✅ הפעילות הגופנית עודכנה בפרופיל*"

        st.markdown(clean_reply)

    st.session_state.messages.append({"role": "assistant", "content": clean_reply})

import os
import re
import json
import base64
from datetime import date, timedelta
from collections import defaultdict
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

# ── Profile ────────────────────────────────────────────────────────────────────
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

# ── App data context (meals, weight, blood) ────────────────────────────────────
def load_data_context() -> str:
    parts = []
    today = date.today()
    week_ago = (today - timedelta(days=6)).isoformat()

    # Meals: last 7 days grouped by date
    all_meals = db.select("meal_log", order="meal_date.asc")
    recent_meals = [m for m in all_meals if m.get("meal_date", "") >= week_ago]
    if recent_meals:
        by_day: dict[str, list[str]] = defaultdict(list)
        for m in recent_meals:
            by_day[m["meal_date"]].append(f"{m.get('meal_type','')} — {m.get('description','')}")
        lines = ["ארוחות 7 ימים אחרונים:"]
        for d_str in sorted(by_day):
            lines.append(f"  {d_str}: {'; '.join(by_day[d_str])}")
        parts.append("\n".join(lines))
    else:
        parts.append("לא נרשמו ארוחות ב-7 ימים האחרונים.")

    # Weight: last 5 readings
    weights = db.select("weight_log", order="log_date.desc", limit=5)
    if weights:
        w_lines = ["מדידות משקל אחרונות:"]
        for w in reversed(weights):
            w_lines.append(f"  {w.get('log_date','')}: {w.get('weight_kg','')} ק״ג")
        parts.append("\n".join(w_lines))

    # Blood: latest result markers (up to 10 markers)
    blood_rows = db.select("blood_results", order="test_date.desc", limit=1)
    if blood_rows:
        b = blood_rows[0]
        markers_raw = b.get("markers")
        if markers_raw:
            try:
                markers = json.loads(markers_raw) if isinstance(markers_raw, str) else markers_raw
                b_lines = [f"בדיקת דם אחרונה ({b.get('test_date','')}):"]
                for name, val in list(markers.items())[:10]:
                    b_lines.append(f"  {name}: {val}")
                parts.append("\n".join(b_lines))
            except Exception:
                pass

    return "\n\n".join(parts)

# ── Session summaries ──────────────────────────────────────────────────────────
def load_summaries_context() -> str:
    rows = db.select("session_summaries", order="summary_date.desc", limit=14)
    if not rows:
        return ""
    lines = ["\n\nסיכומי שיחות קודמות (14 ימים אחרונים):"]
    for r in reversed(rows):
        lines.append(f"\n[{r.get('summary_date','')}]\n{r.get('summary','')}")
    return "\n".join(lines)

# ── System prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """את עוזרת תזונה אישית חמה ומעודדת של מירה. את מדברת עברית בלבד.
את עוזרת למירה לעקוב אחר התזונה שלה ומספקת מידע תזונתי שימושי על בסיס הנתונים שיש לך.
תהיי תמיד חיובית, לא שיפוטית, וענייה — ענני על שאלות לפי הנתונים הזמינים.
הוסיפי הפניה לרופאה רק כאשר מדובר בתסמין חדש, שינוי פתאומי, או החלטה טיפולית ממשית — לא בכל תגובה.

פרטי המשתמשת:
{profile}

נתונים מהאפליקציה:
{data_context}{summaries}

---
**רישום ארוחות:**
כאשר מירה מספרת שאכלה משהו (בטקסט או בתמונה), תגיבי בחום ובסוף הוסיפי:
<!--MEAL:{{"type":"סוג הארוחה","description":"תיאור קצר"}}-->
סוגים: ארוחת בוקר, ארוחת צהריים, ארוחת ערב, חטיף, שתייה

**רישום משקל:**
כאשר מירה מציינת את משקלה, תגיבי בחום ובסוף הוסיפי:
<!--WEIGHT:{{"kg": 68.0}}-->

**עדכון פעילות גופנית:**
כאשר מירה מתארת את הפעילות הגופנית הקבועה שלה, תגיבי בחום ובסוף הוסיפי:
<!--ACTIVITY:{{"description":"תיאור קצר של הפעילות הקבועה"}}-->

**עדכון תרופות ותוספים:**
כאשר מירה מזכירה תרופה, תוסף, או ויטמין שהיא נוטלת באופן קבוע, תגיבי בחום ובסוף הוסיפי:
<!--MEDICATION:{{"medications":"רשימת התרופות והתוספים"}}-->

אל תכתבי תגיות אם לא צוין מידע רלוונטי."""

def get_system(force_reload: bool = False) -> str:
    """Return system prompt with profile + app data + summaries, using session cache."""
    if force_reload or not st.session_state.get("cached_profile"):
        st.session_state.cached_profile = load_profile_context()
    if force_reload or not st.session_state.get("cached_data_context"):
        st.session_state.cached_data_context = load_data_context()
    if force_reload or not st.session_state.get("cached_summaries"):
        st.session_state.cached_summaries = load_summaries_context()
    return SYSTEM_PROMPT.format(
        profile=st.session_state.cached_profile,
        data_context=st.session_state.cached_data_context,
        summaries=st.session_state.cached_summaries,
    )

def cached_system_param(system: str) -> list:
    """Wrap system prompt for Anthropic prompt caching."""
    return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]

# ── Tag parsing ────────────────────────────────────────────────────────────────
def parse_tags(text: str) -> tuple[str, dict | None, dict | None, dict | None, dict | None]:
    meal_data = weight_data = activity_data = medication_data = None
    for tag, store in [
        (r'<!--MEAL:(\{.*?\})-->',       'meal'),
        (r'<!--WEIGHT:(\{.*?\})-->',     'weight'),
        (r'<!--ACTIVITY:(\{.*?\})-->',   'activity'),
        (r'<!--MEDICATION:(\{.*?\})-->', 'medication'),
    ]:
        m = re.search(tag, text, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(1))
                text = text[:m.start()].rstrip() + text[m.end():]
                if store == 'meal':       meal_data       = parsed
                elif store == 'weight':   weight_data     = parsed
                elif store == 'activity': activity_data   = parsed
                else:                     medication_data = parsed
            except json.JSONDecodeError:
                pass
    return text.strip(), meal_data, weight_data, activity_data, medication_data

# ── DB helpers ─────────────────────────────────────────────────────────────────
def save_meal(raw_input: str, meal_type: str, description: str):
    db.insert("meal_log", {
        "meal_date": date.today().isoformat(),
        "meal_type": meal_type,
        "description": description,
        "raw_input": raw_input,
    })

def show_daily_summary():
    today = date.today().isoformat()
    meals = db.select("meal_log", filters={"meal_date": today}, order="created_at.asc")
    if not meals:
        return
    st.markdown("**📋 סיכום ארוחות היום:**")
    rows = []
    for m in meals:
        time_str = m.get("created_at", "")
        time_str = time_str[11:16] if len(time_str) > 15 else ""
        rows.append({"סוג": m.get("meal_type",""), "תיאור": m.get("description",""), "שעה": time_str})
    st.table(rows)

def save_weight(kg: float):
    db.insert("weight_log", {
        "log_date": date.today().isoformat(),
        "weight_kg": kg,
    })

def update_activity(description: str):
    rows = db.select("profile", filters={"is_current": "true"}, order="created_at.desc", limit=1)
    if rows:
        db.update("profile", {"daily_activity": description}, {"id": rows[0]["id"]})
        st.session_state.cached_profile = None

def update_medications(medications: str):
    rows = db.select("profile", filters={"is_current": "true"}, order="created_at.desc", limit=1)
    if rows:
        db.update("profile", {"medications": medications}, {"id": rows[0]["id"]})
        st.session_state.cached_profile = None

# ── Chat message persistence ───────────────────────────────────────────────────
def save_chat_message(role: str, content: str):
    """Persist a single chat message to Supabase."""
    try:
        db.insert("chat_messages", {
            "message_date": date.today().isoformat(),
            "role": role,
            "content": content,
        })
    except Exception:
        pass  # Don't crash if DB insert fails

SUMMARIZE_PROMPT = """סכמי את השיחה הבאה ב-100 מילים בעברית.
התמקדי בנקודות בריאותיות חשובות: מה אכלה מירה, משקל שציינה, תרופות, תוספים, תסמינים, רגשות לגבי אוכל, ושאלות שעלו.
כתבי בגוף שלישי ("מירה אכלה...").

שיחה:
{messages}"""

def _summarize_day(target_date: str):
    """Generate and store a summary for a given date's chat messages."""
    msgs = db.select("chat_messages", filters={"message_date": target_date}, order="created_at.asc")
    if not msgs:
        return
    conversation = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in msgs)
    try:
        response = claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content": SUMMARIZE_PROMPT.format(messages=conversation)}]
        )
        db.insert("session_summaries", {
            "summary_date": target_date,
            "summary": response.content[0].text,
        })
    except Exception:
        pass  # Don't crash the app if summarization fails

def _init_session():
    """Called once per session: restore today's messages + lazy-summarize past days."""
    if st.session_state.get("session_initialized"):
        return

    today_str = date.today().isoformat()

    # Restore today's messages so mom can scroll up after a page refresh
    try:
        today_msgs = db.select("chat_messages", filters={"message_date": today_str}, order="created_at.asc")
        st.session_state.messages = [{"role": m["role"], "content": m["content"]} for m in today_msgs]
    except Exception:
        st.session_state.messages = []

    # Find past dates with messages but no summary → generate lazily
    try:
        all_msg_rows = db.select("chat_messages", order="message_date.asc")
        past_dates = {m["message_date"] for m in all_msg_rows if m["message_date"] < today_str}
        existing = {r["summary_date"] for r in db.select("session_summaries")}
        missing = past_dates - existing
        for d_str in sorted(missing):
            _summarize_day(d_str)
        if missing:
            # New summaries were generated — invalidate cache so they're included
            st.session_state.cached_summaries = None
    except Exception:
        pass

    st.session_state.session_initialized = True

# ── Photo analysis ─────────────────────────────────────────────────────────────
def analyze_photo(image_bytes: bytes, media_type: str = "image/jpeg") -> str:
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

MAX_HISTORY = 10

# ── Session state init ─────────────────────────────────────────────────────────
if "cached_profile" not in st.session_state:
    st.session_state.cached_profile = None
if "cached_data_context" not in st.session_state:
    st.session_state.cached_data_context = None
if "cached_summaries" not in st.session_state:
    st.session_state.cached_summaries = None
if "messages" not in st.session_state:
    st.session_state.messages = []

_init_session()

# ── Display previous messages ──────────────────────────────────────────────────
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message.get("is_image"):
            st.image(message["image_bytes"], width=200)
        st.markdown(message["content"])

# ── Photo input ────────────────────────────────────────────────────────────────
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
    save_chat_message("user", "📷 [תמונת ארוחה]")

    with st.chat_message("user"):
        st.image(image_bytes, width=200)
        st.markdown("📷 [תמונת ארוחה]")

    with st.chat_message("assistant"):
        with st.spinner("מזהה את האוכל בתמונה..."):
            raw_reply = analyze_photo(image_bytes)

        clean_reply, meal_data, weight_data, activity_data, medication_data = parse_tags(raw_reply)

        if meal_data:
            save_meal("[תמונה]", meal_data.get("type", "ארוחה"), meal_data.get("description", ""))
            clean_reply += "\n\n*✅ הארוחה נרשמה ביומן*"
            get_system(force_reload=True)

        st.markdown(clean_reply)
        if meal_data:
            show_daily_summary()

    save_chat_message("assistant", clean_reply)
    st.session_state.messages.append({"role": "assistant", "content": clean_reply})

# ── Text chat input ────────────────────────────────────────────────────────────
if prompt := st.chat_input("כתבי הודעה..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    save_chat_message("user", prompt)

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("חושבת..."):
            system = get_system()
            text_messages = [m for m in st.session_state.messages if not m.get("is_image")]
            recent = [{"role": m["role"], "content": m["content"]} for m in text_messages[-MAX_HISTORY:]]

            response = claude.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=cached_system_param(system),
                messages=recent,
            )
            raw_reply = response.content[0].text

        clean_reply, meal_data, weight_data, activity_data, medication_data = parse_tags(raw_reply)

        if meal_data:
            save_meal(prompt, meal_data.get("type", "ארוחה"), meal_data.get("description", ""))
            clean_reply += "\n\n*✅ הארוחה נרשמה ביומן*"

        if weight_data:
            save_weight(float(weight_data.get("kg", 0)))
            clean_reply += f"\n\n*✅ המשקל נרשם: {weight_data.get('kg')} ק״ג*"

        if activity_data:
            update_activity(activity_data.get("description", ""))
            clean_reply += f"\n\n*✅ הפעילות הגופנית עודכנה בפרופיל*"

        if medication_data:
            update_medications(medication_data.get("medications", ""))
            clean_reply += f"\n\n*✅ התרופות עודכנו בפרופיל*"

        if any([meal_data, weight_data, activity_data, medication_data]):
            get_system(force_reload=True)

        st.markdown(clean_reply)
        if meal_data:
            show_daily_summary()

    save_chat_message("assistant", clean_reply)
    st.session_state.messages.append({"role": "assistant", "content": clean_reply})

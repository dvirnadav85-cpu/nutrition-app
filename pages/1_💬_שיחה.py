import os
import re
import json
import base64
from datetime import date, datetime, timedelta
from collections import defaultdict

try:
    from zoneinfo import ZoneInfo
    _IL_TZ = ZoneInfo("Asia/Jerusalem")
except Exception:
    _IL_TZ = None

import config
import common
import anthropic
import streamlit as st
import supabase_client as db

def _now_il() -> datetime:
    return datetime.now(_IL_TZ) if _IL_TZ else datetime.now()

def _period_label(h: int) -> str:
    if 5 <= h < 11:  return "בוקר"
    if 11 <= h < 15: return "צהריים"
    if 15 <= h < 19: return "אחר הצהריים"
    if 19 <= h < 22: return "ערב"
    return "לילה"

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

    # Blood sugar: last 14 daily readings from chat
    try:
        bs_rows = db.select("blood_sugar_log", order="log_date.desc", limit=14)
    except Exception:
        bs_rows = []
    if bs_rows:
        bs_lines = ["מדידות סוכר בדם אחרונות:"]
        for r in reversed(bs_rows):
            time_str = f" ({r['reading_time']})" if r.get("reading_time") else ""
            bs_lines.append(f"  {r.get('log_date','')}{time_str}: {r.get('value_mgdl','')} mg/dL")
        parts.append("\n".join(bs_lines))

    # Sleep: last 14 nights
    try:
        sleep_rows = db.select("sleep_log", order="log_date.desc", limit=14)
    except Exception:
        sleep_rows = []
    if sleep_rows:
        s_lines = ["שינה (14 לילות אחרונים):"]
        for r in reversed(sleep_rows):
            hrs = r.get("duration_hours")
            q = r.get("quality") or ""
            notes = f" — {r['notes']}" if r.get("notes") else ""
            hrs_str = f"{float(hrs):.1f} שעות" if hrs is not None else "ללא שעות"
            s_lines.append(f"  {r.get('log_date','')}: {hrs_str}, איכות: {q}{notes}")
        parts.append("\n".join(s_lines))

    # Nutrition goals & today's consumed
    goals = common.get_daily_goals()
    if goals:
        consumed = common.get_daily_consumed()
        n_lines = ["יעדים תזונתיים יומיים ומה שנאכל היום:"]
        for k, g in goals.items():
            name, unit = common.NUTRIENT_LABELS.get(k, (k, ""))
            eaten = consumed.get(k, 0)
            unit_str = f" {unit}" if unit else ""
            n_lines.append(f"  {name} ({k}): {eaten:.0f}/{g}{unit_str}")
        parts.append("\n".join(n_lines))
    else:
        parts.append("⚠️ עוד לא הוגדרו יעדים תזונתיים — עזרי למירה להגדיר יעדים מתאימים לפי הפרופיל והמטרות שלה.")

    # Historical monthly aggregates (last 6 months, excluding this week)
    try:
        six_mo_ago = (today - timedelta(days=180)).isoformat()
        older_meals = [m for m in all_meals
                       if six_mo_ago <= m.get("meal_date", "") < week_ago]
    except Exception:
        older_meals = []
    if older_meals and goals:
        # Day → nutrient totals
        day_totals: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for m in older_meals:
            n = m.get("nutrients")
            if isinstance(n, str):
                try: n = json.loads(n)
                except Exception: n = None
            if not isinstance(n, dict):
                continue
            d = m.get("meal_date", "")
            for k, v in n.items():
                try:
                    day_totals[d][k] += float(v)
                except (TypeError, ValueError):
                    pass
        # Month → list of daily totals per nutrient
        month_daily: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        for d, totals in day_totals.items():
            ym = d[:7]
            for k, v in totals.items():
                if k in goals:
                    month_daily[ym][k].append(v)
        if month_daily:
            h_lines = ["ממוצעים חודשיים היסטוריים (ימים שהיו בהם ארוחות מתועדות):"]
            for ym in sorted(month_daily.keys(), reverse=True)[:6]:
                pieces = []
                for k, vals in month_daily[ym].items():
                    avg = sum(vals) / len(vals)
                    name, _ = common.NUTRIENT_LABELS.get(k, (k, ""))
                    pieces.append(f"{name} {avg:.0f}")
                days_with_data = len({d for d in day_totals if d.startswith(ym)})
                h_lines.append(f"  {ym} ({days_with_data} ימים): {', '.join(pieces)}")
            parts.append("\n".join(h_lines))

    # Historical weight range
    try:
        older_weights = db.select("weight_log", order="log_date.asc")
    except Exception:
        older_weights = []
    if len(older_weights) >= 5:
        first_w = older_weights[0]
        last_w = older_weights[-1]
        parts.append(
            f"היסטוריית משקל: מ־{first_w.get('weight_kg')} ק״ג ({first_w.get('log_date')}) "
            f"עד {last_w.get('weight_kg')} ק״ג ({last_w.get('log_date')}), "
            f"סה״כ {len(older_weights)} מדידות."
        )

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

תאריך ושעה: {today} {hhmm} ({period})

פרטי המשתמשת:
{profile}

נתונים מהאפליקציה:
{data_context}{summaries}

---
**כלל תאריך חשוב:**
כל התגיות תומכות בשדה "date" אופציונלי בפורמט YYYY-MM-DD.
אם מירה מתייחסת לאתמול, שלשום, או תאריך ספציפי — חשבי את התאריך הנכון על בסיס תאריך היום והוסיפי אותו לתגית.
אם מדובר בהיום — השמיטי את שדה date לחלוטין.

**רישום ארוחות:**
כאשר מירה מספרת שאכלה משהו (בטקסט או בתמונה), תגיבי בחום ובסוף הוסיפי:
<!--MEAL:{{"type":"סוג הארוחה","description":"תיאור קצר","nutrients":{{"kcal":350,"protein_g":12}}}}-->
אם לא היום: הוסיפי "date":"YYYY-MM-DD" לתגית.
סוגים: ארוחת בוקר, ארוחת צהריים, ארוחת ערב, חטיף, שתייה

**הערכת רכיבים תזונתיים בארוחה (חשוב!):**
- הערכה גסה לפי תיאור האוכל — אל תציגי את המספרים בתגובה לטקסט.
- הערכי **רק** את הרכיבים שיש להם יעד בטבלת היעדים שלמעלה.
- אם אין עוד יעדים — השמיטי את nutrients והציעי למירה להגדיר יעדים יחד איתה.
- השתמשי **אך ורק** במפתחות הקנוניים הבאים (snake_case, יחידה במפתח):
  kcal, protein_g, carbs_g, fat_g, sat_fat_g, fiber_g, sugar_g,
  sodium_mg, calcium_mg, iron_mg, b12_mcg, vitamin_d_iu,
  magnesium_mg, potassium_mg, phosphorus_mg, zinc_mg, cholesterol_mg.
- אם מירה רוצה לעקוב אחר רכיב שאינו ברשימה — הציעי מפתח בסגנון דומה.

**עדכון יעדים תזונתיים:**
<!--GOALS_UPDATE:{{"protein_g":60,"fiber_g":25}}-->
(מיזוג — מעדכן/מוסיף את המפתחות הנתונים, השאר נשארים)

**הסרת רכיב מהמעקב:**
<!--GOALS_REMOVE:["sodium_mg","cholesterol_mg"]-->

**הגדרת יעדים לראשונה / עדכון לפי מטרה:**
כאשר אין יעדים, או כאשר מירה מציינת מטרה חדשה (ירידה במשקל, עלייה במסת שריר, חוסר בברזל/B12, מצב בריאותי חדש) — הציעי יעדים מתאימים לפי גילה, משקלה, פעילותה ומצבה. הסבירי קצרות את ההיגיון, והשתמשי ב-GOALS_UPDATE כדי לשמור. התחילי קטן (3-5 רכיבים חשובים) והרחיבי עם הזמן.

**רישום משקל:**
כאשר מירה מציינת את משקלה, תגיבי בחום ובסוף הוסיפי:
<!--WEIGHT:{{"kg": 68.0}}-->
אם לא היום: <!--WEIGHT:{{"kg": 68.0,"date":"YYYY-MM-DD"}}-->

**עדכון פעילות גופנית:**
כאשר מירה מתארת את הפעילות הגופנית הקבועה שלה, תגיבי בחום ובסוף הוסיפי:
<!--ACTIVITY:{{"description":"תיאור קצר של הפעילות הקבועה"}}-->

**עדכון תרופות ותוספים:**
כאשר מירה מזכירה תרופה, תוסף, או ויטמין שהיא נוטלת באופן קבוע, תגיבי בחום ובסוף הוסיפי:
<!--MEDICATION:{{"medications":"רשימת התרופות והתוספים"}}-->

**רישום סוכר בדם:**
כאשר מירה מציינת ערך סוכר בדם (גלוקוז), תגיבי בחום ובסוף הוסיפי:
<!--BLOOD_SUGAR:{{"value": 95, "reading_time": "בוקר"}}-->
אם לא היום: <!--BLOOD_SUGAR:{{"value": 95, "reading_time": "בוקר","date":"YYYY-MM-DD"}}-->
זמני מדידה אפשריים: בוקר (בצום), אחרי ארוחה, ערב, לפני שינה
אם לא צוין זמן, השמיטי את reading_time.

**רישום שינה:**
כאשר מירה מספרת כמה זמן ישנה או איך ישנה, תגיבי בחום ובסוף הוסיפי:
<!--SLEEP:{{"hours":7.5,"quality":"טוב"}}-->
אם לא הלילה האחרון: <!--SLEEP:{{"hours":7.5,"quality":"טוב","date":"YYYY-MM-DD"}}-->
שדות אופציונליים: hours (מספר), quality (אחת מ: מעולה/טוב/בינוני/גרוע/גרוע מאוד), notes (הערה קצרה).
חשבי את quality מתוך התיאור החופשי שלה.

**שאלה יזומה על שינה:**
בבוקר (5:00-11:00) בתחילת שיחה חדשה, אם לא נרשמה שינה ללילה האחרון, שאלי בעדינות איך ישנה.
אל תשאלי על שינה מחוץ לשעות הבוקר, ואל תשאלי שוב אם מירה כבר דיווחה היום.

אל תכתבי תגיות אם לא צוין מידע רלוונטי."""

def get_system(force_reload: bool = False) -> str:
    """Return system prompt with profile + app data + summaries, using session cache."""
    if force_reload or not st.session_state.get("cached_profile"):
        st.session_state.cached_profile = load_profile_context()
    if force_reload or not st.session_state.get("cached_data_context"):
        st.session_state.cached_data_context = load_data_context()
    if force_reload or not st.session_state.get("cached_summaries"):
        st.session_state.cached_summaries = load_summaries_context()
    now = _now_il()
    return SYSTEM_PROMPT.format(
        today=now.date().isoformat(),
        hhmm=now.strftime("%H:%M"),
        period=_period_label(now.hour),
        profile=st.session_state.cached_profile,
        data_context=st.session_state.cached_data_context,
        summaries=st.session_state.cached_summaries,
    )

def cached_system_param(system: str) -> list:
    """Wrap system prompt for Anthropic prompt caching."""
    return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]

# ── Tag parsing ────────────────────────────────────────────────────────────────
def parse_tags(text: str) -> tuple[str, dict]:
    """Extract all known hidden tags and return (clean_text, {tag_name: parsed_payload})."""
    patterns = {
        "meal":         r'<!--MEAL:(\{.*?\})-->',
        "weight":       r'<!--WEIGHT:(\{.*?\})-->',
        "activity":     r'<!--ACTIVITY:(\{.*?\})-->',
        "medication":   r'<!--MEDICATION:(\{.*?\})-->',
        "blood_sugar":  r'<!--BLOOD_SUGAR:(\{.*?\})-->',
        "sleep":        r'<!--SLEEP:(\{.*?\})-->',
        "goals_update": r'<!--GOALS_UPDATE:(\{.*?\})-->',
        "goals_remove": r'<!--GOALS_REMOVE:(\[.*?\])-->',
    }
    tags: dict = {}
    for name, pattern in patterns.items():
        m = re.search(pattern, text, re.DOTALL)
        if m:
            try:
                tags[name] = json.loads(m.group(1))
                text = text[:m.start()].rstrip() + text[m.end():]
            except json.JSONDecodeError:
                pass
    return text.strip(), tags

# ── DB helpers ─────────────────────────────────────────────────────────────────
def save_meal(raw_input: str, meal_type: str, description: str,
              meal_date: str | None = None, nutrients: dict | None = None):
    row = {
        "meal_date": meal_date or date.today().isoformat(),
        "meal_type": meal_type,
        "description": description,
        "raw_input": raw_input,
    }
    if nutrients:
        row["nutrients"] = nutrients
    db.insert("meal_log", row)

def update_goals(partial: dict):
    """Merge partial goals dict into the current user's daily_goals."""
    current = common.get_daily_goals()
    merged = {**current, **{k: v for k, v in partial.items() if v is not None}}
    rows = db.select("profile", filters={"is_current": "true"},
                     order="created_at.desc", limit=1)
    if rows:
        db.update("profile", {"daily_goals": merged}, {"id": rows[0]["id"]})
        st.session_state.cached_profile = None
        st.session_state.cached_data_context = None

def remove_goals(keys: list):
    """Remove keys from the current user's daily_goals."""
    current = common.get_daily_goals()
    for k in keys:
        current.pop(k, None)
    rows = db.select("profile", filters={"is_current": "true"},
                     order="created_at.desc", limit=1)
    if rows:
        db.update("profile", {"daily_goals": current}, {"id": rows[0]["id"]})
        st.session_state.cached_profile = None
        st.session_state.cached_data_context = None

def save_weight(kg: float, log_date: str | None = None):
    db.insert("weight_log", {
        "log_date": log_date or date.today().isoformat(),
        "weight_kg": kg,
    })

def update_activity(description: str):
    rows = db.select("profile", filters={"is_current": "true"}, order="created_at.desc", limit=1)
    if rows:
        db.update("profile", {"daily_activity": description}, {"id": rows[0]["id"]})
        st.session_state.cached_profile = None

def save_blood_sugar(value: float, reading_time: str | None = None, log_date: str | None = None):
    row = {"log_date": log_date or date.today().isoformat(), "value_mgdl": value}
    if reading_time:
        row["reading_time"] = reading_time
    db.insert("blood_sugar_log", row)

def save_sleep(hours: float | None = None, quality: str | None = None,
               notes: str | None = None, log_date: str | None = None):
    row: dict = {"log_date": log_date or date.today().isoformat()}
    if hours is not None:
        row["duration_hours"] = hours
    if quality:
        row["quality"] = quality
    if notes:
        row["notes"] = notes
    try:
        db.insert("sleep_log", row)
    except Exception:
        pass

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

        clean_reply, tags = parse_tags(raw_reply)

        meal = tags.get("meal")
        if meal:
            md = meal.get("date")
            save_meal("[תמונה]", meal.get("type", "ארוחה"), meal.get("description", ""),
                      md, meal.get("nutrients"))
            clean_reply += f"\n\n*✅ הארוחה נרשמה ביומן{f' ({md})' if md else ''}*"

        bs = tags.get("blood_sugar")
        if bs:
            bsd = bs.get("date")
            save_blood_sugar(float(bs.get("value", 0)), bs.get("reading_time"), bsd)
            clean_reply += f"\n\n*✅ סוכר בדם נרשם: {bs.get('value')} mg/dL{f' ({bsd})' if bsd else ''}*"

        sl = tags.get("sleep")
        if sl:
            sld = sl.get("date")
            hrs = sl.get("hours")
            save_sleep(float(hrs) if hrs is not None else None,
                       sl.get("quality"), sl.get("notes"), sld)
            hrs_label = f"{float(hrs):.1f} שעות" if hrs is not None else "ללא שעות"
            clean_reply += f"\n\n*✅ שינה נרשמה: {hrs_label}, איכות: {sl.get('quality','')}{f' ({sld})' if sld else ''}*"

        if tags.get("goals_update"):
            update_goals(tags["goals_update"])
            clean_reply += "\n\n*✅ היעדים התזונתיים עודכנו*"

        if tags.get("goals_remove"):
            remove_goals(tags["goals_remove"])
            clean_reply += "\n\n*✅ הוסרו רכיבים מהמעקב*"

        if tags:
            get_system(force_reload=True)

        st.markdown(clean_reply)
        if meal:
            common.show_nutrition_table(for_date=meal.get("date"))

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

        clean_reply, tags = parse_tags(raw_reply)

        meal = tags.get("meal")
        if meal:
            md = meal.get("date")
            save_meal(prompt, meal.get("type", "ארוחה"), meal.get("description", ""),
                      md, meal.get("nutrients"))
            clean_reply += f"\n\n*✅ הארוחה נרשמה ביומן{f' ({md})' if md else ''}*"

        weight = tags.get("weight")
        if weight:
            wd = weight.get("date")
            save_weight(float(weight.get("kg", 0)), wd)
            clean_reply += f"\n\n*✅ המשקל נרשם: {weight.get('kg')} ק״ג{f' ({wd})' if wd else ''}*"

        if tags.get("activity"):
            update_activity(tags["activity"].get("description", ""))
            clean_reply += "\n\n*✅ הפעילות הגופנית עודכנה בפרופיל*"

        if tags.get("medication"):
            update_medications(tags["medication"].get("medications", ""))
            clean_reply += "\n\n*✅ התרופות עודכנו בפרופיל*"

        bs = tags.get("blood_sugar")
        if bs:
            bsd = bs.get("date")
            save_blood_sugar(float(bs.get("value", 0)), bs.get("reading_time"), bsd)
            clean_reply += f"\n\n*✅ סוכר בדם נרשם: {bs.get('value')} mg/dL{f' ({bsd})' if bsd else ''}*"

        sl = tags.get("sleep")
        if sl:
            sld = sl.get("date")
            hrs = sl.get("hours")
            save_sleep(float(hrs) if hrs is not None else None,
                       sl.get("quality"), sl.get("notes"), sld)
            hrs_label = f"{float(hrs):.1f} שעות" if hrs is not None else "ללא שעות"
            clean_reply += f"\n\n*✅ שינה נרשמה: {hrs_label}, איכות: {sl.get('quality','')}{f' ({sld})' if sld else ''}*"

        if tags.get("goals_update"):
            update_goals(tags["goals_update"])
            clean_reply += "\n\n*✅ היעדים התזונתיים עודכנו*"

        if tags.get("goals_remove"):
            remove_goals(tags["goals_remove"])
            clean_reply += "\n\n*✅ הוסרו רכיבים מהמעקב*"

        if tags:
            get_system(force_reload=True)

        st.markdown(clean_reply)
        if meal:
            common.show_nutrition_table(for_date=meal.get("date"))

    save_chat_message("assistant", clean_reply)
    st.session_state.messages.append({"role": "assistant", "content": clean_reply})

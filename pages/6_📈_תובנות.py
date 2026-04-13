import os
import config
from datetime import date, timedelta
import anthropic
import streamlit as st
import supabase_client as db

st.set_page_config(page_title="תובנות שבועיות", page_icon="📈", layout="centered")

st.markdown("""
    <style>* { direction: rtl; text-align: right; }</style>
""", unsafe_allow_html=True)

if not st.session_state.get("authenticated"):
    st.warning("אנא התחברי מהדף הראשי תחילה.")
    st.stop()

st.title("📈 תובנות שבועיות")
st.caption("ניתוח מעמיק של השבוע האחרון — תזונה, משקל ומגמות")

claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def build_week_summary() -> str:
    today = date.today()
    week_ago = today - timedelta(days=7)

    # Meals
    all_meals = db.select("meal_log", order="meal_date.asc")
    week_meals = [m for m in all_meals if m.get("meal_date", "") >= week_ago.isoformat()]

    # Weight
    all_weights = db.select("weight_log", order="log_date.asc")
    week_weights = [w for w in all_weights if w.get("log_date", "") >= week_ago.isoformat()]

    # Blood results
    all_blood = db.select("blood_results", order="test_date.desc")
    week_blood = [b for b in all_blood if b.get("test_date", "") >= week_ago.isoformat()]

    # Profile
    profile_rows = db.select("profile", filters={"is_current": "true"}, limit=1)
    profile = profile_rows[0] if profile_rows else {}

    lines = [f"דוח שבועי — {week_ago.strftime('%d/%m/%Y')} עד {today.strftime('%d/%m/%Y')}"]
    lines.append("")

    if profile:
        name = profile.get("name", "המשתמשת")
        lines.append(f"שם: {name}")
        if profile.get("health_goals"):
            lines.append(f"מטרות: {profile['health_goals']}")
        if profile.get("medical_conditions"):
            lines.append(f"מצבים רפואיים: {profile['medical_conditions']}")
        lines.append("")

    lines.append(f"ארוחות שתועדו השבוע: {len(week_meals)}")
    if week_meals:
        from collections import Counter
        by_type = Counter(m.get("meal_type", "לא ידוע") for m in week_meals)
        for meal_type, count in by_type.items():
            lines.append(f"  {meal_type}: {count} פעמים")
        lines.append("פירוט:")
        for m in week_meals:
            lines.append(f"  {m.get('meal_date','')} — {m.get('meal_type','')}: {m.get('description','')}")
    lines.append("")

    if week_weights:
        lines.append(f"מדידות משקל השבוע: {len(week_weights)}")
        for w in week_weights:
            lines.append(f"  {w.get('log_date','')}: {w.get('weight_kg','')} ק\"ג")
    else:
        lines.append("לא נרשמו מדידות משקל השבוע.")
    lines.append("")

    if week_blood:
        lines.append("בדיקות דם השבוע:")
        for b in week_blood:
            lines.append(f"  {b.get('test_date','')}: {b.get('source_filename','')}")
            if b.get("summary"):
                lines.append(f"  סיכום: {b['summary'][:200]}")
    else:
        lines.append("לא הועלו בדיקות דם השבוע.")

    return "\n".join(lines)

INSIGHTS_PROMPT = """את עוזרת תזונה אישית חמה ומנוסה. כתבי דוח שבועי בעברית עבור המשתמשת.

הדוח צריך לכלול:
1. פתיחה חמה ומעודדת
2. סיכום דפוסי האכילה השבוע (מה אכלה, כמה ארוחות, מגוון)
3. מגמת משקל אם יש נתונים
4. 2-3 תצפיות עדינות על קשרים בנתונים (אם קיימים) — לדוגמה: "ביום שבו...")
5. המלצה אחת קטנה לשבוע הבא
6. סיום מעודד

חשוב מאוד:
- תמיד חיובית ולא שיפוטית
- סיימי תמיד במשפט: "אלו תצפיות בלבד — כדאי לדון בהן עם הרופאה או הדיאטנית שלך 🩺"
- אל תתני המלצות רפואיות

נתוני השבוע:
{data}"""

# --- Generate report button ---
week_start = date.today() - timedelta(days=7)
week_end = date.today()

if st.button("✨ צרי דוח שבועי", type="primary"):
    with st.spinner("מנתחת את השבוע... זה עשוי לקחת כחצי דקה"):
        week_data = build_week_summary()

        response = claude.messages.create(
            model="claude-opus-4-6",
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": INSIGHTS_PROMPT.format(data=week_data)
            }]
        )
        report = response.content[0].text

        db.insert("weekly_reports", {
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "report": report,
        })

    st.markdown("---")
    st.markdown(report)

st.divider()

# --- Past reports ---
st.markdown("### דוחות קודמים")
past = db.select("weekly_reports", order="created_at.desc")

if not past:
    st.info("טרם נוצרו דוחות שבועיים.")
else:
    for r in past:
        label = f"שבוע {r.get('week_start','')} עד {r.get('week_end','')}"
        with st.expander(label):
            st.markdown(r.get("report", ""))

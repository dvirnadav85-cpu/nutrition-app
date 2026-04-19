import json
from datetime import date
from collections import defaultdict
import streamlit as st
import supabase_client as db

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

# ── Nutrition tracking ─────────────────────────────────────────────────────────
# Canonical nutrient keys → (Hebrew display name, unit). Unknown keys fall back
# to the raw key with no unit.
NUTRIENT_LABELS: dict[str, tuple[str, str]] = {
    "kcal":           ("קלוריות",      "קק״ל"),
    "protein_g":      ("חלבון",        "ג׳"),
    "carbs_g":        ("פחמימות",      "ג׳"),
    "fat_g":          ("שומן כולל",    "ג׳"),
    "sat_fat_g":      ("שומן רווי",    "ג׳"),
    "fiber_g":        ("סיבים",        "ג׳"),
    "sugar_g":        ("סוכר",         "ג׳"),
    "sodium_mg":      ("נתרן",         "מ״ג"),
    "calcium_mg":     ("סידן",         "מ״ג"),
    "iron_mg":        ("ברזל",         "מ״ג"),
    "b12_mcg":        ("ויטמין B12",   "מק״ג"),
    "vitamin_d_iu":   ("ויטמין D",     "יח׳"),
    "magnesium_mg":   ("מגנזיום",      "מ״ג"),
    "potassium_mg":   ("אשלגן",        "מ״ג"),
    "phosphorus_mg":  ("זרחן",         "מ״ג"),
    "zinc_mg":        ("אבץ",          "מ״ג"),
    "cholesterol_mg": ("כולסטרול",     "מ״ג"),
}

def _as_dict(value) -> dict:
    """JSONB columns may come back as dict or string depending on the row."""
    if not value:
        return {}
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return {}
    return value if isinstance(value, dict) else {}

def get_daily_goals() -> dict:
    """Return the current user's daily nutrition goals (key → numeric target)."""
    try:
        rows = db.select("profile", filters={"is_current": "true"},
                         order="created_at.desc", limit=1)
    except Exception:
        return {}
    if not rows:
        return {}
    return _as_dict(rows[0].get("daily_goals"))

def get_daily_consumed(for_date: str | None = None) -> dict:
    """Aggregate nutrients across all meals on a given date."""
    target = for_date or date.today().isoformat()
    try:
        meals = db.select("meal_log", filters={"meal_date": target})
    except Exception:
        return {}
    totals: dict[str, float] = defaultdict(float)
    for m in meals:
        nutrients = _as_dict(m.get("nutrients"))
        for k, v in nutrients.items():
            try:
                totals[k] += float(v)
            except (TypeError, ValueError):
                pass
    return dict(totals)

def show_nutrition_table(for_date: str | None = None):
    """Render today's (or a given day's) nutrition goals vs consumed as a table."""
    goals = get_daily_goals()
    if not goals:
        st.info("💚 עוד לא הוגדרו יעדים תזונתיים. פתחי את השיחה והעוזרת תעזור לך להגדיר יעדים מתאימים לפי הפרופיל שלך.")
        return

    target = for_date or date.today().isoformat()
    consumed = get_daily_consumed(target)
    label = "היום" if target == date.today().isoformat() else target

    st.markdown(f"**📋 תזונה {label}:**")
    rows = []
    for k, goal in goals.items():
        try:
            goal_num = float(goal)
        except (TypeError, ValueError):
            continue
        name, unit = NUTRIENT_LABELS.get(k, (k, ""))
        eaten = consumed.get(k, 0.0)
        pct = int(100 * eaten / goal_num) if goal_num > 0 else 0
        filled = min(10, max(0, pct // 10))
        bar = "█" * filled + "░" * (10 - filled)
        unit_suffix = f" {unit}" if unit else ""
        rows.append({
            "רכיב": name,
            "אכלה": f"{eaten:.0f}{unit_suffix}",
            "יעד": f"{goal_num:.0f}{unit_suffix}",
            "%": f"{pct}%",
            "התקדמות": bar,
        })
    if rows:
        st.table(rows)
    else:
        st.info("היעדים שהוגדרו אינם תקינים. נסי לעדכן בשיחה.")

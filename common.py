from __future__ import annotations

import json
from datetime import date, datetime
from collections import defaultdict
import streamlit as st
import supabase_client as db

try:
    from zoneinfo import ZoneInfo
    _IL_TZ = ZoneInfo("Asia/Jerusalem")
except Exception:
    _IL_TZ = None

_HEBREW_WEEKDAYS = {
    6: "ראשון", 0: "שני", 1: "שלישי", 2: "רביעי",
    3: "חמישי", 4: "שישי", 5: "שבת",
}

_GREETING_BY_PERIOD = {
    "בוקר": "בוקר טוב",
    "צהריים": "צהריים טובים",
    "אחר הצהריים": "אחר צהריים נעים",
    "ערב": "ערב טוב",
    "לילה": "לילה טוב",
}

def now_il() -> datetime:
    """Current datetime in Israel timezone (falls back to local if zoneinfo missing)."""
    return datetime.now(_IL_TZ) if _IL_TZ else datetime.now()

def period_label(h: int) -> str:
    """Map an hour (0-23) to a Hebrew time-of-day period."""
    if 5 <= h < 11:  return "בוקר"
    if 11 <= h < 15: return "צהריים"
    if 15 <= h < 19: return "אחר הצהריים"
    if 19 <= h < 22: return "ערב"
    return "לילה"

def greeting_now() -> str:
    """Hebrew greeting matching the current Israel hour."""
    return _GREETING_BY_PERIOD[period_label(now_il().hour)]

def hebrew_date_label(dt: datetime | None = None) -> str:
    """e.g. 'יום שני · 27.04' for today in Israel time."""
    dt = dt or now_il()
    weekday = _HEBREW_WEEKDAYS[dt.weekday()]
    return f"יום {weekday} · {dt.day:02d}.{dt.month:02d}"

SHARED_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Frank+Ruhl+Libre:wght@500;700;900&family=Assistant:wght@300;400;500;600;700&display=swap');

    :root {
        --bg-cream: #F5F1E8;
        --bg-cream-deep: #EFE9DB;
        --card-bg: #FFFFFF;
        --sage-deep: #4F6B52;
        --sage: #6B8E6F;
        --sage-soft: #A8C0A0;
        --sage-tint: #E4ECDD;
        --sage-tint-warm: #EDF2E5;

        --text-dark: #2A3829;
        --text-medium: #4A5C4B;
        --text-muted: #7A8A7C;

        --tint-sage:  #E4ECDD;
        --tint-clay:  #F0DFD0;
        --tint-peach: #F8E2CE;
        --tint-honey: #F2E5C2;
        --tint-coral: #F4D7CE;
        --tint-mauve: #E8DDE2;

        --ic-sage:  #5C7E60;
        --ic-clay:  #B4805E;
        --ic-peach: #C97D4F;
        --ic-honey: #B8923A;
        --ic-coral: #C36A55;
        --ic-mauve: #8E6E7F;

        --shadow-sm: 0 1px 2px rgba(74, 92, 75, 0.04), 0 1px 3px rgba(74, 92, 75, 0.06);
        --shadow-md: 0 4px 12px rgba(74, 92, 75, 0.08), 0 2px 4px rgba(74, 92, 75, 0.04);
        --shadow-lg: 0 12px 28px rgba(74, 92, 75, 0.10), 0 4px 8px rgba(74, 92, 75, 0.04);
    }

    * { direction: rtl; text-align: right; -webkit-tap-highlight-color: transparent; }

    /* Global typography + cream background */
    html, body, [class*="st-"], .stApp, .stMarkdown, button, input, textarea, select {
        font-family: 'Assistant', -apple-system, sans-serif;
    }

    .stApp {
        background:
            radial-gradient(ellipse 90% 60% at 100% 0%, rgba(168, 192, 160, 0.18), transparent 60%),
            radial-gradient(ellipse 80% 50% at 0% 12%, rgba(180, 128, 94, 0.08), transparent 55%),
            linear-gradient(180deg, var(--bg-cream) 0%, var(--bg-cream-deep) 100%);
        background-attachment: fixed;
        color: var(--text-dark);
        -webkit-font-smoothing: antialiased;
    }

    h1, h2, h3, h4,
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
        font-family: 'Frank Ruhl Libre', serif !important;
        font-weight: 700;
        color: var(--text-dark);
        letter-spacing: -0.3px;
    }
    h1, .stMarkdown h1 { color: var(--sage-deep); }

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

    /* General buttons — sage-tinted, soft */
    .stButton > button {
        width: 100%;
        padding: 0.85rem 1rem !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        border-radius: 16px !important;
        margin-bottom: 0.5rem;
        background: var(--card-bg) !important;
        color: var(--text-dark) !important;
        border: 1px solid rgba(107, 142, 111, 0.18) !important;
        box-shadow: var(--shadow-sm);
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        border-color: var(--sage) !important;
        box-shadow: var(--shadow-md);
    }
    .stButton > button:active { transform: translateY(0); }

    /* 🏠 Home button — pill, sage-tinted, sits top-right (RTL) */
    [data-testid="stButton"]:first-of-type > button {
        width: auto !important;
        padding: 0.4rem 1.1rem !important;
        font-size: 0.95rem !important;
        font-weight: 500 !important;
        border-radius: 999px !important;
        background: var(--tint-sage) !important;
        color: var(--sage-deep) !important;
        border: 1px solid rgba(92, 126, 96, 0.25) !important;
        box-shadow: none;
        margin-bottom: 1rem;
    }
    [data-testid="stButton"]:first-of-type > button:hover {
        background: #D7E4CE !important;
        border-color: var(--sage) !important;
        transform: none;
        box-shadow: var(--shadow-sm);
    }

    /* Inputs — clean white on cream with sage focus */
    .stTextInput > div > div > input,
    .stTextArea textarea,
    .stNumberInput input,
    .stDateInput input,
    .stSelectbox > div > div {
        background: var(--card-bg) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(107, 142, 111, 0.18) !important;
        color: var(--text-dark) !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea textarea:focus,
    .stNumberInput input:focus {
        border-color: var(--sage) !important;
        box-shadow: 0 0 0 3px rgba(107, 142, 111, 0.15) !important;
    }

    /* Tables and info/alert boxes */
    .stTable, [data-testid="stTable"] {
        background: var(--card-bg);
        border-radius: 16px;
        overflow: hidden;
        box-shadow: var(--shadow-sm);
    }
    [data-testid="stAlert"] {
        border-radius: 14px !important;
        border: 1px solid rgba(107, 142, 111, 0.18) !important;
    }

    /* Chat messages */
    .stChatMessage {
        direction: rtl;
        background: var(--card-bg) !important;
        border-radius: 16px !important;
        border: 1px solid rgba(107, 142, 111, 0.10);
        box-shadow: var(--shadow-sm);
    }

    /* Hide Streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
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

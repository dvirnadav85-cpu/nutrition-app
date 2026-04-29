# Nutrition app — context for new sessions

Hebrew mobile-first nutrition/health assistant for the user's mother (מירה נדב). Fully deployed.

- **Live:** https://nutrition-app-ri3gmsiarp2ntuceig7vxt.streamlit.app/
- **GitHub:** github.com/dvirnadav85-cpu/nutrition-app
- **Folder:** `C:\Users\Admin\Desktop\claude playground\תזונה`

## Stack
- Streamlit multi-page app (no password gate)
- Supabase via custom `supabase_client.py` (httpx REST — NOT supabase-py, breaks on Windows due to pyiceberg)
- Anthropic API: `claude-sonnet-4-6` everywhere, with `cache_control: ephemeral` prompt caching
- Plotly charts with `staticPlot: True` (no toolbar, finger scrolls page)
- All UI in Hebrew RTL
- `config.py`: handles both local (.env) and Streamlit Cloud (st.secrets)

## Files
- `app.py` — home page, nav buttons, nutrition table
- `common.py` — `page_setup()`, `SHARED_CSS` (cream+sage theme that propagates to ALL pages: file_uploader, camera_input, chat_input, expanders, metrics, tables, plotly cards), `now_il`/`period_label`/`greeting_now`/`hebrew_date_label`, `NUTRIENT_LABELS`, `get_daily_goals`, `get_daily_consumed`, `show_nutrition_table` (custom HTML card with sage/clay/coral progress bars — not `st.table`)
- `pages/1_💬_שיחה.py` — main chat (the most complex file)
- `pages/2_👤_פרופיל.py` — profile form (versioned, `is_current` flag)
- `pages/3_📋_יומן.py` — meal diary
- `pages/4_📊_גרפים.py` — all charts (weight, blood sugar, sleep, nutrient selector, blood markers); BASE_LAYOUT + palette constants (SAGE_DEEP/SAGE/CLAY/CORAL/HONEY/MAUVE) match the cream+sage theme
- `pages/5_🩸_בדיקות_דם.py` — blood test PDF/image upload + Claude parsing
- `pages/6_📈_תובנות.py` — weekly insights
- `reminder.py` — Twilio WhatsApp at 20:00 via Windows Task Scheduler

## Supabase tables (no RLS — single-user app)
- `profile` — versioned, columns include `daily_activity`, `medications`, `daily_goals` (jsonb)
- `meal_log` — `meal_date`, `meal_type`, `description`, `raw_input`, `nutrients` (jsonb)
- `weight_log` — `log_date`, `weight_kg`
- `blood_results` — `test_date`, `markers` (jsonb), `summary`, `source_filename`
- `blood_sugar_log` — `log_date`, `value_mgdl`, `reading_time`
- `sleep_log` — `log_date`, `duration_hours`, `quality`, `notes`
- `chat_messages` — `message_date`, `role`, `content` (every chat msg)
- `session_summaries` — `summary_date` (unique), `summary` (lazy-generated daily)
- `weekly_reports` — weekly insight reports

## Chat tag system (assistant emits hidden tags → app saves to DB)
All tags support optional `"date":"YYYY-MM-DD"` for past entries. System prompt includes today's date so Claude can resolve "אתמול"/"שלשום".

- `<!--MEAL:{...}-->` → meal_log; `nutrients` sub-dict only includes keys present in `daily_goals`
- `<!--WEIGHT:{"kg":...}-->` → weight_log
- `<!--ACTIVITY:{"description":...}-->` → updates profile.daily_activity
- `<!--MEDICATION:{"medications":...}-->` → updates profile.medications
- `<!--BLOOD_SUGAR:{"value":...,"reading_time":...}-->` → blood_sugar_log
- `<!--SLEEP:{"hours":...,"quality":...,"notes":...}-->` → sleep_log (quality: מעולה/טוב/בינוני/גרוע/גרוע מאוד)
- `<!--GOALS_UPDATE:{...}-->` → merge into profile.daily_goals
- `<!--GOALS_REMOVE:["key1","key2"]-->` → delete keys from profile.daily_goals

`parse_tags(text) -> (clean_text, tags_dict)`.

## Canonical nutrient keys (in `common.NUTRIENT_LABELS`)
kcal, protein_g, carbs_g, fat_g, sat_fat_g, fiber_g, sugar_g, sodium_mg, calcium_mg, iron_mg, b12_mcg, vitamin_d_iu, magnesium_mg, potassium_mg, phosphorus_mg, zinc_mg, cholesterol_mg.
Unknown keys fall back to raw key, no unit.

## What the assistant always sees in the system prompt
Built by `get_system()` → `load_data_context()` + `load_summaries_context()`:
1. Profile (name, age, goals, conditions, meds, activity)
2. Last 7 days of meals (grouped by date)
3. Last 5 weights
4. Latest blood test markers
5. Last 14 blood sugar readings
6. Last 14 sleep nights
7. Current daily_goals + today's consumed (per nutrient)
8. **Monthly nutrient averages — last 6 months** (long-term pattern awareness)
9. Overall weight range + measurement count
10. Last 14 daily session summaries
11. Current Israel time + Hebrew period (בוקר/צהריים/אחר הצהריים/ערב/לילה)

Caching: profile/data_context/summaries each cached in `session_state`, invalidated on `force_reload=True` after any tag-driven write.

## Chat persistence
- Every message saved to `chat_messages`
- On session start: today's messages restored (mom can scroll up after refresh)
- Past dates with messages but no `session_summaries` entry → lazy-summarized via Claude (~100 Hebrew words) on first session of new day

## Conventions
- Hebrew descriptors > numeric scales (e.g. sleep quality)
- Charts: minimal layout (`BASE_LAYOUT`), Hebrew short-date helper `short_date()` ("מרץ 21")
- `MAX_HISTORY = 10` recent messages sent to Claude API
- Israel timezone via `zoneinfo.ZoneInfo("Asia/Jerusalem")`
- Never delete data
- All API costs go to user's Anthropic account at console.anthropic.com (separate from Claude Code billing)

## Schema migrations done so far (manual ALTER/CREATE in Supabase dashboard)
- `ALTER TABLE profile ADD COLUMN daily_activity text`
- `ALTER TABLE profile ADD COLUMN daily_goals jsonb`
- `ALTER TABLE meal_log ADD COLUMN nutrients jsonb`
- `CREATE TABLE chat_messages, session_summaries, blood_sugar_log, sleep_log`
- All tables created without RLS (single-user app, anon key only)

from urllib.parse import quote

import config
import common
import streamlit as st

st.set_page_config(
    page_title="עוזרת תזונה אישית",
    page_icon="🥗",
    layout="centered",
)

common.page_setup()

CARDS = [
    {
        "variant": "featured",
        "title": "שיחה עם העוזרת",
        "sub": "שאלי כל שאלה על התזונה שלך",
        "slug": "שיחה",
        "icon": '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>',
    },
    {
        "variant": "v-clay",
        "title": "הפרופיל שלי",
        "sub": "פרטים אישיים ויעדים",
        "slug": "פרופיל",
        "icon": '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    },
    {
        "variant": "v-peach",
        "title": "יומן ארוחות",
        "sub": "תיעוד מה שאכלת היום",
        "slug": "יומן",
        "icon": '<path d="M9 2h6a2 2 0 0 1 2 2v2H7V4a2 2 0 0 1 2-2z"/><rect x="5" y="6" width="14" height="16" rx="2"/><line x1="9" y1="12" x2="15" y2="12"/><line x1="9" y1="16" x2="13" y2="16"/>',
    },
    {
        "variant": "v-honey",
        "title": "גרפים ומגמות",
        "sub": "איך התקדמת לאורך זמן",
        "slug": "גרפים",
        "icon": '<line x1="4" y1="20" x2="4" y2="10"/><line x1="10" y1="20" x2="10" y2="4"/><line x1="16" y1="20" x2="16" y2="14"/><line x1="2" y1="20" x2="22" y2="20"/>',
    },
    {
        "variant": "v-coral",
        "title": "בדיקות דם",
        "sub": "תוצאות אחרונות והשוואה",
        "slug": "בדיקות_דם",
        "icon": '<path d="M12 2.5 C 8 8, 5 12, 5 15.5 a 7 7 0 0 0 14 0 C 19 12, 16 8, 12 2.5 z"/>',
    },
    {
        "variant": "v-mauve",
        "title": "תובנות שבועיות",
        "sub": "סיכום והמלצות לשבוע",
        "slug": "תובנות",
        "icon": '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
    },
]

CHEVRON_SVG = (
    '<svg class="chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="15 18 9 12 15 6"/></svg>'
)

LEAF_SVG = """
<svg class="leaf" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path d="M100 20 C 60 40, 30 80, 30 130 C 30 160, 50 180, 80 180 C 130 180, 170 140, 170 90 C 170 60, 150 30, 100 20 Z"
        fill="none" stroke="#6B8E6F" stroke-width="1.2" opacity="0.6"/>
  <path d="M100 25 C 95 60, 85 100, 75 175" fill="none" stroke="#6B8E6F" stroke-width="1" opacity="0.5"/>
  <path d="M85 70 Q 70 75 60 90" fill="none" stroke="#6B8E6F" stroke-width="0.8" opacity="0.4"/>
  <path d="M82 100 Q 65 105 55 120" fill="none" stroke="#6B8E6F" stroke-width="0.8" opacity="0.4"/>
  <path d="M80 130 Q 65 135 55 150" fill="none" stroke="#6B8E6F" stroke-width="0.8" opacity="0.4"/>
</svg>
"""

HOME_CSS = """
<style>
  .app-home {
    max-width: 480px;
    margin: 0 auto;
    padding: 8px 4px 12px;
    position: relative;
    overflow: hidden;
  }
  .app-home .leaf {
    position: absolute;
    top: 14px; left: -30px;
    width: 180px; height: 180px;
    opacity: 0.35;
    pointer-events: none;
    transform: rotate(-25deg);
  }
  .app-home .header { padding: 8px 4px 0; margin-bottom: 28px; }
  .app-home .greeting {
    font-family: 'Assistant', sans-serif;
    font-weight: 500;
    font-size: 14px;
    letter-spacing: 0.5px;
    color: var(--sage-deep);
    text-transform: uppercase;
    margin-bottom: 8px;
    opacity: 0;
    animation: home-rise 0.7s 0.05s ease-out forwards;
  }
  .app-home .greeting::before {
    content: '';
    display: inline-block;
    width: 24px; height: 1.5px;
    background: var(--sage-deep);
    vertical-align: middle;
    margin-left: 10px;
    transform: translateY(-2px);
  }
  .app-home .title {
    font-family: 'Frank Ruhl Libre', serif;
    font-weight: 700;
    font-size: 36px;
    line-height: 1.15;
    color: var(--text-dark);
    letter-spacing: -0.5px;
    margin-bottom: 14px;
    opacity: 0;
    animation: home-rise 0.7s 0.15s ease-out forwards;
  }
  .app-home .title .accent {
    color: var(--sage-deep);
    font-style: italic;
    font-weight: 500;
  }
  .app-home .subtitle {
    font-family: 'Assistant', sans-serif;
    font-weight: 400;
    font-size: 16px;
    color: var(--text-medium);
    line-height: 1.5;
    max-width: 88%;
    opacity: 0;
    animation: home-rise 0.7s 0.25s ease-out forwards;
  }
  .app-home .meta-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 6px;
    margin-bottom: 14px;
    opacity: 0;
    animation: home-rise 0.7s 0.35s ease-out forwards;
  }
  .app-home .meta-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
    letter-spacing: 1.2px;
    text-transform: uppercase;
  }
  .app-home .meta-date {
    font-size: 12px;
    font-weight: 500;
    color: var(--text-muted);
  }
  .app-home .menu { display: flex; flex-direction: column; gap: 12px; }

  .app-home .card {
    background: var(--card-bg);
    border-radius: 20px;
    padding: 18px;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: var(--shadow-sm);
    border: 1px solid rgba(107, 142, 111, 0.07);
    cursor: pointer;
    text-decoration: none;
    color: inherit;
    transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1),
                box-shadow 0.25s ease, border-color 0.25s ease;
    position: relative;
    opacity: 0;
    animation: home-rise 0.6s ease-out forwards;
  }
  .app-home .card:nth-child(1) { animation-delay: 0.45s; }
  .app-home .card:nth-child(2) { animation-delay: 0.52s; }
  .app-home .card:nth-child(3) { animation-delay: 0.59s; }
  .app-home .card:nth-child(4) { animation-delay: 0.66s; }
  .app-home .card:nth-child(5) { animation-delay: 0.73s; }
  .app-home .card:nth-child(6) { animation-delay: 0.80s; }
  .app-home .card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
    border-color: rgba(107, 142, 111, 0.18);
  }
  .app-home .card:active {
    transform: translateY(0) scale(0.98);
    box-shadow: var(--shadow-sm);
  }

  .app-home .icon-wrap {
    flex-shrink: 0;
    width: 52px; height: 52px;
    border-radius: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .app-home .icon-wrap svg {
    width: 24px; height: 24px;
    stroke-width: 1.8;
    fill: none;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
  .app-home .card-text { flex: 1; min-width: 0; }
  .app-home .card-title {
    font-family: 'Assistant', sans-serif;
    font-weight: 600;
    font-size: 17px;
    color: var(--text-dark);
    margin-bottom: 2px;
    line-height: 1.3;
  }
  .app-home .card-sub {
    font-size: 13px;
    font-weight: 400;
    color: var(--text-muted);
    line-height: 1.35;
  }
  .app-home .chevron {
    flex-shrink: 0;
    width: 24px; height: 24px;
    color: var(--text-muted);
    opacity: 0.5;
    transition: transform 0.25s ease, opacity 0.25s ease;
  }
  .app-home .card:hover .chevron {
    opacity: 1;
    transform: translateX(-4px);
    color: var(--sage-deep);
  }

  .app-home .v-clay  .icon-wrap { background: var(--tint-clay); }
  .app-home .v-clay  .icon-wrap svg { stroke: var(--ic-clay); }
  .app-home .v-peach .icon-wrap { background: var(--tint-peach); }
  .app-home .v-peach .icon-wrap svg { stroke: var(--ic-peach); }
  .app-home .v-honey .icon-wrap { background: var(--tint-honey); }
  .app-home .v-honey .icon-wrap svg { stroke: var(--ic-honey); }
  .app-home .v-coral .icon-wrap { background: var(--tint-coral); }
  .app-home .v-coral .icon-wrap svg { stroke: var(--ic-coral); }
  .app-home .v-mauve .icon-wrap { background: var(--tint-mauve); }
  .app-home .v-mauve .icon-wrap svg { stroke: var(--ic-mauve); }

  .app-home .card.featured {
    background: linear-gradient(135deg, #5C7E60 0%, #4F6B52 100%);
    border: none;
    box-shadow: 0 8px 24px rgba(79, 107, 82, 0.22);
  }
  .app-home .card.featured .card-title { color: #FFFFFF; font-weight: 700; }
  .app-home .card.featured .card-sub   { color: rgba(255,255,255,0.78); }
  .app-home .card.featured .icon-wrap  { background: rgba(255,255,255,0.16); }
  .app-home .card.featured .icon-wrap svg { stroke: #FFFFFF; }
  .app-home .card.featured .chevron    { color: rgba(255,255,255,0.7); opacity: 1; }
  .app-home .card.featured:hover { box-shadow: 0 14px 32px rgba(79, 107, 82, 0.30); }

  @keyframes home-rise {
    from { opacity: 0; transform: translateY(12px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  @media (max-width: 380px) {
    .app-home .title { font-size: 30px; }
    .app-home .card { padding: 16px; }
    .app-home .icon-wrap { width: 46px; height: 46px; }
  }
</style>
"""

def _card_html(card: dict) -> str:
    href = "/" + quote(card["slug"], safe="")
    icon_svg = (
        '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">'
        f'{card["icon"]}</svg>'
    )
    return (
        f'<a class="card {card["variant"]}" href="{href}" target="_self">'
        f'  <div class="icon-wrap">{icon_svg}</div>'
        f'  <div class="card-text">'
        f'    <div class="card-title">{card["title"]}</div>'
        f'    <div class="card-sub">{card["sub"]}</div>'
        f'  </div>'
        f'  {CHEVRON_SVG}'
        f'</a>'
    )

cards_html = "\n".join(_card_html(c) for c in CARDS)
greeting = common.greeting_now()
date_label = common.hebrew_date_label()

home_html = f"""
{HOME_CSS}
<div class="app-home">
  {LEAF_SVG}
  <header class="header">
    <div class="greeting">{greeting}</div>
    <h1 class="title">עוזרת התזונה <span class="accent">האישית</span> שלי</h1>
    <p class="subtitle">איך אפשר לעזור לך היום? בחרי באחת מהאפשרויות למטה.</p>
  </header>
  <div class="meta-row">
    <span class="meta-label">תפריט ראשי</span>
    <span class="meta-date">{date_label}</span>
  </div>
  <nav class="menu">
    {cards_html}
  </nav>
</div>
"""

st.markdown(home_html, unsafe_allow_html=True)

st.markdown("---")
common.show_nutrition_table()

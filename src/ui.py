"""Transcript Studio UI — matches product mockup."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

PALETTE = {
    "lavender_grey": "#8E9AAF",
    "thistle": "#CBC0D3",
    "soft_blush": "#EFD3D7",
    "lavender_veil": "#FEEAFA",
    "lavender": "#DEE2FF",
    "text": "#525A6B",
    "nav_active": "#2C2A4A",
    "sidebar_bg": "#EEF1F6",
    "main_bg": "#F6F7FB",
    "card": "#FFFFFF",
    "green": "#22C55E",
}

P = PALETTE

WAVE_SVG = """<svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect x="3" y="10" width="3" height="8" rx="1.5" fill="#6366F1"/>
<rect x="10.5" y="6" width="3" height="12" rx="1.5" fill="#818CF8"/>
<rect x="18" y="3" width="3" height="15" rx="1.5" fill="#A5B4FC"/>
</svg>"""

THEME_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {{
    --nav-active: {P["nav_active"]};
    --lavender: {P["lavender"]};
    --thistle: {P["thistle"]};
}}

html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}}

.stApp {{
    background: {P["main_bg"]};
}}

.main .block-container {{
    padding-top: 0 !important;
    padding-bottom: 2rem;
    padding-left: 1rem;
    padding-right: 1rem;
    max-width: 100%;
}}
[data-testid="stMainBlockContainer"] {{
    padding-top: 0 !important;
}}
[data-testid="stAppViewContainer"] .main {{
    padding-top: 0 !important;
}}

#MainMenu, footer, [data-testid="stToolbar"] {{ visibility: hidden; height: 0; }}
header[data-testid="stHeader"] {{
    background: transparent;
    height: 0 !important;
    min-height: 0 !important;
    visibility: hidden;
}}
[data-testid="stDecoration"] {{
    display: none;
}}
div[data-testid="stAppViewContainer"] > section.main > div {{
    padding-top: 0 !important;
}}
/* First markdown block (utility bar) — drop default top widget gap */
.main .block-container > div:first-child {{
    margin-top: 0 !important;
    padding-top: 0 !important;
}}
[data-testid="stVerticalBlock"] > div:first-child {{
    gap: 0;
}}

/* Sidebar */
section[data-testid="stSidebar"],
div[data-testid="stSidebar"],
div[data-testid="stSidebar"] > div,
div[data-testid="stSidebar"] > div > div,
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
    background: {P["sidebar_bg"]} !important;
}}
section[data-testid="stSidebar"] {{
    border-right: 1px solid #E2E6EE;
    min-width: 240px;
    width: 240px !important;
}}
[data-testid="stSidebar"] .block-container {{
    padding: 1rem 0.75rem 1.5rem;
}}
[data-testid="stAppViewContainer"] > section.main {{
    padding-left: 0.5rem;
    padding-right: 0.75rem;
}}

.sb-brand-row {{
    display: flex;
    align-items: center;
    gap: 0.55rem;
    margin-bottom: 0.65rem;
}}
.sb-brand {{
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--nav-active);
    margin: 0;
}}
.sb-tag {{
    display: inline-block;
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #6366F1;
    background: {P["lavender"]};
    padding: 0.28rem 0.55rem;
    border-radius: 6px;
    margin-bottom: 1.1rem;
}}
.sb-card {{
    background: {P["card"]};
    border: 1px solid #E8EBF2;
    border-radius: 14px;
    padding: 0.85rem 1rem;
    margin-bottom: 0.55rem;
    display: flex;
    gap: 0.65rem;
    align-items: flex-start;
}}
.sb-card-icon {{
    width: 28px;
    height: 28px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.85rem;
    flex-shrink: 0;
}}
.sb-icon-doc {{ background: {P["lavender"]}; color: #4F46E5; }}
.sb-icon-pin {{ background: #DCFCE7; color: #16A34A; }}
.sb-card-title {{
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--nav-active);
    margin: 0;
    line-height: 1.35;
}}
.sb-card-sub {{
    font-size: 0.72rem;
    color: {P["text"]};
    opacity: 0.85;
    margin: 0.15rem 0 0;
}}
.sb-connected {{
    background: {P["card"]};
    border: 1px solid #E8EBF2;
    border-radius: 14px;
    padding: 0.75rem 1rem;
    font-size: 0.78rem;
    font-weight: 600;
    color: {P["green"]};
    margin-bottom: 1.25rem;
}}
.sb-label {{
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: {P["text"]};
    opacity: 0.65;
    margin: 0 0 0.45rem 0;
}}

/* Utility bar */
.utility-bar {{
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.65rem;
    padding-top: 0;
}}
.util-status {{
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: {P["text"]};
    opacity: 0.7;
}}
.util-dot {{
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: {P["green"]};
    margin-right: 0.35rem;
    vertical-align: middle;
}}
.deploy-btn {{
    font-size: 0.75rem;
    font-weight: 600;
    color: #6366F1;
    background: #fff;
    border: 1px solid #C7D2FE;
    border-radius: 999px;
    padding: 0.35rem 0.85rem;
}}

/* Hero */
.hero-mock {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 0.75rem;
    margin-bottom: 1rem;
    position: relative;
}}
.hero-copy {{ flex: 1; min-width: 0; }}
.hero-kicker {{
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: {P["text"]};
    opacity: 0.55;
    margin: 0 0 0.5rem 0;
}}
.hero-title {{
    font-size: clamp(1.2rem, 2.1vw, 1.65rem);
    font-weight: 700;
    color: var(--nav-active);
    margin: 0 0 0.45rem 0;
    line-height: 1.25;
}}
.hero-lead {{
    font-size: 0.88rem;
    color: {P["text"]};
    margin: 0 0 1rem 0;
    line-height: 1.45;
    max-width: 42rem;
}}
.chip-row {{ display: flex; flex-wrap: wrap; gap: 0.45rem; }}
.chip {{
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.72rem;
    font-weight: 500;
    color: {P["text"]};
    background: #fff;
    border: 1px solid #E2E6EE;
    border-radius: 999px;
    padding: 0.35rem 0.7rem;
}}
.chip-accent {{
    background: {P["lavender"]};
    border-color: #C7D2FE;
    color: var(--nav-active);
}}
.hero-art {{
    position: relative;
    width: 88px;
    height: 72px;
    flex-shrink: 0;
    margin-top: 0.35rem;
}}
.hero-art .b1 {{
    position: absolute;
    width: 72px; height: 72px;
    right: 0; top: 0;
    border-radius: 50%;
    background: {P["lavender"]};
    opacity: 0.85;
}}
.hero-art .b2 {{
    position: absolute;
    width: 56px; height: 56px;
    right: 28px; top: 32px;
    border-radius: 50%;
    background: {P["soft_blush"]};
    opacity: 0.9;
}}
.hero-art .b3 {{
    position: absolute;
    width: 40px; height: 40px;
    right: 8px; top: 48px;
    border-radius: 50%;
    background: {P["thistle"]};
    opacity: 0.75;
}}

/* Tabs */
div[data-testid="stTabs"] {{
    margin-bottom: 0;
}}
div[data-testid="stTabs"] [data-baseweb="tab-list"] {{
    gap: 1.5rem;
    background: transparent;
    border-bottom: 1px solid #E2E6EE;
    padding: 0 0.15rem;
}}
div[data-testid="stTabs"] button {{
    font-weight: 600;
    font-size: 0.88rem;
    color: {P["text"]};
    opacity: 0.55;
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    padding: 0.55rem 0.15rem 0.75rem !important;
    box-shadow: none !important;
}}
div[data-testid="stTabs"] button[aria-selected="true"] {{
    opacity: 1;
    color: var(--nav-active) !important;
    border-bottom: 3px solid #6366F1 !important;
}}

/* Tab panel — Streamlit wraps tab content here (no broken HTML boxes) */
div[data-testid="stTabPanel"] {{
    background: {P["card"]};
    border: 1px solid #E8EBF2;
    border-radius: 16px;
    padding: 1rem 1.2rem 1.25rem;
    margin-top: 0.35rem;
    box-shadow: 0 4px 18px -12px rgba(44, 42, 74, 0.12);
}}
div[data-testid="stTabPanel"][aria-hidden="true"] {{
    display: none !important;
}}
.panel-head {{
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.85rem;
}}
.panel-icon {{
    width: 40px;
    height: 40px;
    border-radius: 10px;
    background: {P["lavender"]};
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.1rem;
}}
.panel-label {{
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: {P["text"]};
    opacity: 0.55;
    margin: 0;
}}
.panel-title {{
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--nav-active);
    margin: 0.1rem 0 0;
}}

.footer-hint {{
    text-align: center;
    font-size: 0.78rem;
    color: {P["text"]};
    opacity: 0.55;
    margin: 1.25rem 0 0.5rem;
}}

/* Question box — Tab 1 guide select */
div[data-testid="stTabPanel"] [data-testid="stSelectbox"] {{
    border: 2px solid #A5B4FC;
    border-radius: 14px;
    padding: 0.35rem 0.55rem;
    margin-bottom: 0.75rem;
    margin-top: 0 !important;
    background: #fff;
}}
div[data-testid="stTabPanel"] [data-testid="stSelectbox"] label {{
    display: none !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}}
[data-testid="stSelectbox"] [data-baseweb="select"] > div {{
    background: transparent !important;
    border: none !important;
    border-radius: 10px !important;
    min-height: 44px;
    box-shadow: none !important;
}}
[data-testid="stSelectbox"] [data-baseweb="select"] span {{
    color: var(--nav-active) !important;
    font-size: 0.85rem !important;
}}

.stButton > button[kind="primary"] {{
    background: #6366F1 !important;
    color: #fff !important;
    border: none !important;
    border-radius: 999px !important;
    font-weight: 600 !important;
    padding: 0.5rem 1.25rem !important;
}}

/* Question box — Tab 3 chat input */
[data-testid="stChatInput"] {{
    border: 2px solid #A5B4FC !important;
    border-radius: 14px !important;
    background: #fff !important;
    padding: 0.15rem 0.35rem !important;
}}
[data-testid="stChatInput"] textarea {{
    border: none !important;
    border-radius: 10px !important;
    background: transparent !important;
}}
div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stMarkdownContainer"] {{
    border: 2px solid #A5B4FC;
    border-radius: 14px;
    padding: 0.65rem 0.9rem;
    background: #fff;
}}

/* Cards & synthesis */
.card {{
    border-radius: 14px;
    overflow: hidden;
    height: 100%;
    border: 1px solid #E8EBF2;
    background: #fff;
}}
.card-fr .card-band {{ background: linear-gradient(90deg, {P["soft_blush"]}, {P["lavender"]}); }}
.card-de .card-band {{ background: linear-gradient(90deg, {P["thistle"]}, {P["lavender_veil"]}); }}
.card-uk .card-band {{ background: linear-gradient(90deg, {P["lavender"]}, {P["lavender_veil"]}); }}
.card-band {{ height: 4px; }}
.card-head {{
    padding: 1rem 1.15rem 0.75rem;
    background: #FAFBFD;
    border-bottom: 1px solid #EEF0F4;
}}
.card-market {{
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--nav-active);
    opacity: 0.7;
}}
.card-name {{ font-size: 1rem; font-weight: 700; color: var(--nav-active); margin: 0.25rem 0 0; }}
.card-role {{ font-size: 0.78rem; color: {P["text"]}; margin: 0.1rem 0 0; }}
.card-body-wrap {{ padding: 1rem 1.15rem; }}
.status {{
    display: inline-block;
    font-size: 0.62rem;
    font-weight: 700;
    text-transform: uppercase;
    padding: 0.2rem 0.5rem;
    border-radius: 6px;
    margin-bottom: 0.6rem;
}}
.status-ok {{ background: #DCFCE7; color: #166534; }}
.status-no {{ background: {P["lavender_veil"]}; color: var(--nav-active); }}
.card-body {{ font-size: 0.84rem; line-height: 1.6; color: {P["text"]}; }}
.quote {{
    margin-top: 0.6rem;
    padding: 0.65rem 0.8rem;
    border-radius: 10px;
    font-size: 0.8rem;
    background: {P["lavender_veil"]};
    border-left: 3px solid #6366F1;
    color: var(--nav-active);
}}
.quote-time {{
    display: block;
    margin-top: 0.3rem;
    font-size: 0.65rem;
    font-weight: 600;
    opacity: 0.6;
}}

.synth-block {{
    border-radius: 14px;
    border: 1px solid #E8EBF2;
    margin-bottom: 1rem;
    overflow: hidden;
    background: #fff;
}}
.synth-top {{
    padding: 1rem 1.25rem;
    background: #fff;
    color: var(--nav-active);
    border: 2px solid #A5B4FC;
    border-radius: 12px;
    margin: 0 0 0;
}}
.synth-q {{ font-size: 0.9rem; font-weight: 600; margin: 0; line-height: 1.45; }}
.synth-grid {{ display: grid; grid-template-columns: 1fr 1fr; }}
@media (max-width: 768px) {{ .synth-grid {{ grid-template-columns: 1fr; }} }}
.synth-col-ag {{ background: #F8FAFC; padding: 1rem; border-right: 1px solid #EEF0F4; }}
.synth-col-dg {{ background: {P["lavender_veil"]}; padding: 1rem; }}
.synth-h {{
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--nav-active);
    margin: 0 0 0.5rem;
}}
.synth-line {{ font-size: 0.84rem; line-height: 1.5; color: {P["text"]}; margin-bottom: 0.65rem; }}
.synth-ref {{ font-size: 0.72rem; opacity: 0.65; margin-top: 0.25rem; }}

.hint-box {{
    text-align: center;
    padding: 1.25rem;
    border-radius: 14px;
    font-size: 0.84rem;
    color: {P["text"]};
    background: #F8FAFC;
    border: 1px dashed #E2E6EE;
    margin: 1rem 0;
}}
</style>
"""


def inject_theme() -> None:
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def esc(text: Any) -> str:
    return html.escape(str(text) if text is not None else "")


def render_utility_bar(api_ok: bool) -> None:
    label = "CONNECTED" if api_ok else "OFFLINE"
    st.markdown(
        f"""
        <div class="utility-bar">
            <span class="util-status">
                <span class="util-dot"></span>{label}
            </span>
            <span class="deploy-btn">⚡ Deploy</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_header(lead: str) -> None:
    st.markdown(
        f"""
        <div class="hero-mock">
            <div class="hero-copy">
                <p class="hero-kicker">Hasamex research</p>
                <h1 class="hero-title">European robotic surgery transcripts</h1>
                <p class="hero-lead">{esc(lead)}</p>
            </div>
            <div class="hero-art">
                <div class="b1"></div><div class="b2"></div><div class="b3"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def panel_header(icon: str, label: str, title: str) -> None:
    st.markdown(
        f"""
        <div class="panel-head">
            <div class="panel-icon">{icon}</div>
            <div>
                <p class="panel-label">{esc(label)}</p>
                <p class="panel-title">{esc(title)}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def footer_hint(message: str) -> None:
    st.markdown(f'<p class="footer-hint">{esc(message)}</p>', unsafe_allow_html=True)


def hint(message: str) -> None:
    st.markdown(f'<div class="hint-box">{esc(message)}</div>', unsafe_allow_html=True)


MARKET_CARD_CLASS = {
    "France": "card-fr",
    "Germany": "card-de",
    "United Kingdom": "card-uk",
}


def expert_card_html(
    *,
    expert: str,
    role: str,
    market: str,
    addressed: bool,
    answer: str,
    quotes: list[dict],
    quote_flags: list[dict],
) -> str:
    accent = MARKET_CARD_CLASS.get(market, "card-uk")
    status = (
        '<span class="status status-ok">In transcript</span>'
        if addressed
        else '<span class="status status-no">Not covered</span>'
    )
    quotes_html = ""
    for q in quotes:
        quotes_html += (
            f'<div class="quote">"{esc(q.get("text", ""))}"'
            f'<span class="quote-time">{esc(q.get("timestamp", ""))}</span></div>'
        )
    flags = ""
    for f in quote_flags:
        flags += f'<p class="card-role">{esc(f.get("note", ""))}</p>'

    role_line = esc(role) if role else ""
    return f"""
    <div class="card {accent}">
        <div class="card-band"></div>
        <div class="card-head">
            <div class="card-market">{esc(market)}</div>
            <p class="card-name">{esc(expert)}</p>
            {f'<p class="card-role">{role_line}</p>' if role_line else ''}
        </div>
        <div class="card-body-wrap">
            {status}
            <p class="card-body">{esc(answer)}</p>
            {quotes_html}
            {flags}
        </div>
    </div>
    """


def synthesis_html(block: dict) -> str:
    q = esc(block.get("question", ""))

    def _lines(items: list, builder) -> str:
        if not items:
            return '<div class="synth-line" style="opacity:0.7">—</div>'
        return "".join(builder(x) for x in items)

    ag_html = _lines(
        block.get("agreements") or [],
        lambda ag: (
            f'<div class="synth-line">{esc(ag.get("summary", ""))}'
            + "".join(
                f'<div class="synth-ref">{esc(s.get("expert"))} · {esc(s.get("timestamp"))}</div>'
                for s in (ag.get("supporting") or [])
            )
            + "</div>"
        ),
    )
    disag = block.get("disagreements") or []
    if not disag:
        dg_html = '<div class="synth-line" style="opacity:0.7">None identified.</div>'
    else:
        dg_html = _lines(
            disag,
            lambda dg: (
                f'<div class="synth-line">{esc(dg.get("summary", ""))}'
                + "".join(
                    f'<div class="synth-ref">{esc(p.get("expert"))}: {esc(p.get("position"))} '
                    f'({esc(p.get("timestamp"))})</div>'
                    for p in (dg.get("positions") or [])
                )
                + "</div>"
            ),
        )

    return f"""
    <div class="synth-block">
        <div class="synth-top"><p class="synth-q">{q}</p></div>
        <div class="synth-grid">
            <div class="synth-col-ag"><p class="synth-h">Agreements</p>{ag_html}</div>
            <div class="synth-col-dg"><p class="synth-h">Disagreements</p>{dg_html}</div>
        </div>
    </div>
    """


def sidebar(api_ok: bool) -> None:
    with st.sidebar:
        st.markdown(
            f"""
            <div class="sb-brand-row">
                {WAVE_SVG}
                <p class="sb-brand">Transcript Studio</p>
            </div>
            <span class="sb-tag">EU markets</span>
            <div class="sb-connected" style="color:{'#22C55E' if api_ok else '#DC2626'}">
                ● {'OpenRouter connected' if api_ok else 'API key missing'}
            </div>
            """,
            unsafe_allow_html=True,
        )

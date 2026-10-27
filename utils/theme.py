"""Theme and UI design system for Cricbuzz LiveStats.

Provides consistent Midnight Cricket + Electric Lime visual identity,
custom CSS injection, metric cards, badges, and shared UI components
across all Streamlit pages.
"""

from typing import Optional
import streamlit as st

from config import settings

# ------------------------------------------------------------------------------
# COLOR PALETTE TOKENS
# ------------------------------------------------------------------------------
COLOR_BG_MIDNIGHT = "#0B1220"
COLOR_PANEL_DARK = "#111C2E"
COLOR_CARD_SURFACE = "#17243A"
COLOR_ACCENT_LIME = "#B7F34A"
COLOR_ACCENT_GREEN = "#20C997"
COLOR_TEXT_PRIMARY = "#F3F6FC"
COLOR_TEXT_SECONDARY = "#A7B3C7"
COLOR_BORDER = "#2A3850"
COLOR_ERROR = "#FF6B6B"
COLOR_WARNING = "#F59E0B"
COLOR_SUCCESS = "#10B981"


# ------------------------------------------------------------------------------
# GLOBAL CSS STYLESHEET
# ------------------------------------------------------------------------------
CUSTOM_CSS = f"""
<style>
/* Import Inter & JetBrains Mono Fonts */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}}

/* Main Background and Text Defaults */
.stApp {{
    background-color: {COLOR_BG_MIDNIGHT};
    color: {COLOR_TEXT_PRIMARY};
}}

/* Sidebar Styling */
section[data-testid="stSidebar"] {{
    background-color: {COLOR_PANEL_DARK};
    border-right: 1px solid {COLOR_BORDER};
}}

section[data-testid="stSidebar"] .stMarkdown p {{
    color: {COLOR_TEXT_SECONDARY};
}}

/* Streamlit Header & Toolbar */
header[data-testid="stHeader"] {{
    background-color: rgba(11, 18, 32, 0.9);
    border-bottom: 1px solid {COLOR_BORDER};
}}

/* Primary & Secondary Buttons */
.stButton > button {{
    background-color: {COLOR_CARD_SURFACE};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    font-weight: 600;
    font-size: 14px;
    padding: 0.45rem 1rem;
    transition: all 0.2s ease-in-out;
}}

.stButton > button:hover {{
    border-color: {COLOR_ACCENT_LIME};
    color: {COLOR_ACCENT_LIME};
    box-shadow: 0 0 10px rgba(183, 243, 74, 0.2);
}}

.stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"] {{
    background-color: {COLOR_ACCENT_LIME};
    color: #0B1220 !important;
    border: 1px solid {COLOR_ACCENT_LIME};
    font-weight: 700;
}}

.stButton > button[kind="primary"]:hover, .stButton > button[data-testid="stBaseButton-primary"]:hover {{
    background-color: #A3E635;
    box-shadow: 0 0 15px rgba(183, 243, 74, 0.4);
}}

/* Form Input Fields */
.stTextInput > div > div > input,
.stSelectbox > div > div,
.stMultiSelect > div > div,
.stNumberInput > div > div > input,
.stTextArea > div > div > textarea {{
    background-color: {COLOR_PANEL_DARK} !important;
    color: {COLOR_TEXT_PRIMARY} !important;
    border: 1px solid {COLOR_BORDER} !important;
    border-radius: 8px !important;
}}

.stTextInput > div > div > input:focus,
.stSelectbox > div > div:focus-within,
.stNumberInput > div > div > input:focus {{
    border-color: {COLOR_ACCENT_LIME} !important;
    box-shadow: 0 0 8px rgba(183, 243, 74, 0.25) !important;
}}

/* Streamlit Native Metric Override */
[data-testid="stMetricValue"] {{
    color: {COLOR_ACCENT_LIME} !important;
    font-weight: 800 !important;
    font-family: 'JetBrains Mono', monospace !important;
}}

[data-testid="stMetricLabel"] p {{
    color: {COLOR_TEXT_SECONDARY} !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    font-size: 12px !important;
}}

/* Card Container */
.cric-card {{
    background: {COLOR_CARD_SURFACE};
    border: 1px solid {COLOR_BORDER};
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1rem;
    transition: transform 0.15s ease, border-color 0.15s ease;
}}

.cric-card:hover {{
    border-color: rgba(183, 243, 74, 0.35);
}}

/* KPI Metric Card */
.cric-kpi {{
    background: {COLOR_CARD_SURFACE};
    border: 1px solid {COLOR_BORDER};
    border-radius: 12px;
    padding: 1.2rem;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 110px;
    transition: all 0.2s ease;
}}

.cric-kpi:hover {{
    border-color: {COLOR_ACCENT_LIME};
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
}}

.cric-kpi-title {{
    color: {COLOR_TEXT_SECONDARY};
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}

.cric-kpi-val {{
    color: {COLOR_ACCENT_LIME};
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.9rem;
    font-weight: 800;
    margin: 0.25rem 0;
}}

.cric-kpi-sub {{
    color: {COLOR_TEXT_SECONDARY};
    font-size: 0.78rem;
    display: flex;
    align-items: center;
    gap: 0.3rem;
}}

/* Badges */
.cric-badge {{
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.22rem 0.6rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    line-height: 1;
}}

.cric-badge-lime {{
    background: rgba(183, 243, 74, 0.15);
    color: {COLOR_ACCENT_LIME};
    border: 1px solid rgba(183, 243, 74, 0.3);
}}

.cric-badge-green {{
    background: rgba(32, 201, 151, 0.15);
    color: {COLOR_ACCENT_GREEN};
    border: 1px solid rgba(32, 201, 151, 0.3);
}}

.cric-badge-amber {{
    background: rgba(245, 158, 11, 0.15);
    color: {COLOR_WARNING};
    border: 1px solid rgba(245, 158, 11, 0.3);
}}

.cric-badge-red {{
    background: rgba(255, 107, 107, 0.15);
    color: {COLOR_ERROR};
    border: 1px solid rgba(255, 107, 107, 0.3);
}}

.cric-badge-neutral {{
    background: rgba(167, 179, 199, 0.15);
    color: {COLOR_TEXT_SECONDARY};
    border: 1px solid {COLOR_BORDER};
}}

/* Match Banner Cards */
.match-card {{
    background: {COLOR_CARD_SURFACE};
    border: 1px solid {COLOR_BORDER};
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1rem;
}}

.match-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid {COLOR_BORDER};
    padding-bottom: 0.75rem;
    margin-bottom: 0.75rem;
}}

.match-team-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.35rem 0;
}}

.match-team-name {{
    font-size: 1.05rem;
    font-weight: 700;
    color: {COLOR_TEXT_PRIMARY};
}}

.match-team-score {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.1rem;
    font-weight: 700;
    color: {COLOR_ACCENT_LIME};
}}

/* Tabs Styling */
.stTabs [data-baseweb="tab-list"] {{
    gap: 0.5rem;
    border-bottom: 1px solid {COLOR_BORDER};
}}

.stTabs [data-baseweb="tab"] {{
    height: 42px;
    padding: 0.5rem 1.2rem;
    background-color: transparent;
    border-radius: 6px 6px 0 0;
    color: {COLOR_TEXT_SECONDARY};
    font-weight: 600;
    border: none;
}}

.stTabs [aria-selected="true"] {{
    color: {COLOR_ACCENT_LIME} !important;
    border-bottom: 2px solid {COLOR_ACCENT_LIME} !important;
    background-color: rgba(183, 243, 74, 0.05) !important;
}}

/* Streamlit Dataframe Overrides */
div[data-testid="stDataFrame"] {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    overflow: hidden;
}}

/* Offline Banner */
.offline-banner {{
    background: rgba(245, 158, 11, 0.1);
    border: 1px solid rgba(245, 158, 11, 0.3);
    border-radius: 8px;
    padding: 0.65rem 1rem;
    color: {COLOR_WARNING};
    font-size: 0.85rem;
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin-bottom: 1.25rem;
}}
</style>
"""


def apply_custom_theme() -> None:
    """Inject the global Midnight Cricket + Electric Lime stylesheet."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_header(
    title: str,
    subtitle: str,
    icon: str = "🏏",
    badge_text: Optional[str] = None,
    badge_variant: str = "lime",
) -> None:
    """Render a unified, premium page hero header with icon and optional status badge.

    Args:
        title: Main page title.
        subtitle: Descriptive subtitle explaining the page.
        icon: Emoji or icon symbol.
        badge_text: Optional text to display inside a badge.
        badge_variant: Badge color style ('lime', 'green', 'amber', 'red', 'neutral').
    """
    badge_html = f'<span class="cric-badge cric-badge-{badge_variant}">{badge_text}</span>' if badge_text else ""
    st.markdown(
        f"""
        <div style="margin-bottom: 1.5rem; border-bottom: 1px solid {COLOR_BORDER}; padding-bottom: 1rem;">
            <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem;">
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <span style="font-size: 2rem;">{icon}</span>
                    <h1 style="margin: 0; font-size: 1.85rem; font-weight: 800; color: {COLOR_TEXT_PRIMARY};">{title}</h1>
                </div>
                {badge_html}
            </div>
            <p style="margin: 0.5rem 0 0 0; color: {COLOR_TEXT_SECONDARY}; font-size: 0.95rem;">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_card(
    title: str,
    value: str,
    delta: Optional[str] = None,
    delta_positive: bool = True,
    icon: str = "📊",
    subtext: Optional[str] = None,
) -> None:
    """Render a styled KPI metric card.

    Args:
        title: Metric label.
        value: Primary metric number or string.
        delta: Optional delta badge string (e.g. '+12%').
        delta_positive: True for green delta, False for red delta.
        icon: Icon symbol for metric category.
        subtext: Contextual footnote or comparison text.
    """
    delta_color = COLOR_SUCCESS if delta_positive else COLOR_ERROR
    delta_icon = "▲" if delta_positive else "▼"
    delta_html = f'<span style="color: {delta_color}; font-weight: 600;">{delta_icon} {delta}</span>' if delta else ""
    sub_html = f'<div class="cric-kpi-sub">{delta_html} <span>{subtext or ""}</span></div>' if (delta or subtext) else ""

    st.markdown(
        f"""
        <div class="cric-kpi">
            <div class="cric-kpi-title">
                <span>{title}</span>
                <span>{icon}</span>
            </div>
            <div class="cric-kpi-val">{value}</div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_badge(text: str, variant: str = "lime") -> str:
    """Return an HTML snippet for a styled badge.

    Args:
        text: Badge label.
        variant: Color variant ('lime', 'green', 'amber', 'red', 'neutral').

    Returns:
        HTML string representing the badge.
    """
    return f'<span class="cric-badge cric-badge-{variant}">{text}</span>'


def render_offline_banner(message: Optional[str] = None) -> None:
    """Display standard notification banner for offline-fixture mode."""
    msg = message or "OFFLINE DEMO MODE ACTIVE: Data shown is synthetic demonstration data from local SQLite fixtures."
    st.markdown(
        f"""
        <div class="offline-banner">
            <span style="font-size: 1.1rem;">⚠️</span>
            <div><strong>{msg}</strong> Real-time Cricbuzz API integration will connect in Stage 11.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_brand() -> None:
    """Render the standard sidebar brand header and system status."""
    with st.sidebar:
        st.markdown(
            f"""
            <div style="padding: 0.5rem 0 1rem 0; border-bottom: 1px solid {COLOR_BORDER}; margin-bottom: 1rem;">
                <div style="display: flex; align-items: center; gap: 0.6rem;">
                    <span style="font-size: 1.7rem;">🏏</span>
                    <div>
                        <div style="font-weight: 800; font-size: 1.15rem; color: {COLOR_TEXT_PRIMARY}; letter-spacing: -0.02em;">
                            CRICBUZZ <span style="color: {COLOR_ACCENT_LIME};">LIVESTATS</span>
                        </div>
                        <div style="font-size: 0.72rem; color: {COLOR_TEXT_SECONDARY}; text-transform: uppercase; letter-spacing: 0.06em;">
                            Real-Time Cricket Analytics
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Mode Badge
        if settings.api.offline_mode:
            st.markdown(
                f"""
                <div style="background: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.25); border-radius: 6px; padding: 0.45rem 0.65rem; margin-bottom: 1rem; font-size: 0.78rem; color: {COLOR_WARNING}; display: flex; align-items: center; gap: 0.4rem;">
                    <span style="font-size: 0.9rem;">⚡</span>
                    <div><strong>OFFLINE FIXTURE MODE</strong><br/><span style="font-size: 0.7rem; color: {COLOR_TEXT_SECONDARY};">SQLite Demo DB (Stage 7)</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Quick Database Stats Widget
        st.markdown(
            f"""
            <div style="background: {COLOR_CARD_SURFACE}; border: 1px solid {COLOR_BORDER}; border-radius: 8px; padding: 0.75rem; margin-bottom: 1.25rem;">
                <div style="font-size: 0.72rem; font-weight: 700; color: {COLOR_TEXT_SECONDARY}; text-transform: uppercase; margin-bottom: 0.4rem;">
                    Engine Status
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 0.2rem;">
                    <span style="color: {COLOR_TEXT_SECONDARY};">Database:</span>
                    <span style="color: {COLOR_ACCENT_LIME}; font-weight: 600;">SQLite 3.49 (3NF)</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 0.2rem;">
                    <span style="color: {COLOR_TEXT_SECONDARY};">Foreign Keys:</span>
                    <span style="color: {COLOR_ACCENT_GREEN}; font-weight: 600;">ENFORCED</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.8rem;">
                    <span style="color: {COLOR_TEXT_SECONDARY};">SQL Queries:</span>
                    <span style="color: {COLOR_TEXT_PRIMARY}; font-weight: 600;">25/25 Ready</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.caption("Innovexis Internship Project • Oct 2026")

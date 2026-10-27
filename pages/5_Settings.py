"""Settings & System Diagnostics Page for Cricbuzz LiveStats.

Provides database connectivity diagnostics, cache management, environment telemetry,
and real Cricbuzz REST API configuration guidelines (Stage 11 roadmap).
"""

import os
from pathlib import Path
import sqlite3
import sys
import streamlit as st

from api.factory import get_cricket_client
from config import settings
from data.seed_data import seed_database
from database.connection import db_manager
from utils.theme import (
    COLOR_ACCENT_GREEN,
    COLOR_ACCENT_LIME,
    COLOR_BORDER,
    COLOR_CARD_SURFACE,
    COLOR_PANEL_DARK,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_WARNING,
    apply_custom_theme,
    render_header,
    render_offline_banner,
    render_sidebar_brand,
)

# ------------------------------------------------------------------------------
# PAGE CONFIGURATION
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title=f"Settings | {settings.app.app_short_title}",
    page_icon="⚙️",
    layout="wide",
)

apply_custom_theme()
render_sidebar_brand()

render_header(
    title="Settings & System Diagnostics",
    subtitle="Database engine telemetry, cache governance, and environment configuration",
    icon="⚙️",
    badge_text="TELEMETRY ONLINE",
    badge_variant="green",
)

if settings.api.offline_mode:
    render_offline_banner()


# ------------------------------------------------------------------------------
# TELEMETRY DATA FETCHERS
# ------------------------------------------------------------------------------
def get_db_diagnostics() -> dict:
    """Fetch SQLite integrity, pragma, and table statistics."""
    try:
        with db_manager.get_connection() as conn:
            cur = conn.cursor()

            # Check integrity
            integrity = cur.execute("PRAGMA integrity_check;").fetchone()[0]
            fk_status = cur.execute("PRAGMA foreign_keys;").fetchone()[0]

            # Table counts
            tables = [
                "teams", "players", "venues", "series", "matches",
                "innings", "batting_performances", "bowling_performances",
                "fielding_performances", "partnerships"
            ]
            counts = {}
            for tbl in tables:
                counts[tbl] = cur.execute(f"SELECT COUNT(*) FROM {tbl};").fetchone()[0]

            db_file = Path(settings.paths.db_path)
            file_size_kb = round(db_file.stat().st_size / 1024, 2) if db_file.exists() else 0.0

            return {
                "integrity": integrity,
                "foreign_keys": "ENFORCED (1)" if fk_status == 1 else "DISABLED (0)",
                "file_size_kb": file_size_kb,
                "file_path": str(db_file),
                "counts": counts,
                "sqlite_version": sqlite3.sqlite_version,
            }
    except Exception as exc:
        return {"error": str(exc)}


diag = get_db_diagnostics()


# ------------------------------------------------------------------------------
# 1. DATABASE ENGINE TELEMETRY
# ------------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="cric-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
            <div style="font-weight: 700; font-size: 1.1rem; color: {COLOR_TEXT_PRIMARY};">
                🗄️ Relational Database Telemetry (SQLite 3NF)
            </div>
            <span class="cric-badge cric-badge-green">PRAGMA FK ACTIVE</span>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 0.75rem; font-size: 0.85rem;">
            <div style="background: {COLOR_PANEL_DARK}; border: 1px solid {COLOR_BORDER}; border-radius: 6px; padding: 0.6rem;">
                <span style="color: {COLOR_TEXT_SECONDARY};">SQLite Engine Version:</span><br/>
                <strong style="color: {COLOR_ACCENT_LIME}; font-family: monospace;">{diag.get('sqlite_version', 'Unknown')}</strong>
            </div>
            <div style="background: {COLOR_PANEL_DARK}; border: 1px solid {COLOR_BORDER}; border-radius: 6px; padding: 0.6rem;">
                <span style="color: {COLOR_TEXT_SECONDARY};">Integrity Check:</span><br/>
                <strong style="color: {COLOR_ACCENT_GREEN};">{diag.get('integrity', 'Unknown')}</strong>
            </div>
            <div style="background: {COLOR_PANEL_DARK}; border: 1px solid {COLOR_BORDER}; border-radius: 6px; padding: 0.6rem;">
                <span style="color: {COLOR_TEXT_SECONDARY};">Foreign Key Enforcement:</span><br/>
                <strong style="color: {COLOR_ACCENT_GREEN};">{diag.get('foreign_keys', 'Unknown')}</strong>
            </div>
            <div style="background: {COLOR_PANEL_DARK}; border: 1px solid {COLOR_BORDER}; border-radius: 6px; padding: 0.6rem;">
                <span style="color: {COLOR_TEXT_SECONDARY};">Database File Size:</span><br/>
                <strong style="color: {COLOR_TEXT_PRIMARY};">{diag.get('file_size_kb', 0)} KB</strong>
            </div>
        </div>
        <div style="margin-top: 0.75rem; font-size: 0.8rem; color: {COLOR_TEXT_SECONDARY};">
            Database Location: <code>{diag.get('file_path', '')}</code>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------------------
# 2. TABLE ROW COUNT METRICS
# ------------------------------------------------------------------------------
st.markdown(
    f"""
    <div style="font-weight: 700; font-size: 1rem; color: {COLOR_TEXT_PRIMARY}; margin: 1rem 0 0.5rem 0;">
        📊 Normalized Entity Record Tallies
    </div>
    """,
    unsafe_allow_html=True,
)

if "counts" in diag:
    t_cols = st.columns(5)
    labels = [
        ("Teams", "teams", "🌍"),
        ("Athletes", "players", "👤"),
        ("Venues", "venues", "🏟️"),
        ("Series", "series", "📅"),
        ("Matches", "matches", "🏆"),
    ]
    for idx, (label, key, icon) in enumerate(labels):
        with t_cols[idx]:
            st.metric(label=f"{icon} {label}", value=diag["counts"].get(key, 0))

    t_cols2 = st.columns(5)
    labels2 = [
        ("Innings", "innings", "⏱️"),
        ("Batting Cards", "batting_performances", "🏏"),
        ("Bowling Spells", "bowling_performances", "🎯"),
        ("Fielding Acts", "fielding_performances", "🧤"),
        ("Partnerships", "partnerships", "🤝"),
    ]
    for idx, (label, key, icon) in enumerate(labels2):
        with t_cols2[idx]:
            st.metric(label=f"{icon} {label}", value=diag["counts"].get(key, 0))


# ------------------------------------------------------------------------------
# 3. ENVIRONMENT & RUNTIME TELEMETRY
# ------------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="cric-card" style="margin-top: 1.25rem;">
        <div style="font-weight: 700; font-size: 1.05rem; color: {COLOR_TEXT_PRIMARY}; margin-bottom: 0.6rem;">
            ⚙️ Runtime Environment & Security Telemetry
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 0.75rem; font-size: 0.85rem;">
            <div style="background: {COLOR_PANEL_DARK}; border: 1px solid {COLOR_BORDER}; border-radius: 6px; padding: 0.6rem;">
                <span style="color: {COLOR_TEXT_SECONDARY};">Python Version:</span><br/>
                <strong style="color: {COLOR_TEXT_PRIMARY};">{sys.version.split()[0]}</strong>
            </div>
            <div style="background: {COLOR_PANEL_DARK}; border: 1px solid {COLOR_BORDER}; border-radius: 6px; padding: 0.6rem;">
                <span style="color: {COLOR_TEXT_SECONDARY};">Streamlit Version:</span><br/>
                <strong style="color: {COLOR_ACCENT_LIME};">{st.__version__}</strong>
            </div>
            <div style="background: {COLOR_PANEL_DARK}; border: 1px solid {COLOR_BORDER}; border-radius: 6px; padding: 0.6rem;">
                <span style="color: {COLOR_TEXT_SECONDARY};">API Mode:</span><br/>
                <strong style="color: {COLOR_WARNING};">OFFLINE FIXTURE MODE</strong>
            </div>
            <div style="background: {COLOR_PANEL_DARK}; border: 1px solid {COLOR_BORDER}; border-radius: 6px; padding: 0.6rem;">
                <span style="color: {COLOR_TEXT_SECONDARY};">API Secret Key:</span><br/>
                <strong style="color: {COLOR_TEXT_SECONDARY}; font-family: monospace;">•••••••••••• (Secured)</strong>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------------------
# 4. MAINTENANCE ACTIONS & CACHE GOVERNANCE
# ------------------------------------------------------------------------------
st.markdown(
    f"""
    <div style="font-weight: 700; font-size: 1rem; color: {COLOR_TEXT_PRIMARY}; margin: 1.25rem 0 0.5rem 0;">
        🧹 System Maintenance & Cache Governance
    </div>
    """,
    unsafe_allow_html=True,
)

m_col1, m_col2 = st.columns(2)

with m_col1:
    st.markdown(
        f"""
        <div class="cric-card">
            <h5 style="margin: 0 0 0.4rem 0; color: {COLOR_TEXT_PRIMARY}; font-size: 0.95rem;">Clear Streamlit Application Cache</h5>
            <p style="font-size: 0.82rem; color: {COLOR_TEXT_SECONDARY}; line-height: 1.4; margin-bottom: 0.8rem;">
                Flushes cached database connections and query runner resources. Useful after manual data mutations.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("🧹 Clear In-Memory Cache", key="btn_clear_cache"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("✅ Application cache successfully purged!")

with m_col2:
    st.markdown(
        f"""
        <div class="cric-card">
            <h5 style="margin: 0 0 0.4rem 0; color: {COLOR_TEXT_PRIMARY}; font-size: 0.95rem;">Re-Seed Sample Dataset</h5>
            <p style="font-size: 0.82rem; color: {COLOR_TEXT_SECONDARY}; line-height: 1.4; margin-bottom: 0.8rem;">
                Safely re-populates missing sample fixtures from <code>data/seed_data.py</code> idempotently.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    reseed_confirm = st.checkbox("Confirm re-seed of sample fixtures")
    if st.button("🌱 Re-Seed Sample Data", key="btn_reseed"):
        if not reseed_confirm:
            st.warning("Please tick the confirmation checkbox to trigger re-seeding.")
        else:
            try:
                seed_database(settings.paths.db_path)
                st.success("✅ Sample dataset successfully re-seeded idempotently!")
                st.rerun()
            except Exception as exc:
                st.error(f"Re-seed Error: {exc}")


# ------------------------------------------------------------------------------
# 5. CRICKET DATA API INTEGRATION & QUOTA TELEMETRY (STAGE 11)
# ------------------------------------------------------------------------------
api_status_badge = '<span class="cric-badge cric-badge-amber">OFFLINE MODE (SAFE)</span>' if settings.api.offline_mode else '<span class="cric-badge cric-badge-lime">LIVE MODE</span>'
provider_title = "CricketData.org (Recommended Free Tier)" if settings.api.provider == "cricketdata" else "RapidAPI Cricbuzz"

st.markdown(
    f"""
    <div class="cric-card" style="margin-top: 1.25rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <h4 style="margin: 0; font-size: 1.05rem; color: {COLOR_TEXT_PRIMARY};">
                🌐 Cricket Data API Integration & Free Quota Telemetry
            </h4>
            {api_status_badge}
        </div>
        <p style="color: {COLOR_TEXT_SECONDARY}; font-size: 0.85rem; line-height: 1.5; margin-bottom: 0.75rem;">
            Configured Provider: <strong>{provider_title}</strong>.
            In accordance with ADR-004 and ADR-006, live API data is isolated with <code>source = 'API'</code>
            and protected against manual modification, preserving all local demo fixtures.
        </p>
        <div style="font-size: 0.82rem; color: {COLOR_TEXT_SECONDARY}; line-height: 1.8;">
            • <strong>Free Tier Quota:</strong> 100 requests/day lifetime free (Zero credit card or payment details required).<br/>
            • <strong>Verified Endpoints:</strong> <code>GET /currentMatches</code> (live fixtures), <code>GET /match_scorecard</code> (innings breakdowns).<br/>
            • <strong>In-Memory Cache:</strong> 60-second TTL prevents repeated requests and protects your 100 hits/day allowance.<br/>
            • <strong>Data Provenance:</strong> Independent cricket aggregator (~30–60s broadcast delay).<br/>
            • <strong>Enabling Live Mode:</strong> Obtain key from <a href="https://cricketdata.org" target="_blank" style="color: {COLOR_ACCENT_LIME};">CricketData.org</a>, set <code>CRICKETDATA_API_KEY</code> and <code>OFFLINE_MODE=False</code> in <code>.env</code>.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

test_col1, test_col2 = st.columns([3, 1])
with test_col1:
    st.caption("Verify API credentials, latency, and daily quota consumption.")
with test_col2:
    btn_test_conn = st.button("🔌 Test Connection", key="btn_test_api_conn", use_container_width=True)

if btn_test_conn:
    if settings.api.offline_mode:
        st.warning(
            "ℹ️ Connection Test Skipped: System is running in OFFLINE_MODE=True. "
            "Live network calls are disabled to guarantee zero quota consumption. "
            "To test live connectivity, obtain a free key from CricketData.org and set OFFLINE_MODE=False in .env."
        )
    else:
        try:
            client = get_cricket_client()
            with st.spinner(f"Testing live handshake with {client.provider_name}..."):
                res = client.test_connection()
            if res.get("success"):
                st.success(f"✅ {res.get('message')}")
                q = res.get("quota", {})
                if q.get("hits_today") is not None:
                    st.info(f"📊 Telemetry: {q.get('hits_today')} hits today / {q.get('hits_limit')} limit ({q.get('hits_remaining')} remaining)")
            else:
                st.error(f"❌ Connection Failed ({res.get('error_type')}): {res.get('message')}")
        except Exception as exc:
            st.error(f"❌ Diagnostic Failure: {exc}")


"""Match Center & Live Scores Page for Cricbuzz LiveStats.

Browse international and domestic cricket fixtures with real-time scorecards,
format filtering, toss outcomes, and detailed batting & bowling scorecards.
"""

import pandas as pd
import streamlit as st

from api.base_client import (
    APIAuthenticationError,
    APIConnectionError,
    CricketAPIError,
    MissingAPIKeyError,
    RateLimitExceededError,
)
from api.factory import get_cricket_client
from api.parser import CricketDataParser
from config import settings
from database.connection import db_manager
from services.ingestion_service import IngestionService
from utils.theme import (
    COLOR_ACCENT_GREEN,
    COLOR_ACCENT_LIME,
    COLOR_BORDER,
    COLOR_CARD_SURFACE,
    COLOR_PANEL_DARK,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    apply_custom_theme,
    render_header,
    render_offline_banner,
    render_sidebar_brand,
)

# ------------------------------------------------------------------------------
# PAGE CONFIGURATION
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title=f"Match Center | {settings.app.app_short_title}",
    page_icon="🔴",
    layout="wide",
)

apply_custom_theme()
render_sidebar_brand()

render_header(
    title="Match Center & Live Scores",
    subtitle="Detailed cricket fixtures, toss intelligence, and full innings scorecards",
    icon="🔴",
    badge_text="OFFLINE DEMO DATA" if settings.api.offline_mode else "LIVE DATA FEED",
    badge_variant="amber" if settings.api.offline_mode else "green",
)

if settings.api.offline_mode:
    render_offline_banner(
        "DEMO FIXTURES ACTIVE: The matches shown below are verified sample records from the SQLite local database."
    )
else:
    st.info(
        "📡 LIVE API MODE: Displaying fixtures from CricketData.org. "
        "Scores reflect an independent data feed with ~30-60s broadcast delay."
    )

# ------------------------------------------------------------------------------
# LIVE API SYNC CONTROL
# ------------------------------------------------------------------------------
sync_col1, sync_col2 = st.columns([3, 1])
with sync_col1:
    st.markdown(
        f"""
        <div style="font-size: 0.82rem; color: {COLOR_TEXT_SECONDARY}; padding: 0.35rem 0;">
            Synchronize live fixtures and scorecards from external API feed.
            Protected by ADR-006: Local sample fixtures are preserved.
        </div>
        """,
        unsafe_allow_html=True,
    )
with sync_col2:
    btn_sync = st.button("🔄 Sync Live Feed", key="btn_sync_live_matches", use_container_width=True)

if btn_sync:
    if settings.api.offline_mode:
        st.warning(
            "⚠️ Live API Sync Disabled: System is operating in OFFLINE_MODE=True. "
            "Zero external requests were sent. To enable live sync with CricketData.org, "
            "obtain a free key and set OFFLINE_MODE=False in your .env file."
        )
    else:
        try:
            client = get_cricket_client()
            with st.spinner(f"Connecting to {client.provider_name}..."):
                raw_matches = client.get_live_matches(force_refresh=True)
                ingestion = IngestionService()
                ingested = 0
                for raw in raw_matches:
                    parsed = CricketDataParser.parse_match(raw)
                    ingestion.ingest_match(parsed)
                    ingested += 1
            st.success(f"✅ Successfully synchronized {ingested} fixtures from API feed!")
            st.rerun()
        except MissingAPIKeyError as exc:
            st.error(f"❌ API Key Missing: {exc}")
        except APIAuthenticationError as exc:
            st.error(f"🔒 Authentication Rejected: {exc}")
        except RateLimitExceededError as exc:
            st.error(f"⏳ Daily Free Quota Exceeded (100 hits/day): {exc}")
        except APIConnectionError as exc:
            st.error(f"📡 Network Connection Failure: {exc}")
        except Exception as exc:
            st.error(f"❌ Ingestion Error: {exc}")


# ------------------------------------------------------------------------------
# DATA ACCESS FUNCTIONS
# ------------------------------------------------------------------------------
def get_teams_list() -> list:
    """Fetch distinct team names for dropdown filtering."""
    try:
        with db_manager.get_connection() as conn:
            cur = conn.cursor()
            rows = cur.execute("SELECT team_name FROM teams ORDER BY team_name ASC").fetchall()
            return [r[0] for r in rows]
    except Exception:
        return []


def get_filtered_matches(format_filter: str, status_filter: str, team_filter: str) -> list:
    """Fetch matches matching selected criteria."""
    try:
        with db_manager.get_connection() as conn:
            cur = conn.cursor()
            query = """
                SELECT
                    m.match_id,
                    m.external_id,
                    m.match_desc,
                    m.match_format,
                    m.match_date,
                    m.match_status,
                    m.source,
                    m.created_at,
                    t1.team_name AS team1,
                    t1.short_name AS team1_code,
                    t2.team_name AS team2,
                    t2.short_name AS team2_code,
                    tw.team_name AS toss_winner,
                    m.toss_decision,
                    twin.team_name AS winner,
                    m.win_margin,
                    m.win_type,
                    v.venue_name,
                    v.city,
                    v.country AS venue_country
                FROM matches m
                JOIN teams t1 ON m.team1_id = t1.team_id
                JOIN teams t2 ON m.team2_id = t2.team_id
                LEFT JOIN teams tw ON m.toss_winner_id = tw.team_id
                LEFT JOIN teams twin ON m.winning_team_id = twin.team_id
                JOIN venues v ON m.venue_id = v.venue_id
                WHERE 1=1
            """
            params = []
            if format_filter != "All Formats":
                query += " AND m.match_format = ?"
                params.append(format_filter)
            if status_filter != "All Statuses":
                query += " AND m.match_status = ?"
                params.append(status_filter)
            if team_filter != "All Teams":
                query += " AND (t1.team_name = ? OR t2.team_name = ?)"
                params.extend([team_filter, team_filter])

            query += " ORDER BY m.match_date DESC, m.match_id DESC;"
            rows = cur.execute(query, tuple(params)).fetchall()
            return [dict(r) for r in rows]
    except Exception as exc:
        st.error(f"Error querying matches: {exc}")
        return []


def get_innings_scorecards(match_id: int) -> dict:
    """Fetch batting and bowling scorecards for a specific match."""
    try:
        with db_manager.get_connection() as conn:
            # Innings summary
            df_innings = pd.read_sql_query(
                """
                SELECT
                    i.innings_id,
                    i.innings_number,
                    bt.team_name AS batting_team,
                    bl.team_name AS bowling_team,
                    i.total_runs,
                    i.total_wickets,
                    i.overs_completed
                FROM innings i
                JOIN teams bt ON i.batting_team_id = bt.team_id
                JOIN teams bl ON i.bowling_team_id = bl.team_id
                WHERE i.match_id = ?
                ORDER BY i.innings_number ASC;
                """,
                conn,
                params=(match_id,),
            )

            scorecards = {}
            for _, inn in df_innings.iterrows():
                inn_id = inn["innings_id"]
                # Batting performances
                df_batting = pd.read_sql_query(
                    """
                    SELECT
                        bp.batting_position AS [Pos],
                        p.full_name AS [Batter],
                        bp.runs_scored AS [Runs],
                        bp.balls_faced AS [Balls],
                        bp.fours AS [4s],
                        bp.sixes AS [6s],
                        ROUND((bp.runs_scored * 100.0) / NULLIF(bp.balls_faced, 0), 2) AS [SR],
                        bp.dismissal_type AS [Dismissal]
                    FROM batting_performances bp
                    JOIN players p ON bp.player_id = p.player_id
                    WHERE bp.innings_id = ?
                    ORDER BY bp.batting_position ASC;
                    """,
                    conn,
                    params=(inn_id,),
                )

                # Bowling performances
                df_bowling = pd.read_sql_query(
                    """
                    SELECT
                        p.full_name AS [Bowler],
                        ((bow.balls_bowled / 6) || '.' || (bow.balls_bowled % 6)) AS [Overs],
                        bow.maidens AS [Mdn],
                        bow.runs_conceded AS [Runs],
                        bow.wickets_taken AS [Wkts],
                        ROUND((bow.runs_conceded * 6.0) / NULLIF(bow.balls_bowled, 0), 2) AS [Econ]
                    FROM bowling_performances bow
                    JOIN players p ON bow.player_id = p.player_id
                    WHERE bow.innings_id = ?
                    ORDER BY bow.wickets_taken DESC, Econ ASC;
                    """,
                    conn,
                    params=(inn_id,),
                )

                scorecards[inn_id] = {
                    "meta": inn,
                    "batting": df_batting,
                    "bowling": df_bowling,
                }
            return scorecards
    except Exception as exc:
        st.error(f"Error loading scorecard: {exc}")
        return {}


# ------------------------------------------------------------------------------
# FILTER BAR
# ------------------------------------------------------------------------------
teams = get_teams_list()

st.markdown(
    f"""
    <div style="background: {COLOR_PANEL_DARK}; border: 1px solid {COLOR_BORDER}; border-radius: 10px; padding: 0.85rem 1.25rem; margin-bottom: 1.5rem;">
        <div style="font-size: 0.75rem; font-weight: 700; color: {COLOR_TEXT_SECONDARY}; text-transform: uppercase; margin-bottom: 0.5rem;">
            🔍 Filter Matches
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

f_col1, f_col2, f_col3 = st.columns(3)
with f_col1:
    sel_format = st.selectbox("Cricket Format", ["All Formats", "Test", "ODI", "T20I"], index=0)
with f_col2:
    sel_status = st.selectbox("Match Status", ["All Statuses", "Completed", "Scheduled", "In Progress", "Abandoned"], index=0)
with f_col3:
    sel_team = st.selectbox("Participating Team", ["All Teams"] + teams, index=0)


# ------------------------------------------------------------------------------
# MATCHES FEED & SCORECARD DRAWER
# ------------------------------------------------------------------------------
matches = get_filtered_matches(sel_format, sel_status, sel_team)

st.markdown(
    f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin: 1.25rem 0 0.75rem 0;">
        <h3 style="margin: 0; font-size: 1.15rem; color: {COLOR_TEXT_PRIMARY};">
            Showing {len(matches)} Matches
        </h3>
    </div>
    """,
    unsafe_allow_html=True,
)

if not matches:
    st.markdown(
        f"""
        <div class="cric-card" style="text-align: center; padding: 3rem 1rem;">
            <span style="font-size: 2.5rem;">🏏</span>
            <h4 style="margin: 0.75rem 0 0.3rem 0; color: {COLOR_TEXT_PRIMARY};">No Matches Found</h4>
            <p style="color: {COLOR_TEXT_SECONDARY}; font-size: 0.9rem;">
                No fixtures matched your selected filters ({sel_format}, {sel_status}, {sel_team}).
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    for match in matches:
        m_id = match["match_id"]
        fmt_badge = "lime" if match["match_format"] == "T20I" else ("green" if match["match_format"] == "ODI" else "amber")
        margin_str = f"by {match['win_margin']} {match['win_type']}" if match["win_margin"] else ""
        toss_str = f"{match['toss_winner']} won toss & elected to {match['toss_decision']}" if match["toss_winner"] else "Toss info pending"
        is_api = (match.get("source") == "API")
        created_ts = match.get("created_at") or "Unknown"
        if is_api:
            source_badge = '<span class="cric-badge cric-badge-lime" style="font-size: 0.72rem; margin-left: 0.4rem;">📡 API Feed</span>'
            provenance_label = f"<span style='color: {COLOR_ACCENT_LIME}; font-size: 0.78rem; margin-left: 0.5rem;'>🕒 Synced: {created_ts} UTC (~30-60s delay)</span>"
        else:
            source_badge = '<span class="cric-badge cric-badge-amber" style="font-size: 0.72rem; margin-left: 0.4rem;">💾 LOCAL Demo</span>'
            provenance_label = f"<span style='color: {COLOR_TEXT_SECONDARY}; font-size: 0.78rem; margin-left: 0.5rem;'>💾 Static Sample Fixture</span>"

        # Match Card Container
        st.markdown(
            f"""
            <div class="match-card">
                <div class="match-header">
                    <div>
                        <span class="cric-badge cric-badge-{fmt_badge}">{match['match_format']}</span>
                        {source_badge}
                        <span style="font-weight: 700; font-size: 1.05rem; color: {COLOR_TEXT_PRIMARY}; margin-left: 0.5rem;">
                            {match['match_desc']}
                        </span>
                    </div>
                    <div style="font-size: 0.8rem; color: {COLOR_TEXT_SECONDARY};">
                        📅 {match['match_date']} • 📍 {match['venue_name']}, {match['city']} {provenance_label}
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
                    <div>
                        <div style="font-size: 1.1rem; font-weight: 800; color: {COLOR_TEXT_PRIMARY};">
                            {match['team1']} <span style="color: {COLOR_TEXT_SECONDARY}; font-weight: 400;">vs</span> {match['team2']}
                        </div>
                        <div style="font-size: 0.82rem; color: {COLOR_TEXT_SECONDARY}; margin-top: 0.2rem;">
                            🪙 {toss_str}
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <span class="cric-badge cric-badge-lime" style="font-size: 0.85rem; padding: 0.35rem 0.75rem;">
                            🏆 {match['winner']} {margin_str}
                        </span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Expandable Innings Scorecards
        with st.expander(f"📊 Detailed Innings Scorecard for {match['match_desc']}"):
            if is_api:
                sc_col1, sc_col2 = st.columns([3, 1])
                with sc_col2:
                    if st.button("🔄 Sync Innings Feed", key=f"btn_sync_sc_{m_id}", use_container_width=True):
                        if settings.api.offline_mode:
                            st.warning("⚠️ Scorecard API sync disabled: OFFLINE_MODE=True is active.")
                        else:
                            ext_id = match.get("external_id")
                            if not ext_id:
                                st.error("❌ Missing external API match ID for this fixture. Click '🔄 Sync Live Feed' above to refresh match IDs.")
                            else:
                                try:
                                    client = get_cricket_client()
                                    with st.spinner("Fetching live innings breakdown..."):
                                        raw_sc = client.get_match_scorecard(str(ext_id), force_refresh=True)
                                        parsed_sc = CricketDataParser.parse_scorecard(raw_sc)
                                        ingestion = IngestionService()
                                        ingestion.ingest_scorecard(m_id, parsed_sc)
                                    st.success("✅ Scorecard successfully synchronized!")
                                    st.rerun()
                                except Exception as exc:
                                    st.error(f"❌ Scorecard Ingestion Error: {exc}")

            scorecards = get_innings_scorecards(m_id)
            if not scorecards:
                st.info("No detailed ball-by-ball scorecards recorded for this fixture.")
            else:
                for inn_id, inn_data in scorecards.items():
                    meta = inn_data["meta"]
                    run_rate = round(meta["total_runs"] / meta["overs_completed"], 2) if meta["overs_completed"] > 0 else 0.0

                    st.markdown(
                        f"""
                        <div style="background: {COLOR_PANEL_DARK}; border: 1px solid {COLOR_BORDER}; border-radius: 8px; padding: 0.6rem 1rem; margin: 0.75rem 0; display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <span style="color: {COLOR_ACCENT_LIME}; font-weight: 800; font-size: 1rem;">
                                    Innings {meta['innings_number']}: {meta['batting_team']}
                                </span>
                            </div>
                            <div style="font-family: 'JetBrains Mono', monospace; font-size: 1rem; font-weight: 700; color: {COLOR_TEXT_PRIMARY};">
                                {meta['total_runs']} / {meta['total_wickets']} <span style="font-size: 0.85rem; color: {COLOR_TEXT_SECONDARY};">({meta['overs_completed']} ov • RR {run_rate})</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    tab_bat, tab_bowl = st.tabs(["🏏 Batting Scorecard", "🎯 Bowling Figures"])
                    with tab_bat:
                        if not inn_data["batting"].empty:
                            st.dataframe(inn_data["batting"], use_container_width=True, hide_index=True)
                        else:
                            st.caption("No individual batting records available for this innings.")

                    with tab_bowl:
                        if not inn_data["bowling"].empty:
                            st.dataframe(inn_data["bowling"], use_container_width=True, hide_index=True)
                        else:
                            st.caption("No individual bowling spells recorded for this innings.")

        st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

"""Top Players & Leaderboards Page for Cricbuzz LiveStats.

Provides format-specific batting and bowling leaderboards, player search,
career statistics, and individual player profile spotlights.
"""

import pandas as pd
import streamlit as st

from config import settings
from database.connection import db_manager
from utils.charts import create_bar_chart, create_scatter_plot
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
    render_kpi_card,
    render_offline_banner,
    render_sidebar_brand,
)

# ------------------------------------------------------------------------------
# PAGE CONFIGURATION
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title=f"Top Players | {settings.app.app_short_title}",
    page_icon="👑",
    layout="wide",
)

apply_custom_theme()
render_sidebar_brand()

render_header(
    title="Player Statistics & Leaderboards",
    subtitle="Comprehensive batting, bowling, and all-round statistics across cricket formats",
    icon="👑",
    badge_text="ATHLETE STATS",
    badge_variant="lime",
)

if settings.api.offline_mode:
    render_offline_banner()


# ------------------------------------------------------------------------------
# DATA ACCESS FUNCTIONS
# ------------------------------------------------------------------------------
def get_filter_options() -> tuple:
    """Fetch distinct countries and player names."""
    try:
        with db_manager.get_connection() as conn:
            cur = conn.cursor()
            countries = [r[0] for r in cur.execute("SELECT DISTINCT country FROM players ORDER BY country ASC").fetchall()]
            players = [r[0] for r in cur.execute("SELECT full_name FROM players WHERE is_active = 1 ORDER BY full_name ASC").fetchall()]
            return countries, players
    except Exception:
        return [], []


def get_batting_leaderboard(format_filter: str, country_filter: str, role_filter: str) -> pd.DataFrame:
    """Query top batting records."""
    try:
        with db_manager.get_connection() as conn:
            query = """
                SELECT
                    p.full_name AS [Player],
                    p.country AS [Country],
                    p.playing_role AS [Role],
                    m.match_format AS [Format],
                    COUNT(bp.perf_id) AS [Innings],
                    SUM(bp.runs_scored) AS [Runs],
                    MAX(bp.runs_scored) AS [HS],
                    ROUND(SUM(bp.runs_scored) * 1.0 / NULLIF(SUM(1 - bp.is_not_out), 0), 2) AS [Average],
                    ROUND(SUM(bp.runs_scored) * 100.0 / NULLIF(SUM(bp.balls_faced), 0), 2) AS [Strike Rate],
                    SUM(CASE WHEN bp.runs_scored >= 100 THEN 1 ELSE 0 END) AS [100s],
                    SUM(CASE WHEN bp.runs_scored >= 50 AND bp.runs_scored < 100 THEN 1 ELSE 0 END) AS [50s],
                    SUM(bp.fours) AS [4s],
                    SUM(bp.sixes) AS [6s]
                FROM batting_performances bp
                JOIN players p ON bp.player_id = p.player_id
                JOIN innings i ON bp.innings_id = i.innings_id
                JOIN matches m ON i.match_id = m.match_id
                WHERE 1=1
            """
            params = []
            if format_filter != "All Formats":
                query += " AND m.match_format = ?"
                params.append(format_filter)
            if country_filter != "All Countries":
                query += " AND p.country = ?"
                params.append(country_filter)
            if role_filter != "All Roles":
                query += " AND p.playing_role = ?"
                params.append(role_filter)

            query += " GROUP BY p.player_id, p.full_name, p.country, p.playing_role, m.match_format ORDER BY Runs DESC, Average DESC;"
            return pd.read_sql_query(query, conn, params=params)
    except Exception as exc:
        st.error(f"Error loading batting leaderboard: {exc}")
        return pd.DataFrame()


def get_bowling_leaderboard(format_filter: str, country_filter: str) -> pd.DataFrame:
    """Query top bowling records."""
    try:
        with db_manager.get_connection() as conn:
            query = """
                SELECT
                    p.full_name AS [Player],
                    p.country AS [Country],
                    p.playing_role AS [Role],
                    m.match_format AS [Format],
                    ((SUM(bow.balls_bowled) / 6) || '.' || (SUM(bow.balls_bowled) % 6)) AS [Overs],
                    SUM(bow.maidens) AS [Maidens],
                    SUM(bow.runs_conceded) AS [Runs Conceded],
                    SUM(bow.wickets_taken) AS [Wickets],
                    ROUND((SUM(bow.runs_conceded) * 6.0) / NULLIF(SUM(bow.balls_bowled), 0), 2) AS [Economy],
                    ROUND(SUM(bow.runs_conceded) * 1.0 / NULLIF(SUM(bow.wickets_taken), 0), 2) AS [Bowling Avg]
                FROM bowling_performances bow
                JOIN players p ON bow.player_id = p.player_id
                JOIN innings i ON bow.innings_id = i.innings_id
                JOIN matches m ON i.match_id = m.match_id
                WHERE 1=1
            """
            params = []
            if format_filter != "All Formats":
                query += " AND m.match_format = ?"
                params.append(format_filter)
            if country_filter != "All Countries":
                query += " AND p.country = ?"
                params.append(country_filter)

            query += " GROUP BY p.player_id, p.full_name, p.country, p.playing_role, m.match_format ORDER BY Wickets DESC, Economy ASC;"
            return pd.read_sql_query(query, conn, params=params)
    except Exception as exc:
        st.error(f"Error loading bowling leaderboard: {exc}")
        return pd.DataFrame()


def get_player_profile(player_name: str) -> dict:
    """Fetch complete career breakdown for a selected player."""
    try:
        with db_manager.get_connection() as conn:
            cur = conn.cursor()
            p_row = cur.execute(
                """
                SELECT player_id, full_name, country, playing_role, batting_style, bowling_style, source
                FROM players WHERE full_name = ?;
                """,
                (player_name,),
            ).fetchone()
            if not p_row:
                return {}
            player = dict(p_row)

            df_batting = pd.read_sql_query(
                """
                SELECT
                    m.match_format AS [Format],
                    COUNT(bp.perf_id) AS [Innings],
                    SUM(bp.runs_scored) AS [Runs],
                    MAX(bp.runs_scored) AS [HS],
                    ROUND(SUM(bp.runs_scored) * 1.0 / NULLIF(SUM(1 - bp.is_not_out), 0), 2) AS [Average],
                    ROUND(SUM(bp.runs_scored) * 100.0 / NULLIF(SUM(bp.balls_faced), 0), 2) AS [SR],
                    SUM(CASE WHEN bp.runs_scored >= 100 THEN 1 ELSE 0 END) AS [100s],
                    SUM(CASE WHEN bp.runs_scored >= 50 AND bp.runs_scored < 100 THEN 1 ELSE 0 END) AS [50s]
                FROM batting_performances bp
                JOIN innings i ON bp.innings_id = i.innings_id
                JOIN matches m ON i.match_id = m.match_id
                WHERE bp.player_id = ?
                GROUP BY m.match_format;
                """,
                conn,
                params=(player["player_id"],),
            )

            df_bowling = pd.read_sql_query(
                """
                SELECT
                    m.match_format AS [Format],
                    ((SUM(bow.balls_bowled) / 6) || '.' || (SUM(bow.balls_bowled) % 6)) AS [Overs],
                    SUM(bow.wickets_taken) AS [Wickets],
                    ROUND((SUM(bow.runs_conceded) * 6.0) / NULLIF(SUM(bow.balls_bowled), 0), 2) AS [Economy]
                FROM bowling_performances bow
                JOIN innings i ON bow.innings_id = i.innings_id
                JOIN matches m ON i.match_id = m.match_id
                WHERE bow.player_id = ?
                GROUP BY m.match_format;
                """,
                conn,
                params=(player["player_id"],),
            )

            return {"info": player, "batting": df_batting, "bowling": df_bowling}
    except Exception as exc:
        st.error(f"Error loading player profile: {exc}")
        return {}


# ------------------------------------------------------------------------------
# FILTERS BAR
# ------------------------------------------------------------------------------
countries, all_players = get_filter_options()

f_col1, f_col2, f_col3 = st.columns(3)
with f_col1:
    sel_format = st.selectbox("Cricket Format", ["All Formats", "Test", "ODI", "T20I"], index=0)
with f_col2:
    sel_country = st.selectbox("Country / National Squad", ["All Countries"] + countries, index=0)
with f_col3:
    sel_role = st.selectbox("Playing Role", ["All Roles", "Batter", "Bowler", "All-rounder", "Wicket-keeper"], index=0)

st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)


# ------------------------------------------------------------------------------
# MAIN LEADERBOARDS TABS
# ------------------------------------------------------------------------------
tab_bat, tab_bowl, tab_profile = st.tabs(["🏏 Top Batsmen", "🎯 Top Bowlers", "👤 Player Spotlight Profile"])

# -----------------
# TAB 1: BATTING
# -----------------
with tab_bat:
    df_bat = get_batting_leaderboard(sel_format, sel_country, sel_role)
    if df_bat.empty:
        st.info("No batting records found matching the selected filters.")
    else:
        # Chart top 8 run scorers
        top_batters = df_bat.head(8)
        fig_bat = create_bar_chart(
            top_batters,
            x_col="Player",
            y_col="Runs",
            title=f"Top Run Scorers ({sel_format})",
            color_col="Format" if sel_format == "All Formats" else None,
        )
        st.plotly_chart(fig_bat, use_container_width=True)

        st.markdown(
            f"""
            <div style="font-weight: 700; font-size: 0.95rem; color: {COLOR_TEXT_PRIMARY}; margin: 0.75rem 0 0.5rem 0;">
                Complete Batting Leaderboard
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.dataframe(df_bat, use_container_width=True, hide_index=True)

# -----------------
# TAB 2: BOWLING
# -----------------
with tab_bowl:
    df_bowl = get_bowling_leaderboard(sel_format, sel_country)
    if df_bowl.empty:
        st.info("No bowling records found matching the selected filters.")
    else:
        top_bowlers = df_bowl.head(8)
        fig_bowl = create_bar_chart(
            top_bowlers,
            x_col="Player",
            y_col="Wickets",
            title=f"Top Wicket Takers ({sel_format})",
            color_col="Format" if sel_format == "All Formats" else None,
        )
        st.plotly_chart(fig_bowl, use_container_width=True)

        st.markdown(
            f"""
            <div style="font-weight: 700; font-size: 0.95rem; color: {COLOR_TEXT_PRIMARY}; margin: 0.75rem 0 0.5rem 0;">
                Complete Bowling Leaderboard
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.dataframe(df_bowl, use_container_width=True, hide_index=True)

# -----------------
# TAB 3: SPOTLIGHT
# -----------------
with tab_profile:
    st.markdown(
        f"""
        <div style="font-weight: 700; font-size: 1rem; color: {COLOR_TEXT_PRIMARY}; margin-bottom: 0.5rem;">
            Select Athlete to Inspect Career Profile
        </div>
        """,
        unsafe_allow_html=True,
    )
    selected_player = st.selectbox("Athlete Name", all_players, index=0 if all_players else None)

    if selected_player:
        profile = get_player_profile(selected_player)
        if profile and profile.get("info"):
            info = profile["info"]
            st.markdown(
                f"""
                <div class="cric-card" style="margin-top: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                        <div>
                            <h3 style="margin: 0; font-size: 1.5rem; color: {COLOR_TEXT_PRIMARY};">{info['full_name']}</h3>
                            <div style="font-size: 0.9rem; color: {COLOR_ACCENT_LIME}; font-weight: 600; margin-top: 0.2rem;">
                                🌍 {info['country']} • {info['playing_role']}
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <span class="cric-badge cric-badge-lime">{info['source']} RECORD</span>
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-top: 1rem; border-top: 1px solid {COLOR_BORDER}; padding-top: 0.8rem;">
                        <div>
                            <span style="font-size: 0.75rem; color: {COLOR_TEXT_SECONDARY};">BATTING STYLE</span>
                            <div style="font-weight: 700; color: {COLOR_TEXT_PRIMARY};">{info['batting_style']}</div>
                        </div>
                        <div>
                            <span style="font-size: 0.75rem; color: {COLOR_TEXT_SECONDARY};">BOWLING STYLE</span>
                            <div style="font-weight: 700; color: {COLOR_TEXT_PRIMARY};">{info['bowling_style'] or 'None'}</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            p_col1, p_col2 = st.columns(2)
            with p_col1:
                st.markdown(f"<div style='font-weight: 700; color: {COLOR_TEXT_PRIMARY}; margin: 0.5rem 0;'>Career Batting by Format</div>", unsafe_allow_html=True)
                if not profile["batting"].empty:
                    st.dataframe(profile["batting"], use_container_width=True, hide_index=True)
                else:
                    st.caption("No batting records recorded.")

            with p_col2:
                st.markdown(f"<div style='font-weight: 700; color: {COLOR_TEXT_PRIMARY}; margin: 0.5rem 0;'>Career Bowling by Format</div>", unsafe_allow_html=True)
                if not profile["bowling"].empty:
                    st.dataframe(profile["bowling"], use_container_width=True, hide_index=True)
                else:
                    st.caption("No bowling spells recorded.")

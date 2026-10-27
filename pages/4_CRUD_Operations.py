"""CRUD Operations Page for Cricbuzz LiveStats.

Provides a safe, form-based interface for Create, Read, Update, and Delete
operations across Players, Venues, and Matches with transactional integrity,
domain validation, foreign-key dependency protection, and API source segregation.
"""

from datetime import date
import pandas as pd
import streamlit as st

from config import settings
from database.connection import db_manager
from services.crud_service import (
    CRUDError,
    CRUDService,
    DuplicateRecordError,
    ProtectedRecordError,
    ReadOnlyRecordError,
    RecordNotFoundError,
    ValidationError,
)
from utils.theme import (
    COLOR_ACCENT_GREEN,
    COLOR_ACCENT_LIME,
    COLOR_BORDER,
    COLOR_CARD_SURFACE,
    COLOR_ERROR,
    COLOR_PANEL_DARK,
    COLOR_SUCCESS,
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
    page_title=f"CRUD Operations | {settings.app.app_short_title}",
    page_icon="🛠️",
    layout="wide",
)

apply_custom_theme()
render_sidebar_brand()

render_header(
    title="CRUD Operations & Database Management",
    subtitle="Parameterized Create, Read, Update, and Delete with transactional validation and referential protection",
    icon="🛠️",
    badge_text="TRANSACTIONS ENABLED",
    badge_variant="green",
)

if settings.api.offline_mode:
    render_offline_banner()

crud_service = CRUDService()


# ------------------------------------------------------------------------------
# ENTITY TABS: PLAYERS, VENUES, MATCHES
# ------------------------------------------------------------------------------
tab_players, tab_venues, tab_matches = st.tabs(["🏏 Players Management", "🏟️ Venues Management", "🏆 Matches Management"])


# ==============================================================================
# TAB 1: PLAYERS CRUD
# ==============================================================================
with tab_players:
    p_sub_view, p_sub_create, p_sub_update, p_sub_delete = st.tabs(["🔍 View Players", "➕ Add New Player", "✏️ Edit Player", "🗑️ Delete Player"])

    # 1. VIEW PLAYERS
    with p_sub_view:
        search_query = st.text_input("Search players by name", "", key="p_search")
        role_filter = st.selectbox("Role Filter", ["All Roles", "Batter", "Bowler", "All-rounder", "Wicket-keeper"], key="p_role_filt")
        rf = None if role_filter == "All Roles" else role_filter
        players_list = crud_service.get_players(role=rf, search=search_query or None)
        df_p = pd.DataFrame(players_list)
        if not df_p.empty:
            st.dataframe(df_p, use_container_width=True, hide_index=True)
            st.caption(f"Showing {len(df_p)} athlete records.")
        else:
            st.info("No players found matching search criteria.")

    # 2. CREATE PLAYER
    with p_sub_create:
        st.markdown(f"<div style='font-weight: 700; color: {COLOR_TEXT_PRIMARY}; margin-bottom: 0.5rem;'>Register New Athlete</div>", unsafe_allow_html=True)
        teams = crud_service.get_teams()
        team_map = {t["team_name"]: t["team_id"] for t in teams}

        with st.form("create_player_form"):
            cp_col1, cp_col2 = st.columns(2)
            with cp_col1:
                p_name = st.text_input("Full Athlete Name *", placeholder="e.g. Yashasvi Jaiswal")
                p_country = st.text_input("Country *", placeholder="e.g. India")
                p_team = st.selectbox("National / League Team", list(team_map.keys()))
            with cp_col2:
                p_role = st.selectbox("Playing Role *", ["Batter", "Bowler", "All-rounder", "Wicket-keeper"])
                p_bat_style = st.selectbox("Batting Style *", ["Right-hand bat", "Left-hand bat"])
                p_bowl_style = st.selectbox(
                    "Bowling Style",
                    [
                        "None", "Right-arm fast", "Right-arm medium", "Right-arm offbreak", "Right-arm legbreak",
                        "Left-arm fast", "Left-arm medium", "Left-arm orthodox", "Slow left-arm chinaman",
                    ],
                )

            submit_create_p = st.form_submit_button("Create Player", type="primary")

            if submit_create_p:
                try:
                    new_id = crud_service.create_player({
                        "full_name": p_name,
                        "country": p_country,
                        "team_id": team_map.get(p_team),
                        "playing_role": p_role,
                        "batting_style": p_bat_style,
                        "bowling_style": None if p_bowl_style == "None" else p_bowl_style,
                    })
                    st.success(f"✅ Player '{p_name}' successfully created with ID {new_id}!")
                    st.rerun()
                except ValidationError as ve:
                    st.error(f"Validation Failed: {ve}")
                except DuplicateRecordError as de:
                    st.error(f"Duplicate Error: {de}")
                except Exception as e:
                    st.error(f"Creation Error: {e}")

    # 3. UPDATE PLAYER
    with p_sub_update:
        st.markdown(f"<div style='font-weight: 700; color: {COLOR_TEXT_PRIMARY}; margin-bottom: 0.5rem;'>Modify Athlete Information</div>", unsafe_allow_html=True)
        all_p = crud_service.get_players()
        p_dict = {f"{p['full_name']} (ID: {p['player_id']}, {p['country']})": p for p in all_p}

        if p_dict:
            sel_p_key = st.selectbox("Select Athlete to Edit", list(p_dict.keys()), key="p_edit_sel")
            target_p = p_dict[sel_p_key]

            with st.form("edit_player_form"):
                ep_col1, ep_col2 = st.columns(2)
                with ep_col1:
                    ep_name = st.text_input("Full Athlete Name", value=target_p["full_name"])
                    ep_country = st.text_input("Country", value=target_p["country"])
                    ep_is_active = st.checkbox("Is Active Athlete", value=bool(target_p["is_active"]))
                with ep_col2:
                    roles = ["Batter", "Bowler", "All-rounder", "Wicket-keeper"]
                    ep_role = st.selectbox("Playing Role", roles, index=roles.index(target_p["playing_role"]) if target_p["playing_role"] in roles else 0)
                    bat_styles = ["Right-hand bat", "Left-hand bat"]
                    ep_bat = st.selectbox("Batting Style", bat_styles, index=bat_styles.index(target_p["batting_style"]) if target_p["batting_style"] in bat_styles else 0)

                submit_edit_p = st.form_submit_button("Update Player", type="primary")
                if submit_edit_p:
                    try:
                        crud_service.update_player(target_p["player_id"], {
                            "full_name": ep_name,
                            "country": ep_country,
                            "playing_role": ep_role,
                            "batting_style": ep_bat,
                            "is_active": 1 if ep_is_active else 0,
                        })
                        st.success(f"✅ Player ID {target_p['player_id']} successfully updated!")
                        st.rerun()
                    except Exception as err:
                        st.error(f"Update Error: {err}")

    # 4. DELETE PLAYER
    with p_sub_delete:
        st.markdown(f"<div style='font-weight: 700; color: {COLOR_ERROR}; margin-bottom: 0.5rem;'>Athlete Deletion Safeguards</div>", unsafe_allow_html=True)
        if p_dict:
            del_p_key = st.selectbox("Select Athlete to Remove", list(p_dict.keys()), key="p_del_sel")
            del_target = p_dict[del_p_key]

            del_type = st.radio("Deletion Type", ["Soft Delete (Deactivate)", "Hard Delete (Permanent)"], index=0)
            confirm_del_p = st.checkbox(f"Confirm removal of {del_target['full_name']} (Source: {del_target['source']})")

            if st.button("Execute Deletion", type="primary" if del_type.startswith("Soft") else "secondary"):
                if not confirm_del_p:
                    st.warning("Please tick the confirmation checkbox to proceed.")
                else:
                    try:
                        if del_type.startswith("Soft"):
                            crud_service.soft_delete_player(del_target["player_id"])
                            st.success(f"✅ Player ID {del_target['player_id']} successfully deactivated.")
                        else:
                            crud_service.hard_delete_player(del_target["player_id"])
                            st.success(f"✅ Player ID {del_target['player_id']} permanently deleted.")
                        st.rerun()
                    except ReadOnlyRecordError as ro:
                        st.error(f"Read-Only Error: {ro}")
                    except ProtectedRecordError as pr:
                        st.error(f"Protected Dependency Error: {pr}")
                    except Exception as err:
                        st.error(f"Deletion Error: {err}")


# ==============================================================================
# TAB 2: VENUES CRUD
# ==============================================================================
with tab_venues:
    v_sub_view, v_sub_create, v_sub_delete = st.tabs(["🔍 View Venues", "➕ Add New Venue", "🗑️ Delete Venue"])

    with v_sub_view:
        venues_list = crud_service.get_venues()
        df_v = pd.DataFrame(venues_list)
        if not df_v.empty:
            st.dataframe(df_v, use_container_width=True, hide_index=True)
        else:
            st.info("No venues recorded.")

    with v_sub_create:
        with st.form("create_venue_form"):
            v_name = st.text_input("Venue / Stadium Name *", placeholder="e.g. Sydney Cricket Ground")
            v_city = st.text_input("City *", placeholder="e.g. Sydney")
            v_country = st.text_input("Country *", placeholder="e.g. Australia")
            v_cap = st.number_input("Seating Capacity", min_value=1000, max_value=200000, value=48000, step=1000)

            if st.form_submit_button("Register Venue", type="primary"):
                try:
                    vid = crud_service.create_venue({
                        "venue_name": v_name,
                        "city": v_city,
                        "country": v_country,
                        "capacity": int(v_cap),
                    })
                    st.success(f"✅ Venue '{v_name}' successfully added with ID {vid}!")
                    st.rerun()
                except Exception as err:
                    st.error(f"Venue Error: {err}")

    with v_sub_delete:
        v_dict = {f"{v['venue_name']} ({v['city']}, {v['country']})": v for v in venues_list}
        if v_dict:
            sel_v_del = st.selectbox("Select Venue to Delete", list(v_dict.keys()))
            target_v = v_dict[sel_v_del]
            confirm_v = st.checkbox(f"Confirm deletion of {target_v['venue_name']}")
            if st.button("Delete Venue"):
                if not confirm_v:
                    st.warning("Please confirm deletion.")
                else:
                    try:
                        crud_service.delete_venue(target_v["venue_id"])
                        st.success(f"✅ Venue {target_v['venue_name']} deleted.")
                        st.rerun()
                    except ProtectedRecordError as pe:
                        st.error(f"Cannot delete: Venue is referenced by existing matches ({pe})")
                    except Exception as err:
                        st.error(f"Deletion Error: {err}")


# ==============================================================================
# TAB 3: MATCHES CRUD
# ==============================================================================
with tab_matches:
    m_sub_view, m_sub_create, m_sub_delete = st.tabs(["🔍 View Matches", "➕ Schedule New Match", "🗑️ Delete Match"])

    with m_sub_view:
        m_list = crud_service.get_matches()
        df_m = pd.DataFrame(m_list)
        if not df_m.empty:
            st.dataframe(df_m, use_container_width=True, hide_index=True)
        else:
            st.info("No matches recorded.")

    with m_sub_create:
        teams = crud_service.get_teams()
        t_options = {t["team_name"]: t["team_id"] for t in teams}
        venues = crud_service.get_venues()
        v_options = {f"{v['venue_name']} ({v['city']})": v["venue_id"] for v in venues}

        with st.form("create_match_form"):
            m_desc = st.text_input("Match Description *", placeholder="e.g. IND vs AUS 4th Test - Melbourne")
            m_fmt = st.selectbox("Format *", ["Test", "ODI", "T20I", "T20"])
            m_date = st.date_input("Match Date *", value=date.today())

            m_col1, m_col2 = st.columns(2)
            with m_col1:
                team1_name = st.selectbox("Team 1 *", list(t_options.keys()), index=0)
            with m_col2:
                team2_name = st.selectbox("Team 2 *", list(t_options.keys()), index=1 if len(t_options) > 1 else 0)

            venue_name = st.selectbox("Stadium Venue *", list(v_options.keys()))
            m_status = st.selectbox("Match Status", ["Completed", "Live", "Upcoming", "Abandoned", "No Result", "Tied"])

            if st.form_submit_button("Schedule Match", type="primary"):
                try:
                    new_mid = crud_service.create_match({
                        "match_desc": m_desc,
                        "match_format": m_fmt,
                        "match_date": str(m_date),
                        "team1_id": t_options[team1_name],
                        "team2_id": t_options[team2_name],
                        "venue_id": v_options[venue_name],
                        "match_status": m_status,
                    })
                    st.success(f"✅ Match successfully created with ID {new_mid}!")
                    st.rerun()
                except ValidationError as ve:
                    st.error(f"Validation Error: {ve}")
                except Exception as err:
                    st.error(f"Match Creation Error: {err}")

    with m_sub_delete:
        if m_list:
            m_del_dict = {f"{m['match_desc']} ({m['match_date']}, ID: {m['match_id']})": m for m in m_list}
            sel_m_del = st.selectbox("Select Match to Delete", list(m_del_dict.keys()))
            del_m_target = m_del_dict[sel_m_del]
            force_cascade = st.checkbox("Force Cascade Delete (Also remove linked innings and scorecards)")
            confirm_m_del = st.checkbox(f"Confirm deletion of Match ID {del_m_target['match_id']}")

            if st.button("Delete Match Record"):
                if not confirm_m_del:
                    st.warning("Please tick confirmation checkbox.")
                else:
                    try:
                        crud_service.delete_match(del_m_target["match_id"], force=force_cascade)
                        st.success(f"✅ Match ID {del_m_target['match_id']} successfully deleted.")
                        st.rerun()
                    except ProtectedRecordError as pre:
                        st.error(f"Cannot delete match with existing scorecards. Tick 'Force Cascade Delete' to cascade. ({pre})")
                    except Exception as err:
                        st.error(f"Match Deletion Error: {err}")

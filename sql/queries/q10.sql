-- ==============================================================================
-- Query 10: Last 20 Completed Matches with Margins
-- Category: Intermediate
--
-- Business Purpose:
--   Retrieve recent match results with full contextual details including
--   competing teams, victorious team, victory margin, victory type, and venue.
--
-- SQL Concepts:
--   - Multiple JOINs against the same lookup table (teams as t1, t2, and tw)
--   - LEFT JOIN on winning_team_id to safely handle tied or no-result matches
--   - Filter on match_status = 'Completed'
--   - Order by match_date DESC with secondary match_id tie-breaker
--   - LIMIT 20 to restrict result volume
-- ==============================================================================

SELECT
    m.match_desc,
    t1.team_name AS team1_name,
    t2.team_name AS team2_name,
    COALESCE(tw.team_name, 'Tied / No Winner') AS winning_team_name,
    m.win_margin,
    m.win_type,
    v.venue_name,
    m.match_date
FROM matches m
JOIN teams t1 ON m.team1_id = t1.team_id
JOIN teams t2 ON m.team2_id = t2.team_id
LEFT JOIN teams tw ON m.winning_team_id = tw.team_id
JOIN venues v ON m.venue_id = v.venue_id
WHERE m.match_status = 'Completed'
ORDER BY m.match_date DESC, m.match_id DESC
LIMIT 20;

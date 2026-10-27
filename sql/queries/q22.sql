-- ==============================================================================
-- Query 22: Team Head-to-Head Analysis & Match Prediction
-- Category: Advanced
--
-- Business Purpose:
--   Produce head-to-head matchup matrices for bilateral rivalries with sufficient
--   recent history (>= 5 matches in the last 3 years).
--
-- SQL Concepts:
--   - Canonical pairing with CASE WHEN team1_id < team2_id to combine A vs B and B vs A
--   - Filtering by rolling 3-year date window: match_date >= DATE('now', '-3 years')
--   - Segmented victory tallies, average winning margins, and win percentages
--   - Minimum rivalry sample threshold: HAVING COUNT(m.match_id) >= 5
-- ==============================================================================

WITH canonical_matches AS (
    SELECT
        m.match_id,
        m.match_date,
        CASE WHEN m.team1_id < m.team2_id THEN m.team1_id ELSE m.team2_id END AS team_a_id,
        CASE WHEN m.team1_id < m.team2_id THEN m.team2_id ELSE m.team1_id END AS team_b_id,
        m.winning_team_id,
        m.win_margin,
        m.win_type
    FROM matches m
    WHERE m.match_status = 'Completed'
      AND m.match_date >= DATE('now', '-3 years')
)
SELECT
    ta.team_name AS team_a,
    tb.team_name AS team_b,
    COUNT(cm.match_id) AS total_matches,
    SUM(CASE WHEN cm.winning_team_id = ta.team_id THEN 1 ELSE 0 END) AS team_a_wins,
    SUM(CASE WHEN cm.winning_team_id = tb.team_id THEN 1 ELSE 0 END) AS team_b_wins,
    SUM(CASE WHEN cm.winning_team_id NOT IN (ta.team_id, tb.team_id) OR cm.winning_team_id IS NULL THEN 1 ELSE 0 END) AS ties_or_no_result,
    ROUND(
        AVG(CASE WHEN cm.winning_team_id = ta.team_id AND cm.win_margin IS NOT NULL THEN cm.win_margin END),
        1
    ) AS team_a_avg_margin,
    ROUND(
        AVG(CASE WHEN cm.winning_team_id = tb.team_id AND cm.win_margin IS NOT NULL THEN cm.win_margin END),
        1
    ) AS team_b_avg_margin,
    ROUND(
        SUM(CASE WHEN cm.winning_team_id = ta.team_id THEN 1.0 ELSE 0.0 END) * 100.0
        / COUNT(cm.match_id),
        2
    ) AS team_a_win_pct,
    ROUND(
        SUM(CASE WHEN cm.winning_team_id = tb.team_id THEN 1.0 ELSE 0.0 END) * 100.0
        / COUNT(cm.match_id),
        2
    ) AS team_b_win_pct
FROM canonical_matches cm
JOIN teams ta ON cm.team_a_id = ta.team_id
JOIN teams tb ON cm.team_b_id = tb.team_id
GROUP BY cm.team_a_id, cm.team_b_id, ta.team_name, tb.team_name
HAVING COUNT(cm.match_id) >= 5
ORDER BY total_matches DESC, team_a_win_pct DESC;

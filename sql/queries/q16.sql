-- ==============================================================================
-- Query 16: Yearly Batting Trends Since 2020
-- Category: Intermediate
--
-- Business Purpose:
--   Track annual scoring trajectories and batting strike rates for consistent
--   top-tier batsmen (minimum 5 matches played in that calendar year).
--
-- SQL Concepts:
--   - Date extraction using STRFTIME('%Y', match_date)
--   - Multi-column GROUP BY (player and year)
--   - Aggregation filter: HAVING COUNT(DISTINCT m.match_id) >= 5
--   - Weighted strike rate calculation: (total runs * 100.0) / total balls faced
--   - Safe division using NULLIF to prevent divide-by-zero
-- ==============================================================================

SELECT
    STRFTIME('%Y', m.match_date) AS match_year,
    p.full_name AS player_name,
    COUNT(DISTINCT m.match_id) AS matches_played,
    SUM(bp.runs_scored) AS total_runs,
    ROUND(AVG(bp.runs_scored), 2) AS avg_runs_per_match,
    ROUND(
        SUM(bp.runs_scored) * 100.0 / NULLIF(SUM(bp.balls_faced), 0),
        2
    ) AS strike_rate
FROM players p
JOIN batting_performances bp ON p.player_id = bp.player_id
JOIN innings i ON bp.innings_id = i.innings_id
JOIN matches m ON i.match_id = m.match_id
WHERE m.match_date >= '2020-01-01'
GROUP BY STRFTIME('%Y', m.match_date), p.player_id, p.full_name
HAVING COUNT(DISTINCT m.match_id) >= 5
ORDER BY match_year DESC, total_runs DESC, p.full_name ASC;

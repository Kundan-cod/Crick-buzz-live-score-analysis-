-- ==============================================================================
-- Query 11: Cross-Format Player Performance
-- Category: Intermediate
--
-- Business Purpose:
--   Evaluate multi-format cricketers by contrasting aggregate runs across
--   Test, ODI, and T20I formats, plus their career overall batting average.
--
-- SQL Concepts:
--   - Conditional aggregation using SUM(CASE WHEN ...)
--   - Safe batting average calculation (runs / dismissals) with NULLIF protection
--   - HAVING clause filtering for multi-format athletes (COUNT(DISTINCT format) >= 2)
--   - Inner joins across players, batting performances, innings, and matches
-- ==============================================================================

SELECT
    p.full_name AS player_name,
    SUM(CASE WHEN m.match_format = 'Test' THEN bp.runs_scored ELSE 0 END) AS test_runs,
    SUM(CASE WHEN m.match_format = 'ODI' THEN bp.runs_scored ELSE 0 END) AS odi_runs,
    SUM(CASE WHEN m.match_format IN ('T20I', 'T20') THEN bp.runs_scored ELSE 0 END) AS t20i_runs,
    SUM(bp.runs_scored) AS total_runs,
    ROUND(
        SUM(bp.runs_scored) * 1.0 / NULLIF(SUM(1 - bp.is_not_out), 0),
        2
    ) AS overall_batting_average
FROM players p
JOIN batting_performances bp ON p.player_id = bp.player_id
JOIN innings i ON bp.innings_id = i.innings_id
JOIN matches m ON i.match_id = m.match_id
GROUP BY p.player_id, p.full_name
HAVING COUNT(DISTINCT m.match_format) >= 2
ORDER BY total_runs DESC, overall_batting_average DESC, p.full_name ASC;

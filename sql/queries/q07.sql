-- ==============================================================================
-- Query 07: Highest Individual Score by Format
-- Category: Beginner
--
-- Business Purpose:
--   Highlight record individual batting performances across standard cricket
--   formats (Test, ODI, T20I).
--
-- SQL Concepts:
--   - Window function: ROW_NUMBER() OVER (PARTITION BY match_format ORDER BY runs_scored DESC)
--   - Multi-table INNER JOIN (players -> batting_performances -> innings -> matches)
--   - Deterministic tie-breaking on balls faced and performance ID
-- ==============================================================================

WITH ranked_scores AS (
    SELECT
        m.match_format,
        p.full_name AS player_name,
        bp.runs_scored AS highest_score,
        bp.balls_faced,
        bp.is_not_out,
        ROW_NUMBER() OVER (
            PARTITION BY m.match_format
            ORDER BY bp.runs_scored DESC, bp.balls_faced ASC, bp.perf_id ASC
        ) AS rnk
    FROM batting_performances bp
    JOIN players p ON bp.player_id = p.player_id
    JOIN innings i ON bp.innings_id = i.innings_id
    JOIN matches m ON i.match_id = m.match_id
)
SELECT
    match_format,
    player_name,
    highest_score,
    balls_faced,
    CASE WHEN is_not_out = 1 THEN 'Yes' ELSE 'No' END AS not_out
FROM ranked_scores
WHERE rnk = 1
ORDER BY match_format ASC;

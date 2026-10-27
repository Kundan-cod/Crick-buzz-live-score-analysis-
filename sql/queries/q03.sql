-- ==============================================================================
-- Query 03: Top 10 ODI Run Scorers
-- Category: Beginner
--
-- Business Purpose:
--   Identify the leading run-scorers in One Day Internationals (ODI).
--   Displays player name, aggregate runs, batting average, and century count.
--
-- SQL Concepts:
--   - Multi-table INNER JOIN: players -> batting_performances -> innings -> matches
--   - Filter on match_format = 'ODI'
--   - Aggregate metrics: SUM(runs_scored), COUNT centuries
--   - Proper batting average: total runs / total dismissals (not averaging averages)
--   - Safe division using NULLIF to prevent divide-by-zero for unbeaten batsmen
--   - Sorting by total runs DESC with limit of 10
-- ==============================================================================

SELECT
    p.full_name AS player_name,
    SUM(bp.runs_scored) AS total_runs,
    COUNT(bp.perf_id) AS innings_batted,
    SUM(CASE WHEN bp.runs_scored >= 100 THEN 1 ELSE 0 END) AS centuries,
    SUM(CASE WHEN bp.runs_scored >= 50 AND bp.runs_scored < 100 THEN 1 ELSE 0 END) AS half_centuries,
    ROUND(
        SUM(bp.runs_scored) * 1.0 / NULLIF(SUM(1 - bp.is_not_out), 0),
        2
    ) AS batting_average
FROM players p
JOIN batting_performances bp ON p.player_id = bp.player_id
JOIN innings i ON bp.innings_id = i.innings_id
JOIN matches m ON i.match_id = m.match_id
WHERE m.match_format = 'ODI'
GROUP BY p.player_id, p.full_name
ORDER BY total_runs DESC, batting_average DESC
LIMIT 10;

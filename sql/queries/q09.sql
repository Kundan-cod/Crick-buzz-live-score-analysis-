-- ==============================================================================
-- Query 09: All-rounders (> 1,000 Runs AND > 50 Wickets)
-- Category: Intermediate
--
-- Business Purpose:
--   Identify elite all-rounders who have achieved the benchmark double of
--   over 1,000 runs and over 50 wickets in their career for a format.
--
-- SQL Concepts:
--   - JOIN MULTIPLICATION PROTECTION: Pre-aggregating batting and bowling metrics
--     in separate CTEs before joining on player_id prevents Cartesian product inflation.
--   - Multi-metric filtering: total_runs > 1000 AND total_wickets > 50
--   - Clean presentation of dual-discipline athlete records
-- ==============================================================================

WITH player_batting AS (
    SELECT
        bp.player_id,
        m.match_format,
        SUM(bp.runs_scored) AS total_runs
    FROM batting_performances bp
    JOIN innings i ON bp.innings_id = i.innings_id
    JOIN matches m ON i.match_id = m.match_id
    GROUP BY bp.player_id, m.match_format
),
player_bowling AS (
    SELECT
        bow.player_id,
        m.match_format,
        SUM(bow.wickets_taken) AS total_wickets
    FROM bowling_performances bow
    JOIN innings i ON bow.innings_id = i.innings_id
    JOIN matches m ON i.match_id = m.match_id
    GROUP BY bow.player_id, m.match_format
)
SELECT
    p.full_name AS player_name,
    pb.total_runs,
    pbo.total_wickets,
    pb.match_format
FROM players p
JOIN player_batting pb ON p.player_id = pb.player_id
JOIN player_bowling pbo ON p.player_id = pbo.player_id AND pb.match_format = pbo.match_format
WHERE pb.total_runs > 1000
  AND pbo.total_wickets > 50
ORDER BY pb.total_runs DESC, pbo.total_wickets DESC, p.full_name ASC;

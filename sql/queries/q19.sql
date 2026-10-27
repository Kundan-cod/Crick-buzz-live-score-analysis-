-- ==============================================================================
-- Query 19: Batting Consistency (Standard Deviation of Runs)
-- Category: Advanced
--
-- Business Purpose:
--   Measure batting consistency by evaluating the standard deviation of innings scores
--   since 2022 among batsmen who faced >= 10 balls per innings. Lower standard deviation
--   indicates predictable, steady output rather than volatile boom-or-bust scoring.
--
-- SQL Concepts:
--   - Mathematical implementation of sample standard deviation in standard SQL / SQLite:
--     SQRT((SUM(x^2) - (SUM(x)^2 / N)) / (N - 1))
--   - Filter on sample quality: bp.balls_faced >= 10 and match_date >= '2022-01-01'
--   - HAVING COUNT(bp.perf_id) >= 2 to ensure degrees of freedom (N - 1 > 0)
--   - Deterministic sorting by stddev_runs ASC, avg_runs DESC
-- ==============================================================================

SELECT
    p.full_name AS player_name,
    COUNT(bp.perf_id) AS qualifying_innings,
    SUM(bp.runs_scored) AS total_runs,
    ROUND(AVG(bp.runs_scored), 2) AS avg_runs,
    ROUND(
        SQRT(
            (
                SUM(bp.runs_scored * bp.runs_scored)
                - (SUM(bp.runs_scored) * SUM(bp.runs_scored) * 1.0 / COUNT(bp.perf_id))
            )
            / NULLIF(COUNT(bp.perf_id) - 1, 0)
        ),
        2
    ) AS stddev_runs
FROM players p
JOIN batting_performances bp ON p.player_id = bp.player_id
JOIN innings i ON bp.innings_id = i.innings_id
JOIN matches m ON i.match_id = m.match_id
WHERE m.match_date >= '2022-01-01'
  AND bp.balls_faced >= 10
GROUP BY p.player_id, p.full_name
HAVING COUNT(bp.perf_id) >= 2
ORDER BY stddev_runs ASC, avg_runs DESC, player_name ASC;

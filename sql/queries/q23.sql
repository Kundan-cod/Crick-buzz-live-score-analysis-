-- ==============================================================================
-- Query 23: Recent Player Form and Momentum Analysis
-- Category: Advanced
--
-- Business Purpose:
--   Track short-term player momentum and form trajectory across each batsman's
--   most recent 10 innings, evaluating last-5 vs last-10 averages, 50+ milestones,
--   scoring volatility, and assigning an objective form tier.
--
-- SQL Concepts:
--   - Window function: ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY match_date DESC, perf_id DESC)
--   - Window filtering: WHERE innings_seq <= 10
--   - Segmented averages: last 5 vs last 10 innings using conditional aggregation
--   - Standard deviation calculation for recent volatility
--   - Categorical classification using CASE expressions (Excellent, Good, Average, Poor)
-- ==============================================================================

WITH recent_innings AS (
    SELECT
        p.player_id,
        p.full_name AS player_name,
        bp.perf_id,
        bp.runs_scored,
        bp.balls_faced,
        m.match_date,
        ROW_NUMBER() OVER (
            PARTITION BY p.player_id
            ORDER BY m.match_date DESC, bp.perf_id DESC
        ) AS innings_seq
    FROM batting_performances bp
    JOIN players p ON bp.player_id = p.player_id
    JOIN innings i ON bp.innings_id = i.innings_id
    JOIN matches m ON i.match_id = m.match_id
)
SELECT
    player_name,
    COUNT(perf_id) AS recent_innings_count,
    ROUND(AVG(CASE WHEN innings_seq <= 5 THEN runs_scored END), 2) AS last_5_avg_runs,
    ROUND(AVG(runs_scored), 2) AS last_10_avg_runs,
    ROUND(
        SUM(CASE WHEN innings_seq <= 5 THEN runs_scored ELSE 0 END) * 100.0
        / NULLIF(SUM(CASE WHEN innings_seq <= 5 THEN balls_faced ELSE 0 END), 0),
        2
    ) AS last_5_strike_rate,
    SUM(CASE WHEN runs_scored >= 50 THEN 1 ELSE 0 END) AS scores_50_plus,
    ROUND(
        SQRT(
            (
                SUM(runs_scored * runs_scored)
                - (SUM(runs_scored) * SUM(runs_scored) * 1.0 / COUNT(perf_id))
            )
            / NULLIF(COUNT(perf_id) - 1, 0)
        ),
        2
    ) AS recent_stddev,
    CASE
        WHEN AVG(CASE WHEN innings_seq <= 5 THEN runs_scored END) >= 50.0 THEN 'Excellent Form'
        WHEN AVG(CASE WHEN innings_seq <= 5 THEN runs_scored END) >= 35.0 THEN 'Good Form'
        WHEN AVG(CASE WHEN innings_seq <= 5 THEN runs_scored END) >= 20.0 THEN 'Average Form'
        ELSE 'Poor Form'
    END AS form_tier
FROM recent_innings
WHERE innings_seq <= 10
GROUP BY player_id, player_name
ORDER BY last_5_avg_runs DESC, player_name ASC;

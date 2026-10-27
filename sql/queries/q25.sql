-- ==============================================================================
-- Query 25: Quarterly Career Trajectory Time-Series Analysis
-- Category: Advanced
--
-- Business Purpose:
--   Perform longitudinal time-series tracking of batting performance across
--   calendar quarters, detecting quarter-on-quarter momentum, scoring shifts,
--   and overall career phase classification (Ascending, Stable, Declining).
--
-- SQL Concepts:
--   - Time-series quarterly partitioning: STRFTIME('%Y') || '-Q' || ((month + 2) / 3)
--   - Two-tier HAVING qualification: >= 3 matches/quarter AND >= 6 qualifying quarters
--   - Window function: LAG(avg_runs, 1) OVER (PARTITION BY player_id ORDER BY match_quarter)
--   - Trend categorization comparing current quarter metrics to previous quarter baseline
-- ==============================================================================

WITH quarterly_stats AS (
    SELECT
        p.player_id,
        p.full_name AS player_name,
        STRFTIME('%Y', m.match_date) || '-Q' || ((CAST(STRFTIME('%m', m.match_date) AS INTEGER) + 2) / 3) AS match_quarter,
        COUNT(DISTINCT m.match_id) AS matches_in_quarter,
        SUM(bp.runs_scored) AS total_runs,
        ROUND(AVG(bp.runs_scored), 2) AS avg_runs,
        ROUND(
            SUM(bp.runs_scored) * 100.0 / NULLIF(SUM(bp.balls_faced), 0),
            2
        ) AS strike_rate
    FROM players p
    JOIN batting_performances bp ON p.player_id = bp.player_id
    JOIN innings i ON bp.innings_id = i.innings_id
    JOIN matches m ON i.match_id = m.match_id
    GROUP BY p.player_id, p.full_name, match_quarter
    HAVING COUNT(DISTINCT m.match_id) >= 3
),
quarter_counts AS (
    SELECT
        player_id,
        COUNT(match_quarter) AS qualifying_quarters
    FROM quarterly_stats
    GROUP BY player_id
    HAVING COUNT(match_quarter) >= 6
),
quarter_with_lag AS (
    SELECT
        qs.player_name,
        qs.match_quarter,
        qs.matches_in_quarter,
        qs.total_runs,
        qs.avg_runs,
        qs.strike_rate,
        LAG(qs.avg_runs, 1) OVER (
            PARTITION BY qs.player_id
            ORDER BY qs.match_quarter
        ) AS prev_quarter_avg,
        LAG(qs.strike_rate, 1) OVER (
            PARTITION BY qs.player_id
            ORDER BY qs.match_quarter
        ) AS prev_quarter_sr
    FROM quarterly_stats qs
    JOIN quarter_counts qc ON qs.player_id = qc.player_id
)
SELECT
    player_name,
    match_quarter,
    matches_in_quarter,
    total_runs,
    avg_runs,
    strike_rate,
    prev_quarter_avg,
    CASE
        WHEN prev_quarter_avg IS NULL THEN 'Baseline'
        WHEN avg_runs > prev_quarter_avg + 5.0 THEN 'Improving'
        WHEN avg_runs < prev_quarter_avg - 5.0 THEN 'Declining'
        ELSE 'Stable'
    END AS quarterly_trend,
    CASE
        WHEN avg_runs >= 45.0 THEN 'Career Ascending'
        WHEN avg_runs <= 25.0 THEN 'Career Declining'
        ELSE 'Career Stable'
    END AS career_phase
FROM quarter_with_lag
ORDER BY player_name ASC, match_quarter ASC;

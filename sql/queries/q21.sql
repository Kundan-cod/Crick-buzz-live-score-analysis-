-- ==============================================================================
-- Query 21: Weighted Player Ranking System
-- Category: Advanced
--
-- STATUS: FORMULA-DEPENDENT COMPOSITE SCORE IS BLOCKED PENDING REVIEW
--
-- Governance Note:
--   Per Project Decision DEC-004 and internship governance rules, the proposed
--   bowling scoring formula:
--     Bowling Points = (wickets * 2) + ((50 - bowling_avg) * 0.5) + ((6 - economy) * 2)
--   is mathematically unstable (e.g., negative points when economy > 6.0, divide-by-zero
--   when wickets = 0).
--   The underlying metric calculation CTEs (batting, bowling, fielding) are fully
--   structured below, but the composite ranking formula is left clearly marked as
--   PENDING REVIEW until formally agreed upon.
-- ==============================================================================

WITH batting_metrics AS (
    SELECT
        bp.player_id,
        m.match_format,
        SUM(bp.runs_scored) AS runs_scored,
        ROUND(
            SUM(bp.runs_scored) * 1.0 / NULLIF(SUM(1 - bp.is_not_out), 0),
            2
        ) AS batting_average,
        ROUND(
            SUM(bp.runs_scored) * 100.0 / NULLIF(SUM(bp.balls_faced), 0),
            2
        ) AS strike_rate,
        ROUND(
            (SUM(bp.runs_scored) * 0.01)
            + (COALESCE(SUM(bp.runs_scored) * 1.0 / NULLIF(SUM(1 - bp.is_not_out), 0), 0) * 0.5)
            + (COALESCE(SUM(bp.runs_scored) * 100.0 / NULLIF(SUM(bp.balls_faced), 0), 0) * 0.3),
            2
        ) AS batting_points
    FROM batting_performances bp
    JOIN innings i ON bp.innings_id = i.innings_id
    JOIN matches m ON i.match_id = m.match_id
    GROUP BY bp.player_id, m.match_format
),
bowling_metrics AS (
    SELECT
        bow.player_id,
        m.match_format,
        SUM(bow.wickets_taken) AS wickets_taken,
        SUM(bow.balls_bowled) AS balls_bowled,
        SUM(bow.runs_conceded) AS runs_conceded,
        ROUND(
            SUM(bow.runs_conceded) * 1.0 / NULLIF(SUM(bow.wickets_taken), 0),
            2
        ) AS bowling_average,
        ROUND(
            (SUM(bow.runs_conceded) * 6.0) / NULLIF(SUM(bow.balls_bowled), 0),
            2
        ) AS economy_rate
    FROM bowling_performances bow
    JOIN innings i ON bow.innings_id = i.innings_id
    JOIN matches m ON i.match_id = m.match_id
    GROUP BY bow.player_id, m.match_format
),
fielding_metrics AS (
    SELECT
        fp.player_id,
        m.match_format,
        SUM(fp.catches) AS catches,
        SUM(fp.stumpings) AS stumpings,
        ((SUM(fp.catches) * 3) + (SUM(fp.stumpings) * 5)) AS fielding_points
    FROM fielding_performances fp
    JOIN innings i ON fp.innings_id = i.innings_id
    JOIN matches m ON i.match_id = m.match_id
    GROUP BY fp.player_id, m.match_format
)
SELECT
    p.full_name AS player_name,
    COALESCE(bm.match_format, bowm.match_format, fm.match_format) AS match_format,
    COALESCE(bm.runs_scored, 0) AS runs_scored,
    COALESCE(bm.batting_average, 0.0) AS batting_average,
    COALESCE(bm.strike_rate, 0.0) AS strike_rate,
    COALESCE(bm.batting_points, 0.0) AS batting_points,
    COALESCE(bowm.wickets_taken, 0) AS wickets_taken,
    bowm.bowling_average,
    COALESCE(bowm.economy_rate, 0.0) AS economy_rate,
    COALESCE(fm.catches, 0) AS catches,
    COALESCE(fm.stumpings, 0) AS stumpings,
    COALESCE(fm.fielding_points, 0) AS fielding_points,
    'PENDING REVIEW' AS composite_ranking_status
FROM players p
LEFT JOIN batting_metrics bm ON p.player_id = bm.player_id
LEFT JOIN bowling_metrics bowm ON p.player_id = bowm.player_id
                              AND bm.match_format = bowm.match_format
LEFT JOIN fielding_metrics fm ON p.player_id = fm.player_id
                             AND bm.match_format = fm.match_format
WHERE bm.match_format IS NOT NULL
ORDER BY bm.batting_points DESC, p.full_name ASC;

-- ==============================================================================
-- Cricbuzz LiveStats: Reusable Analytical Views
-- Designed for Sports Analytics, Dashboards & SQL Practice Queries
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. v_match_details
-- Denormalized projection joining teams, venues, and series for match views
-- ------------------------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_match_details AS
SELECT
    m.match_id,
    m.match_desc,
    m.match_format,
    m.match_date,
    m.match_status,
    m.series_id,
    s.series_name,
    m.venue_id,
    v.venue_name,
    v.city AS venue_city,
    v.country AS venue_country,
    v.capacity AS venue_capacity,
    m.team1_id,
    t1.team_name AS team1_name,
    t1.short_name AS team1_short,
    t1.country AS team1_country,
    m.team2_id,
    t2.team_name AS team2_name,
    t2.short_name AS team2_short,
    t2.country AS team2_country,
    m.toss_winner_id,
    tw.team_name AS toss_winner_name,
    m.toss_decision,
    m.winning_team_id,
    twon.team_name AS winning_team_name,
    m.win_margin,
    m.win_type,
    m.source
FROM matches m
JOIN teams t1 ON m.team1_id = t1.team_id
JOIN teams t2 ON m.team2_id = t2.team_id
JOIN venues v ON m.venue_id = v.venue_id
LEFT JOIN series s ON m.series_id = s.series_id
LEFT JOIN teams tw ON m.toss_winner_id = tw.team_id
LEFT JOIN teams twon ON m.winning_team_id = twon.team_id;

-- ------------------------------------------------------------------------------
-- 2. v_innings_summary
-- Summarizes innings with team names, run rates, and completion state
-- ------------------------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_innings_summary AS
SELECT
    i.innings_id,
    i.match_id,
    m.match_format,
    m.match_date,
    i.innings_number,
    i.batting_team_id,
    bt.team_name AS batting_team_name,
    bt.short_name AS batting_team_short,
    i.bowling_team_id,
    bl.team_name AS bowling_team_name,
    bl.short_name AS bowling_team_short,
    i.total_runs,
    i.total_wickets,
    i.overs_completed,
    i.is_declared,
    CASE
        WHEN i.overs_completed > 0 THEN ROUND(i.total_runs / i.overs_completed, 2)
        ELSE 0.0
    END AS run_rate
FROM innings i
JOIN matches m ON i.match_id = m.match_id
JOIN teams bt ON i.batting_team_id = bt.team_id
JOIN teams bl ON i.bowling_team_id = bl.team_id;

-- ------------------------------------------------------------------------------
-- 3. v_player_batting_by_format
-- Aggregates batting statistics per player per format
-- Never averages averages: computes total_runs / total_dismissals directly
-- ------------------------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_player_batting_by_format AS
SELECT
    p.player_id,
    p.full_name,
    p.country,
    p.playing_role,
    p.batting_style,
    m.match_format,
    COUNT(DISTINCT m.match_id) AS matches_played,
    COUNT(bp.perf_id) AS innings_batted,
    SUM(bp.runs_scored) AS total_runs,
    SUM(bp.balls_faced) AS total_balls_faced,
    SUM(bp.fours) AS total_fours,
    SUM(bp.sixes) AS total_sixes,
    MAX(bp.runs_scored) AS highest_score,
    SUM(CASE WHEN bp.runs_scored >= 100 THEN 1 ELSE 0 END) AS centuries,
    SUM(CASE WHEN bp.runs_scored >= 50 AND bp.runs_scored < 100 THEN 1 ELSE 0 END) AS fifties,
    SUM(CASE WHEN bp.is_not_out = 1 THEN 1 ELSE 0 END) AS not_outs,
    SUM(CASE WHEN bp.is_not_out = 0 THEN 1 ELSE 0 END) AS dismissals,
    ROUND(
        CAST(SUM(bp.runs_scored) AS REAL) /
        NULLIF(SUM(CASE WHEN bp.is_not_out = 0 THEN 1 ELSE 0 END), 0),
        2
    ) AS batting_average,
    ROUND(
        (CAST(SUM(bp.runs_scored) AS REAL) * 100.0) /
        NULLIF(SUM(bp.balls_faced), 0),
        2
    ) AS strike_rate
FROM players p
JOIN batting_performances bp ON p.player_id = bp.player_id
JOIN innings i ON bp.innings_id = i.innings_id
JOIN matches m ON i.match_id = m.match_id
GROUP BY p.player_id, p.full_name, p.country, p.playing_role, p.batting_style, m.match_format;

-- ------------------------------------------------------------------------------
-- 4. v_player_bowling_by_format
-- Aggregates bowling statistics per player per format
-- Computes true bowling average (runs_conceded / wickets_taken)
-- ------------------------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_player_bowling_by_format AS
SELECT
    p.player_id,
    p.full_name,
    p.country,
    p.playing_role,
    p.bowling_style,
    m.match_format,
    COUNT(DISTINCT m.match_id) AS matches_played,
    COUNT(bowl.bowl_id) AS innings_bowled,
    -- Total legal balls bowled
    SUM(
        CASE
            WHEN bowl.balls_bowled > 0 THEN bowl.balls_bowled
            ELSE CAST(bowl.overs_bowled AS INT) * 6 + CAST(ROUND((bowl.overs_bowled - CAST(bowl.overs_bowled AS INT)) * 10) AS INT)
        END
    ) AS total_balls_bowled,
    -- Cricket overs notation: completed overs + '.' + remaining balls (e.g. 10.4, not decimal 10.4)
    (
        SUM(
            CASE
                WHEN bowl.balls_bowled > 0 THEN bowl.balls_bowled
                ELSE CAST(bowl.overs_bowled AS INT) * 6 + CAST(ROUND((bowl.overs_bowled - CAST(bowl.overs_bowled AS INT)) * 10) AS INT)
            END
        ) / 6
    ) || '.' || (
        SUM(
            CASE
                WHEN bowl.balls_bowled > 0 THEN bowl.balls_bowled
                ELSE CAST(bowl.overs_bowled AS INT) * 6 + CAST(ROUND((bowl.overs_bowled - CAST(bowl.overs_bowled AS INT)) * 10) AS INT)
            END
        ) % 6
    ) AS total_overs,
    SUM(bowl.maidens) AS total_maidens,
    SUM(bowl.runs_conceded) AS total_runs_conceded,
    SUM(bowl.wickets_taken) AS total_wickets,
    SUM(CASE WHEN bowl.wickets_taken >= 4 AND bowl.wickets_taken < 5 THEN 1 ELSE 0 END) AS four_wickets,
    SUM(CASE WHEN bowl.wickets_taken >= 5 THEN 1 ELSE 0 END) AS five_wickets,
    ROUND(
        CAST(SUM(bowl.runs_conceded) AS REAL) /
        NULLIF(SUM(bowl.wickets_taken), 0),
        2
    ) AS bowling_average,
    -- True economy rate: (runs_conceded * 6.0) / total_balls_bowled
    ROUND(
        (CAST(SUM(bowl.runs_conceded) AS REAL) * 6.0) /
        NULLIF(
            SUM(
                CASE
                    WHEN bowl.balls_bowled > 0 THEN bowl.balls_bowled
                    ELSE CAST(bowl.overs_bowled AS INT) * 6 + CAST(ROUND((bowl.overs_bowled - CAST(bowl.overs_bowled AS INT)) * 10) AS INT)
                END
            ),
            0
        ),
        2
    ) AS economy_rate
FROM players p
JOIN bowling_performances bowl ON p.player_id = bowl.player_id
JOIN innings i ON bowl.innings_id = i.innings_id
JOIN matches m ON i.match_id = m.match_id
GROUP BY p.player_id, p.full_name, p.country, p.playing_role, p.bowling_style, m.match_format;

-- ------------------------------------------------------------------------------
-- 5. v_player_career_totals
-- Cross-format career totals combining batting and bowling
-- Pre-aggregated in isolated subqueries to prevent join multiplication / inflated stats
-- Supports Q9 (All-rounders with >1000 runs and >50 wickets)
-- ------------------------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_player_career_totals AS
SELECT
    p.player_id,
    p.full_name,
    p.country,
    p.playing_role,
    COALESCE(bat.career_runs, 0) AS career_runs,
    COALESCE(bat.career_innings_batted, 0) AS career_innings_batted,
    COALESCE(bat.career_centuries, 0) AS career_centuries,
    bat.career_batting_avg,
    COALESCE(bowl.career_wickets, 0) AS career_wickets,
    COALESCE(bowl.career_overs, '0.0') AS career_overs,
    bowl.career_bowling_avg,
    bowl.career_economy
FROM players p
LEFT JOIN (
    SELECT
        bp.player_id,
        SUM(bp.runs_scored) AS career_runs,
        COUNT(bp.perf_id) AS career_innings_batted,
        SUM(CASE WHEN bp.runs_scored >= 100 THEN 1 ELSE 0 END) AS career_centuries,
        ROUND(
            CAST(SUM(bp.runs_scored) AS REAL) /
            NULLIF(SUM(CASE WHEN bp.is_not_out = 0 THEN 1 ELSE 0 END), 0),
            2
        ) AS career_batting_avg
    FROM batting_performances bp
    GROUP BY bp.player_id
) bat ON p.player_id = bat.player_id
LEFT JOIN (
    SELECT
        b.player_id,
        SUM(b.wickets_taken) AS career_wickets,
        (
            SUM(
                CASE
                    WHEN b.balls_bowled > 0 THEN b.balls_bowled
                    ELSE CAST(b.overs_bowled AS INT) * 6 + CAST(ROUND((b.overs_bowled - CAST(b.overs_bowled AS INT)) * 10) AS INT)
                END
            ) / 6
        ) || '.' || (
            SUM(
                CASE
                    WHEN b.balls_bowled > 0 THEN b.balls_bowled
                    ELSE CAST(b.overs_bowled AS INT) * 6 + CAST(ROUND((b.overs_bowled - CAST(b.overs_bowled AS INT)) * 10) AS INT)
                END
            ) % 6
        ) AS career_overs,
        ROUND(
            CAST(SUM(b.runs_conceded) AS REAL) /
            NULLIF(SUM(b.wickets_taken), 0),
            2
        ) AS career_bowling_avg,
        ROUND(
            (CAST(SUM(b.runs_conceded) AS REAL) * 6.0) /
            NULLIF(
                SUM(
                    CASE
                        WHEN b.balls_bowled > 0 THEN b.balls_bowled
                        ELSE CAST(b.overs_bowled AS INT) * 6 + CAST(ROUND((b.overs_bowled - CAST(b.overs_bowled AS INT)) * 10) AS INT)
                    END
                ),
                0
            ),
            2
        ) AS career_economy
    FROM bowling_performances b
    GROUP BY b.player_id
) bowl ON p.player_id = bowl.player_id;

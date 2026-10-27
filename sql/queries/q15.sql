-- ==============================================================================
-- Query 15: Players in Close Matches (< 50 Runs OR < 5 Wickets)
-- Category: Intermediate
--
-- Business Purpose:
--   Identify clutch performers who excel under high-pressure scenarios, specifically
--   matches decided by narrow margins (< 50 runs or < 5 wickets).
--
-- SQL Concepts:
--   - Complex boolean filtering for competitive margin thresholds
--   - Distinct match counting to measure appearances in qualifying matches
--   - Conditional COUNT for team victory correlation (team won when player batted)
--   - Safe averages and percentage rate calculations
-- ==============================================================================

SELECT
    p.full_name AS player_name,
    COUNT(DISTINCT m.match_id) AS close_matches_batted,
    SUM(bp.runs_scored) AS total_runs,
    ROUND(AVG(bp.runs_scored), 2) AS avg_runs_per_close_match,
    COUNT(DISTINCT CASE WHEN m.winning_team_id = i.batting_team_id THEN m.match_id END) AS close_matches_won,
    ROUND(
        COUNT(DISTINCT CASE WHEN m.winning_team_id = i.batting_team_id THEN m.match_id END) * 100.0
        / COUNT(DISTINCT m.match_id),
        2
    ) AS win_pct_when_batted
FROM players p
JOIN batting_performances bp ON p.player_id = bp.player_id
JOIN innings i ON bp.innings_id = i.innings_id
JOIN matches m ON i.match_id = m.match_id
WHERE m.match_status = 'Completed'
  AND (
      (m.win_type = 'runs' AND m.win_margin < 50)
      OR
      (m.win_type = 'wickets' AND m.win_margin < 5)
  )
GROUP BY p.player_id, p.full_name
ORDER BY avg_runs_per_close_match DESC, close_matches_won DESC, p.full_name ASC;

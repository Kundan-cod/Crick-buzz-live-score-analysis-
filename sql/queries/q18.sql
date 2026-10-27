-- ==============================================================================
-- Query 18: Economical Limited-Overs Bowlers
-- Category: Advanced
--
-- Business Purpose:
--   Rank the most economical bowlers in white-ball cricket (ODI & T20 formats)
--   who have substantial sample size (>= 10 matches, averaging >= 2 overs/12 balls per match).
--
-- SQL Concepts:
--   - Filter on limited-overs formats (ODI, T20I, T20)
--   - Multi-metric HAVING thresholds: match frequency AND average overs workload
--   - True mathematical economy rate: (runs_conceded * 6.0) / balls_bowled
--   - Cricket over formatting: (balls / 6) || '.' || (balls % 6)
--   - Sorting by economy_rate ASC, total_wickets DESC
-- ==============================================================================

SELECT
    p.full_name AS bowler_name,
    COUNT(DISTINCT m.match_id) AS limited_overs_matches,
    (SUM(bow.balls_bowled) / 6) || '.' || (SUM(bow.balls_bowled) % 6) AS overs_bowled,
    SUM(bow.runs_conceded) AS runs_conceded,
    SUM(bow.wickets_taken) AS total_wickets,
    ROUND(
        (SUM(bow.runs_conceded) * 6.0) / NULLIF(SUM(bow.balls_bowled), 0),
        2
    ) AS economy_rate
FROM bowling_performances bow
JOIN players p ON bow.player_id = p.player_id
JOIN innings i ON bow.innings_id = i.innings_id
JOIN matches m ON i.match_id = m.match_id
WHERE m.match_format IN ('ODI', 'T20I', 'T20')
GROUP BY p.player_id, p.full_name
HAVING COUNT(DISTINCT m.match_id) >= 10
   AND (SUM(bow.balls_bowled) * 1.0 / COUNT(DISTINCT m.match_id)) >= 12
ORDER BY economy_rate ASC, total_wickets DESC, bowler_name ASC;

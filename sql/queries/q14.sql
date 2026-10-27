-- ==============================================================================
-- Query 14: Venue Bowling Analysis
-- Category: Intermediate
--
-- Business Purpose:
--   Evaluate venue-specific bowling proficiency for bowlers with substantial experience
--   (>= 3 matches at a venue) who bowl full spells (>= 4 overs / 24 balls per match).
--
-- SQL Concepts:
--   - Multi-table joins (players -> bowling_performances -> innings -> matches -> venues)
--   - Filter on spell workload: balls_bowled >= 24 (4 completed overs)
--   - HAVING filter on venue appearance frequency: COUNT(DISTINCT m.match_id) >= 3
--   - Cricket standard overs representation: (balls / 6) || '.' || (balls % 6)
--   - True weighted economy calculation: (runs_conceded * 6.0) / balls_bowled
-- ==============================================================================

SELECT
    p.full_name AS bowler_name,
    v.venue_name,
    v.city,
    COUNT(DISTINCT m.match_id) AS matches_played,
    (SUM(bow.balls_bowled) / 6) || '.' || (SUM(bow.balls_bowled) % 6) AS overs_bowled,
    SUM(bow.wickets_taken) AS total_wickets,
    ROUND(
        (SUM(bow.runs_conceded) * 6.0) / NULLIF(SUM(bow.balls_bowled), 0),
        2
    ) AS economy_rate
FROM bowling_performances bow
JOIN players p ON bow.player_id = p.player_id
JOIN innings i ON bow.innings_id = i.innings_id
JOIN matches m ON i.match_id = m.match_id
JOIN venues v ON m.venue_id = v.venue_id
WHERE bow.balls_bowled >= 24
GROUP BY p.player_id, p.full_name, v.venue_id, v.venue_name, v.city
HAVING COUNT(DISTINCT m.match_id) >= 3
ORDER BY total_wickets DESC, economy_rate ASC, bowler_name ASC;

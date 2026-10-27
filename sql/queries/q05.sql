-- ==============================================================================
-- Query 05: Team Wins Summary
-- Category: Beginner
--
-- Business Purpose:
--   Rank international teams by total matches won across all completed fixtures,
--   transparently accounting for all teams (including those with 0 wins).
--
-- SQL Concepts:
--   - LEFT OUTER JOIN to include teams that have zero registered victories
--   - Filtering on completed match status in JOIN predicate (preventing filter drop)
--   - Aggregate COUNT on the joined primary key (COUNT(m.match_id), not COUNT(*))
--   - Deterministic sorting by total_wins DESC, team_name ASC
-- ==============================================================================

SELECT
    t.team_name,
    COUNT(m.match_id) AS total_wins
FROM teams t
LEFT JOIN matches m ON t.team_id = m.winning_team_id
                    AND m.match_status = 'Completed'
GROUP BY t.team_id, t.team_name
ORDER BY total_wins DESC, t.team_name ASC;

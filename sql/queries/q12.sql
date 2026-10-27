-- ==============================================================================
-- Query 12: Home vs. Away Performance
-- Category: Intermediate
--
-- Business Purpose:
--   Assess team strength and home ground advantage by segmenting victories
--   into home matches (venue country equals team country) versus away/neutral fixtures.
--
-- SQL Concepts:
--   - Unpivoting team participation using OR in JOIN predicate (team1_id OR team2_id)
--   - Conditional logic (CASE WHEN v.country = t.country) to determine match context
--   - Conditional COUNT aggregations for segmented home/away victory tallies
--   - Deterministic sorting by total_wins DESC, home_wins DESC
-- ==============================================================================

WITH team_matches AS (
    SELECT
        t.team_id,
        t.team_name,
        t.country AS team_country,
        m.match_id,
        m.winning_team_id,
        v.country AS venue_country,
        CASE WHEN v.country = t.country THEN 'Home' ELSE 'Away' END AS condition
    FROM teams t
    JOIN matches m ON (t.team_id = m.team1_id OR t.team_id = m.team2_id)
    JOIN venues v ON m.venue_id = v.venue_id
    WHERE m.match_status = 'Completed'
)
SELECT
    team_name,
    COUNT(CASE WHEN condition = 'Home' THEN 1 END) AS home_matches,
    COUNT(CASE WHEN condition = 'Home' AND winning_team_id = team_id THEN 1 END) AS home_wins,
    COUNT(CASE WHEN condition = 'Away' THEN 1 END) AS away_matches,
    COUNT(CASE WHEN condition = 'Away' AND winning_team_id = team_id THEN 1 END) AS away_wins,
    COUNT(CASE WHEN winning_team_id = team_id THEN 1 END) AS total_wins
FROM team_matches
GROUP BY team_id, team_name
ORDER BY total_wins DESC, home_wins DESC, team_name ASC;

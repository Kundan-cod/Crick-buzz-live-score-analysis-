-- ==============================================================================
-- Query 02: Matches in the Last 30 Days
-- Category: Beginner
--
-- Business Purpose:
--   Retrieve recently completed or ongoing matches played within the last 30 days.
--   Provides fans, commentators, and dashboard widgets with recent match activity,
--   including the match description, competing teams, host city, and match date.
--
-- SQL Concepts:
--   - Multi-table INNER JOINs connecting matches to teams (twice: for team1 and team2)
--     and venues (to resolve venue city).
--   - Date arithmetic using SQLite's DATE('now', '-30 days').
--   - Boundary filtering:
--       * m.match_date >= DATE('now', '-30 days'): includes matches played exactly 30 days ago
--       * m.match_date <= DATE('now'): strictly excludes future-dated fixtures
--   - Index optimization leveraging idx_matches_date on matches(match_date).
--   - Ordering by match_date DESC for reverse-chronological presentation.
-- ==============================================================================

SELECT
    m.match_desc,
    t1.team_name AS team1_name,
    t2.team_name AS team2_name,
    v.city AS venue_city,
    m.match_date
FROM matches m
JOIN teams t1 ON m.team1_id = t1.team_id
JOIN teams t2 ON m.team2_id = t2.team_id
JOIN venues v ON m.venue_id = v.venue_id
WHERE m.match_date >= DATE('now', '-30 days')
  AND m.match_date <= DATE('now')
ORDER BY m.match_date DESC;

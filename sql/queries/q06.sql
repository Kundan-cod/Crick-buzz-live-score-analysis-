-- ==============================================================================
-- Query 06: Player Counts by Playing Role
-- Category: Beginner
--
-- Business Purpose:
--   Understand the squad composition and talent distribution across core
--   cricketing roles (Batter, Bowler, All-rounder, Wicket-keeper).
--
-- SQL Concepts:
--   - Single-table aggregation using GROUP BY
--   - Aggregate COUNT(player_id)
--   - Alphabetical tie-breaking for equal counts
-- ==============================================================================

SELECT
    playing_role,
    COUNT(player_id) AS player_count
FROM players
GROUP BY playing_role
ORDER BY player_count DESC, playing_role ASC;

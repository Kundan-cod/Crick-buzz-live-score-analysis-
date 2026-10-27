-- ==============================================================================
-- Query 01: India Players (Full Name, Playing Role, Batting Style, Bowling Style)
-- Category: Beginner
--
-- Business Purpose:
--   Retrieve the squad roster of all players representing India.
--   Provides coaches, commentators, and fans with individual athlete profiles,
--   including their playing role, batting handedness, and bowling classification.
--
-- SQL Concepts:
--   - Column projection via SELECT
--   - Row filtering via WHERE clause leveraging index idx_players_country
--   - Handling NULL values gracefully using COALESCE()
--   - Deterministic alphabetical sorting using ORDER BY
-- ==============================================================================

SELECT
    p.full_name,
    p.playing_role,
    p.batting_style,
    COALESCE(p.bowling_style, 'None') AS bowling_style
FROM players p
WHERE p.country = 'India'
ORDER BY p.full_name ASC;

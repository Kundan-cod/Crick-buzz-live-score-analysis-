-- ==============================================================================
-- Query 20: Matches and Batting Averages by Format
-- Category: Advanced
--
-- Business Purpose:
--   Generate a comprehensive format-by-format profile (Test, ODI, T20) detailing
--   match appearances and format-specific batting averages for veteran players (>= 20 total matches).
--
-- SQL Concepts:
--   - Pivot-style conditional aggregations for format match counts and averages
--   - Accurate dismissal counting: SUM(CASE WHEN format THEN (1 - is_not_out) END)
--   - Safe division with NULLIF to prevent divide-by-zero for unbeaten records
--   - High appearance threshold: HAVING COUNT(DISTINCT m.match_id) >= 20
-- ==============================================================================

SELECT
    p.full_name AS player_name,
    COUNT(DISTINCT CASE WHEN m.match_format = 'Test' THEN m.match_id END) AS test_matches,
    ROUND(
        SUM(CASE WHEN m.match_format = 'Test' THEN bp.runs_scored ELSE 0 END) * 1.0
        / NULLIF(SUM(CASE WHEN m.match_format = 'Test' THEN (1 - bp.is_not_out) ELSE 0 END), 0),
        2
    ) AS test_batting_avg,
    COUNT(DISTINCT CASE WHEN m.match_format = 'ODI' THEN m.match_id END) AS odi_matches,
    ROUND(
        SUM(CASE WHEN m.match_format = 'ODI' THEN bp.runs_scored ELSE 0 END) * 1.0
        / NULLIF(SUM(CASE WHEN m.match_format = 'ODI' THEN (1 - bp.is_not_out) ELSE 0 END), 0),
        2
    ) AS odi_batting_avg,
    COUNT(DISTINCT CASE WHEN m.match_format IN ('T20I', 'T20') THEN m.match_id END) AS t20_matches,
    ROUND(
        SUM(CASE WHEN m.match_format IN ('T20I', 'T20') THEN bp.runs_scored ELSE 0 END) * 1.0
        / NULLIF(SUM(CASE WHEN m.match_format IN ('T20I', 'T20') THEN (1 - bp.is_not_out) ELSE 0 END), 0),
        2
    ) AS t20_batting_avg,
    COUNT(DISTINCT m.match_id) AS total_matches
FROM players p
JOIN batting_performances bp ON p.player_id = bp.player_id
JOIN innings i ON bp.innings_id = i.innings_id
JOIN matches m ON i.match_id = m.match_id
GROUP BY p.player_id, p.full_name
HAVING COUNT(DISTINCT m.match_id) >= 20
ORDER BY total_matches DESC, p.full_name ASC;

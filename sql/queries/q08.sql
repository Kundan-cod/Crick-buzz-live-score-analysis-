-- ==============================================================================
-- Query 08: Series Started in 2024
-- Category: Beginner
--
-- Business Purpose:
--   Retrieve all international and domestic tournament series scheduled or launched
--   during the calendar year 2024.
--
-- SQL Concepts:
--   - Date extraction and range filtering (STRFTIME or BETWEEN)
--   - Single-table SELECT with projection
--   - Chronological sorting with alphabetical secondary key
-- ==============================================================================

SELECT
    series_name,
    host_country,
    match_type,
    start_date,
    total_matches
FROM series
WHERE start_date >= '2024-01-01'
  AND start_date <= '2024-12-31'
ORDER BY start_date ASC, series_name ASC;

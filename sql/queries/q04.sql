-- ==============================================================================
-- Query 04: Large Venues (> 50,000 Capacity)
-- Category: Beginner
--
-- Business Purpose:
--   Identify major cricket stadiums suitable for high-attendance fixtures,
--   tournament finals, and marquee international series based on seating capacity.
--
-- SQL Concepts:
--   - Single-table SELECT with filtering
--   - Strict inequality filter (capacity > 50000)
--   - Deterministic multi-column sorting (capacity DESC, venue_name ASC)
--   - Handling NULL capacities gracefully
-- ==============================================================================

SELECT
    venue_name,
    city,
    country,
    capacity
FROM venues
WHERE capacity IS NOT NULL
  AND capacity > 50000
ORDER BY capacity DESC, venue_name ASC;

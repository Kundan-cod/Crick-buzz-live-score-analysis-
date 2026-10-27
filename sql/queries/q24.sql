-- ==============================================================================
-- Query 24: Batting Partnerships Analysis
-- Category: Advanced
--
-- Business Purpose:
--   Identify premier batting pairs who consistently build significant scoring stands
--   (minimum 5 recorded partnerships), assessing average stand, 50+ milestones,
--   highest stand, and partnership success rate.
--
-- SQL Concepts:
--   - Canonical pairing with CASE WHEN player1_id < player2_id to combine pairings
--   - Multi-table lookup joins to players table for both partnership participants
--   - Milestone aggregation (stands >= 50 runs) and success rate percentages
--   - Sample size qualification: HAVING COUNT(part.partnership_id) >= 5
-- ==============================================================================

WITH canonical_partnerships AS (
    SELECT
        part.partnership_id,
        part.runs_scored,
        CASE WHEN part.player1_id < part.player2_id THEN part.player1_id ELSE part.player2_id END AS batsman_a_id,
        CASE WHEN part.player1_id < part.player2_id THEN part.player2_id ELSE part.player1_id END AS batsman_b_id
    FROM partnerships part
)
SELECT
    p1.full_name AS batsman_1,
    p2.full_name AS batsman_2,
    COUNT(cp.partnership_id) AS total_partnerships,
    ROUND(AVG(cp.runs_scored), 2) AS avg_partnership_runs,
    SUM(CASE WHEN cp.runs_scored >= 50 THEN 1 ELSE 0 END) AS stands_50_plus,
    MAX(cp.runs_scored) AS highest_partnership,
    ROUND(
        SUM(CASE WHEN cp.runs_scored >= 50 THEN 1.0 ELSE 0.0 END) * 100.0
        / COUNT(cp.partnership_id),
        2
    ) AS success_rate_pct
FROM canonical_partnerships cp
JOIN players p1 ON cp.batsman_a_id = p1.player_id
JOIN players p2 ON cp.batsman_b_id = p2.player_id
GROUP BY cp.batsman_a_id, cp.batsman_b_id, p1.full_name, p2.full_name
HAVING COUNT(cp.partnership_id) >= 5
ORDER BY avg_partnership_runs DESC, success_rate_pct DESC, batsman_1 ASC;

-- ==============================================================================
-- Query 17: Toss Advantage Analysis (Bat vs. Bowl First)
-- Category: Advanced
--
-- Business Purpose:
--   Quantify the strategic value of the coin toss by computing match win percentages
--   for toss-winning teams, segmented by their decision to bat first versus bowl first.
--
-- SQL Concepts:
--   - Categorical segmentation with GROUP BY toss_decision
--   - Conditional summation: SUM(CASE WHEN toss_winner_id = winning_team_id THEN 1 ELSE 0 END)
--   - Precision percentage calculation with floating-point arithmetic (100.0 / COUNT(*))
--   - Robust data sanitization (filtering out matches with missing toss data or non-completed status)
-- ==============================================================================

SELECT
    m.toss_decision,
    COUNT(m.match_id) AS total_matches,
    SUM(CASE WHEN m.toss_winner_id = m.winning_team_id THEN 1 ELSE 0 END) AS toss_winner_wins,
    SUM(CASE WHEN m.toss_winner_id != m.winning_team_id THEN 1 ELSE 0 END) AS toss_winner_losses,
    ROUND(
        SUM(CASE WHEN m.toss_winner_id = m.winning_team_id THEN 1.0 ELSE 0.0 END) * 100.0
        / COUNT(m.match_id),
        2
    ) AS toss_win_match_win_pct
FROM matches m
WHERE m.match_status = 'Completed'
  AND m.toss_winner_id IS NOT NULL
  AND m.toss_decision IN ('bat', 'bowl')
GROUP BY m.toss_decision
ORDER BY m.toss_decision ASC;

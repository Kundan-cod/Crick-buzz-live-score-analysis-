-- ==============================================================================
-- Query 13: Consecutive Batting-Position Pairs (Combined Runs >= 100)
-- Category: Intermediate
--
-- Business Purpose:
--   Detect impactful batting partnerships formed by consecutive order batsmen
--   (e.g., opener-opener, #3-#4) who collectively accumulated 100+ runs in an innings.
--
-- SQL Concepts:
--   - Self-join on batting_performances table (bp1 and bp2)
--   - Consecutive adjacency condition: bp2.batting_position = bp1.batting_position + 1
--   - Multi-player lookup via repeated joins to the players table
--   - Arithmetic filter: (bp1.runs_scored + bp2.runs_scored) >= 100
-- ==============================================================================

SELECT
    m.match_desc,
    i.innings_number,
    p1.full_name AS batsman_1,
    bp1.batting_position AS position_1,
    bp1.runs_scored AS runs_1,
    p2.full_name AS batsman_2,
    bp2.batting_position AS position_2,
    bp2.runs_scored AS runs_2,
    (bp1.runs_scored + bp2.runs_scored) AS combined_runs
FROM batting_performances bp1
JOIN batting_performances bp2 ON bp1.innings_id = bp2.innings_id
                             AND bp2.batting_position = bp1.batting_position + 1
JOIN players p1 ON bp1.player_id = p1.player_id
JOIN players p2 ON bp2.player_id = p2.player_id
JOIN innings i ON bp1.innings_id = i.innings_id
JOIN matches m ON i.match_id = m.match_id
WHERE (bp1.runs_scored + bp2.runs_scored) >= 100
ORDER BY combined_runs DESC, m.match_date DESC, p1.full_name ASC;

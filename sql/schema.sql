-- ==============================================================================
-- Cricbuzz LiveStats: Relational SQLite Database Schema
-- Normalized to 3NF for Sports Analytics & Web Application
-- ==============================================================================

-- Enforce foreign keys on connection
PRAGMA foreign_keys = ON;

-- ------------------------------------------------------------------------------
-- 1. TEAMS
-- Represents participating international and domestic cricket teams
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS teams (
    team_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_name TEXT NOT NULL UNIQUE,
    short_name TEXT NOT NULL,
    country TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------------------------
-- 2. PLAYERS
-- Master record of all cricket athletes
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS players (
    player_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER REFERENCES teams(team_id) ON DELETE SET NULL,
    full_name TEXT NOT NULL,
    country TEXT NOT NULL,
    playing_role TEXT NOT NULL CHECK (
        playing_role IN ('Batter', 'Bowler', 'All-rounder', 'Wicket-keeper')
    ),
    batting_style TEXT NOT NULL CHECK (
        batting_style IN ('Right-hand bat', 'Left-hand bat')
    ),
    bowling_style TEXT CHECK (
        bowling_style IN (
            'Right-arm fast', 'Right-arm medium', 'Right-arm offbreak', 'Right-arm legbreak',
            'Left-arm fast', 'Left-arm medium', 'Left-arm orthodox', 'Slow left-arm chinaman',
            'None'
        )
    ),
    source TEXT NOT NULL DEFAULT 'LOCAL' CHECK (source IN ('API', 'LOCAL')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(full_name, country)
);

-- ------------------------------------------------------------------------------
-- 3. VENUES
-- Stadiums and match grounds with geographical and capacity data
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS venues (
    venue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    venue_name TEXT NOT NULL,
    city TEXT NOT NULL,
    country TEXT NOT NULL,
    capacity INTEGER CHECK (capacity IS NULL OR capacity > 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(venue_name, city)
);

-- ------------------------------------------------------------------------------
-- 4. SERIES
-- Bilateral tours, multilateral cups, and league tournaments
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS series (
    series_id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_name TEXT NOT NULL,
    host_country TEXT NOT NULL,
    match_type TEXT NOT NULL CHECK (
        match_type IN ('Test', 'ODI', 'T20I', 'T20', 'Multi-format')
    ),
    start_date DATE NOT NULL,
    end_date DATE,
    total_matches INTEGER NOT NULL DEFAULT 1 CHECK (total_matches > 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(series_name, start_date)
);

-- ------------------------------------------------------------------------------
-- 5. MATCHES
-- Individual fixtures with format, toss, status, and outcome details
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS matches (
    match_id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT,
    series_id INTEGER REFERENCES series(series_id) ON DELETE SET NULL,
    match_desc TEXT NOT NULL,
    match_format TEXT NOT NULL CHECK (
        match_format IN ('Test', 'ODI', 'T20I', 'T20')
    ),
    match_date DATE NOT NULL,
    team1_id INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE RESTRICT,
    team2_id INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE RESTRICT,
    venue_id INTEGER NOT NULL REFERENCES venues(venue_id) ON DELETE RESTRICT,
    toss_winner_id INTEGER REFERENCES teams(team_id) ON DELETE RESTRICT,
    toss_decision TEXT CHECK (toss_decision IN ('bat', 'bowl') OR toss_decision IS NULL),
    match_status TEXT NOT NULL DEFAULT 'Completed' CHECK (
        match_status IN ('Completed', 'Live', 'Upcoming', 'Abandoned', 'No Result', 'Tied')
    ),
    winning_team_id INTEGER REFERENCES teams(team_id) ON DELETE RESTRICT,
    win_margin INTEGER CHECK (win_margin IS NULL OR win_margin >= 0),
    win_type TEXT CHECK (
        win_type IN ('runs', 'wickets', 'tie', 'no result', 'abandoned') OR win_type IS NULL
    ),
    source TEXT NOT NULL DEFAULT 'LOCAL' CHECK (source IN ('API', 'LOCAL')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (team1_id != team2_id)
);

-- ------------------------------------------------------------------------------
-- 6. INNINGS
-- Innings breakdown per match (up to 4 innings for Tests, 2 for ODIs/T20s)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS innings (
    innings_id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    innings_number INTEGER NOT NULL CHECK (innings_number IN (1, 2, 3, 4)),
    batting_team_id INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE RESTRICT,
    bowling_team_id INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE RESTRICT,
    total_runs INTEGER NOT NULL DEFAULT 0 CHECK (total_runs >= 0),
    total_wickets INTEGER NOT NULL DEFAULT 0 CHECK (total_wickets BETWEEN 0 AND 10),
    overs_completed REAL NOT NULL DEFAULT 0.0 CHECK (overs_completed >= 0.0),
    is_declared INTEGER NOT NULL DEFAULT 0 CHECK (is_declared IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(match_id, innings_number),
    CHECK (batting_team_id != bowling_team_id)
);

-- ------------------------------------------------------------------------------
-- 7. BATTING PERFORMANCES
-- Individual batsman scorecards per innings
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS batting_performances (
    perf_id INTEGER PRIMARY KEY AUTOINCREMENT,
    innings_id INTEGER NOT NULL REFERENCES innings(innings_id) ON DELETE CASCADE,
    player_id INTEGER NOT NULL REFERENCES players(player_id) ON DELETE RESTRICT,
    batting_position INTEGER NOT NULL CHECK (batting_position BETWEEN 1 AND 11),
    runs_scored INTEGER NOT NULL DEFAULT 0 CHECK (runs_scored >= 0),
    balls_faced INTEGER NOT NULL DEFAULT 0 CHECK (balls_faced >= 0),
    fours INTEGER NOT NULL DEFAULT 0 CHECK (fours >= 0),
    sixes INTEGER NOT NULL DEFAULT 0 CHECK (sixes >= 0),
    dismissal_type TEXT NOT NULL DEFAULT 'not out' CHECK (
        dismissal_type IN (
            'bowled', 'caught', 'lbw', 'run out', 'stumped', 'hit wicket',
            'retired hurt', 'not out', 'did not bat'
        )
    ),
    is_not_out INTEGER NOT NULL DEFAULT 0 CHECK (is_not_out IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(innings_id, player_id),
    UNIQUE(innings_id, batting_position)
);

-- ------------------------------------------------------------------------------
-- 8. BOWLING PERFORMANCES
-- Individual bowler scorecards per innings
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bowling_performances (
    bowl_id INTEGER PRIMARY KEY AUTOINCREMENT,
    innings_id INTEGER NOT NULL REFERENCES innings(innings_id) ON DELETE CASCADE,
    player_id INTEGER NOT NULL REFERENCES players(player_id) ON DELETE RESTRICT,
    overs_bowled REAL NOT NULL DEFAULT 0.0 CHECK (overs_bowled >= 0.0),
    balls_bowled INTEGER NOT NULL DEFAULT 0 CHECK (balls_bowled >= 0),
    maidens INTEGER NOT NULL DEFAULT 0 CHECK (maidens >= 0),
    runs_conceded INTEGER NOT NULL DEFAULT 0 CHECK (runs_conceded >= 0),
    wickets_taken INTEGER NOT NULL DEFAULT 0 CHECK (wickets_taken BETWEEN 0 AND 10),
    economy_rate REAL NOT NULL DEFAULT 0.0 CHECK (economy_rate >= 0.0),
    wides INTEGER NOT NULL DEFAULT 0 CHECK (wides >= 0),
    no_balls INTEGER NOT NULL DEFAULT 0 CHECK (no_balls >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(innings_id, player_id)
);

-- ------------------------------------------------------------------------------
-- 9. FIELDING PERFORMANCES
-- Fielding contributions per player per innings (catches, stumpings, run outs)
-- Required for Q21 weighted ranking
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fielding_performances (
    field_id INTEGER PRIMARY KEY AUTOINCREMENT,
    innings_id INTEGER NOT NULL REFERENCES innings(innings_id) ON DELETE CASCADE,
    player_id INTEGER NOT NULL REFERENCES players(player_id) ON DELETE RESTRICT,
    catches INTEGER NOT NULL DEFAULT 0 CHECK (catches >= 0),
    stumpings INTEGER NOT NULL DEFAULT 0 CHECK (stumpings >= 0),
    run_outs INTEGER NOT NULL DEFAULT 0 CHECK (run_outs >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(innings_id, player_id)
);

-- ------------------------------------------------------------------------------
-- 10. PARTNERSHIPS
-- Wicket partnerships between two batsmen in an innings
-- Required for Q13 and Q24 partnership analytics
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS partnerships (
    partnership_id INTEGER PRIMARY KEY AUTOINCREMENT,
    innings_id INTEGER NOT NULL REFERENCES innings(innings_id) ON DELETE CASCADE,
    wicket_number INTEGER NOT NULL CHECK (wicket_number BETWEEN 1 AND 10),
    player1_id INTEGER NOT NULL REFERENCES players(player_id) ON DELETE RESTRICT,
    player2_id INTEGER NOT NULL REFERENCES players(player_id) ON DELETE RESTRICT,
    runs_scored INTEGER NOT NULL DEFAULT 0 CHECK (runs_scored >= 0),
    balls_faced INTEGER DEFAULT 0 CHECK (balls_faced >= 0),
    is_unbroken INTEGER NOT NULL DEFAULT 0 CHECK (is_unbroken IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(innings_id, wicket_number),
    CHECK (player1_id != player2_id)
);

-- ==============================================================================
-- INDEXES FOR FREQUENTLY QUERIED PATTERNS
-- ==============================================================================

-- Players indexes
CREATE INDEX IF NOT EXISTS idx_players_team_id ON players(team_id);
CREATE INDEX IF NOT EXISTS idx_players_country ON players(country);
CREATE INDEX IF NOT EXISTS idx_players_role ON players(playing_role);

-- Matches indexes
CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(match_date);
CREATE INDEX IF NOT EXISTS idx_matches_format ON matches(match_format);
CREATE INDEX IF NOT EXISTS idx_matches_teams ON matches(team1_id, team2_id);
CREATE INDEX IF NOT EXISTS idx_matches_venue ON matches(venue_id);
CREATE INDEX IF NOT EXISTS idx_matches_winner ON matches(winning_team_id);
CREATE INDEX IF NOT EXISTS idx_matches_external_id ON matches(external_id);

-- Innings indexes
CREATE INDEX IF NOT EXISTS idx_innings_match ON innings(match_id);

-- Batting performances indexes
CREATE INDEX IF NOT EXISTS idx_batting_player ON batting_performances(player_id);
CREATE INDEX IF NOT EXISTS idx_batting_innings ON batting_performances(innings_id);
CREATE INDEX IF NOT EXISTS idx_batting_runs ON batting_performances(runs_scored);

-- Bowling performances indexes
CREATE INDEX IF NOT EXISTS idx_bowling_player ON bowling_performances(player_id);
CREATE INDEX IF NOT EXISTS idx_bowling_innings ON bowling_performances(innings_id);
CREATE INDEX IF NOT EXISTS idx_bowling_wickets ON bowling_performances(wickets_taken);

-- Fielding performances indexes
CREATE INDEX IF NOT EXISTS idx_fielding_player ON fielding_performances(player_id);
CREATE INDEX IF NOT EXISTS idx_fielding_innings ON fielding_performances(innings_id);

-- Partnerships indexes
CREATE INDEX IF NOT EXISTS idx_partnerships_players ON partnerships(player1_id, player2_id);
CREATE INDEX IF NOT EXISTS idx_partnerships_innings ON partnerships(innings_id);

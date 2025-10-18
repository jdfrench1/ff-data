BEGIN;

CREATE TABLE IF NOT EXISTS seasons (
    season_id BIGSERIAL PRIMARY KEY,
    year INTEGER NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS weeks (
    week_id BIGSERIAL PRIMARY KEY,
    season_id BIGINT NOT NULL REFERENCES seasons(season_id) ON DELETE RESTRICT,
    week_number INTEGER NOT NULL CHECK (week_number BETWEEN 1 AND 22),
    start_date DATE,
    end_date DATE,
    UNIQUE (season_id, week_number)
);

CREATE TABLE IF NOT EXISTS teams (
    team_id BIGSERIAL PRIMARY KEY,
    team_code TEXT NOT NULL UNIQUE,
    team_name TEXT,
    conference TEXT,
    division TEXT
);

CREATE TABLE IF NOT EXISTS players (
    player_id BIGSERIAL PRIMARY KEY,
    gsis_id TEXT UNIQUE,
    pfr_id TEXT UNIQUE,
    full_name TEXT NOT NULL,
    position TEXT,
    birthdate DATE
);

CREATE TABLE IF NOT EXISTS coaches (
    coach_id BIGSERIAL PRIMARY KEY,
    full_name TEXT NOT NULL,
    birthdate DATE
);

CREATE TABLE IF NOT EXISTS id_map (
    id_map_id BIGSERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id BIGINT NOT NULL,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    UNIQUE (entity_type, source, source_id)
);

CREATE TABLE IF NOT EXISTS roster_assignments (
    assignment_id BIGSERIAL PRIMARY KEY,
    player_id BIGINT NOT NULL REFERENCES players(player_id) ON DELETE RESTRICT,
    team_id BIGINT NOT NULL REFERENCES teams(team_id) ON DELETE RESTRICT,
    start_week_id BIGINT NOT NULL REFERENCES weeks(week_id) ON DELETE RESTRICT,
    end_week_id BIGINT REFERENCES weeks(week_id) ON DELETE RESTRICT,
    jersey_number INTEGER,
    position_group TEXT,
    UNIQUE (player_id, team_id, start_week_id)
);

CREATE TABLE IF NOT EXISTS coach_roles (
    coach_role_id BIGSERIAL PRIMARY KEY,
    coach_id BIGINT NOT NULL REFERENCES coaches(coach_id) ON DELETE RESTRICT,
    team_id BIGINT NOT NULL REFERENCES teams(team_id) ON DELETE RESTRICT,
    role TEXT NOT NULL,
    start_week_id BIGINT NOT NULL REFERENCES weeks(week_id) ON DELETE RESTRICT,
    end_week_id BIGINT REFERENCES weeks(week_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS games (
    game_id BIGSERIAL PRIMARY KEY,
    nflfast_game_id TEXT UNIQUE,
    week_id BIGINT NOT NULL REFERENCES weeks(week_id) ON DELETE RESTRICT,
    home_team_id BIGINT NOT NULL REFERENCES teams(team_id) ON DELETE RESTRICT,
    away_team_id BIGINT NOT NULL REFERENCES teams(team_id) ON DELETE RESTRICT,
    venue TEXT,
    kickoff_ts TIMESTAMPTZ,
    roof TEXT,
    surface TEXT,
    vegas_favorite_team_id BIGINT REFERENCES teams(team_id) ON DELETE RESTRICT,
    spread REAL,
    total REAL,
    home_points INTEGER,
    away_points INTEGER,
    winner_team_id BIGINT REFERENCES teams(team_id) ON DELETE RESTRICT,
    UNIQUE (week_id, home_team_id, away_team_id)
);

CREATE TABLE IF NOT EXISTS team_game_stats (
    team_game_stats_id BIGSERIAL PRIMARY KEY,
    game_id BIGINT NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
    team_id BIGINT NOT NULL REFERENCES teams(team_id) ON DELETE RESTRICT,
    points INTEGER,
    yards INTEGER,
    pass_yards INTEGER,
    rush_yards INTEGER,
    sacks_made INTEGER,
    sacks_allowed INTEGER,
    turnovers INTEGER,
    epa NUMERIC,
    success_rate NUMERIC,
    UNIQUE (game_id, team_id)
);

CREATE TABLE IF NOT EXISTS player_game_stats (
    player_game_stats_id BIGSERIAL PRIMARY KEY,
    game_id BIGINT NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
    player_id BIGINT NOT NULL REFERENCES players(player_id) ON DELETE RESTRICT,
    team_id BIGINT NOT NULL REFERENCES teams(team_id) ON DELETE RESTRICT,
    week_id BIGINT NOT NULL REFERENCES weeks(week_id) ON DELETE RESTRICT,
    position TEXT,
    starter BOOLEAN,
    snaps_off INTEGER,
    snaps_def INTEGER,
    snaps_st INTEGER,
    pass_att INTEGER,
    pass_cmp INTEGER,
    pass_yds INTEGER,
    pass_td INTEGER,
    int_thrown INTEGER,
    rush_att INTEGER,
    rush_yds INTEGER,
    rush_td INTEGER,
    targets INTEGER,
    receptions INTEGER,
    rec_yds INTEGER,
    rec_td INTEGER,
    tackles INTEGER,
    sacks NUMERIC,
    interceptions INTEGER,
    fumbles INTEGER,
    fantasy_ppr NUMERIC,
    UNIQUE (game_id, player_id)
);

COMMIT;

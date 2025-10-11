from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Generator, List, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db import session_scope

logger = logging.getLogger(__name__)

app = FastAPI(title="NFL Database API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api/v1")


class SeasonResponse(BaseModel):
    season_id: int
    year: int


class WeekResponse(BaseModel):
    week_id: int
    week_number: int
    start_date: Optional[date]
    end_date: Optional[date]


class GameResponse(BaseModel):
    game_id: int
    nflfast_game_id: Optional[str]
    season: int
    week: int
    home_team: str
    away_team: str
    home_points: Optional[int]
    away_points: Optional[int]
    kickoff_ts: Optional[datetime]


class TeamStatsResponse(BaseModel):
    game_id: int
    season: int
    week: int
    team_code: str
    team_name: Optional[str]
    points: Optional[int]
    yards: Optional[int]
    pass_yards: Optional[int]
    rush_yards: Optional[int]
    sacks_made: Optional[int]
    sacks_allowed: Optional[int]
    turnovers: Optional[int]


class PlayerSummaryResponse(BaseModel):
    player_id: int
    full_name: str
    position: Optional[str]
    team_code: Optional[str]
    team_name: Optional[str]


class PlayerTimelineEntryResponse(BaseModel):
    season: int
    week: int
    team_code: Optional[str]
    team_name: Optional[str]
    kickoff_ts: Optional[datetime]
    games_played: int
    pass_att: Optional[int]
    pass_cmp: Optional[int]
    pass_yds: Optional[int]
    pass_td: Optional[int]
    int_thrown: Optional[int]
    rush_att: Optional[int]
    rush_yds: Optional[int]
    rush_td: Optional[int]
    targets: Optional[int]
    receptions: Optional[int]
    rec_yds: Optional[int]
    rec_td: Optional[int]
    tackles: Optional[int]
    sacks: Optional[float]
    interceptions: Optional[int]
    fumbles: Optional[int]
    fantasy_ppr: Optional[float]
    snaps_off: Optional[int]
    snaps_def: Optional[int]
    snaps_st: Optional[int]


class PlayerTeamEventResponse(BaseModel):
    team_code: str
    team_name: Optional[str]
    start_season: int
    start_week: int
    end_season: int
    end_week: int


class PlayerTimelineResponse(BaseModel):
    player_id: int
    full_name: str
    position: Optional[str]
    timeline: List[PlayerTimelineEntryResponse]
    team_events: List[PlayerTeamEventResponse]


class ErrorResponse(BaseModel):
    detail: str


def get_session() -> Generator[Session, None, None]:
    with session_scope() as session:
        yield session


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
):
    logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


@app.get("/health", response_model=dict)
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@api_router.get(
    "/seasons",
    response_model=List[SeasonResponse],
    responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse}},
)
def list_seasons(session: Session = Depends(get_session)) -> List[SeasonResponse]:
    rows = session.execute(
        text(
            """
            SELECT s.season_id, s.year
            FROM seasons AS s
            WHERE EXISTS (
                SELECT 1
                FROM weeks AS w
                JOIN games AS g ON g.week_id = w.week_id
                WHERE w.season_id = s.season_id
                  AND g.home_points IS NOT NULL
                  AND g.away_points IS NOT NULL
            )
            ORDER BY s.year DESC
            """
        )
    ).mappings()
    return [
        SeasonResponse(season_id=row["season_id"], year=row["year"]) for row in rows
    ]


@api_router.get(
    "/weeks",
    response_model=List[WeekResponse],
    responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse}},
)
def list_weeks(
    season: int = Query(..., ge=1920, description="Season year, e.g. 2023"),
    session: Session = Depends(get_session),
) -> List[WeekResponse]:
    rows = session.execute(
        text(
            """
            SELECT w.week_id, w.week_number, w.start_date, w.end_date
            FROM weeks AS w
            JOIN seasons AS s ON s.season_id = w.season_id
            WHERE s.year = :season
            ORDER BY w.week_number ASC
            """
        ),
        {"season": season},
    ).mappings()

    return [
        WeekResponse(
            week_id=row["week_id"],
            week_number=row["week_number"],
            start_date=row["start_date"],
            end_date=row["end_date"],
        )
        for row in rows
    ]


@api_router.get(
    "/games",
    response_model=List[GameResponse],
    responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse}},
)
def list_games(
    season: int = Query(..., ge=1920, description="Season year, e.g. 2023"),
    session: Session = Depends(get_session),
) -> List[GameResponse]:
    rows = session.execute(
        text(
            """
            SELECT
                g.game_id,
                g.nflfast_game_id,
                s.year AS season,
                w.week_number,
                home.team_code AS home_team,
                away.team_code AS away_team,
                g.home_points,
                g.away_points,
                g.kickoff_ts
            FROM games AS g
            JOIN weeks AS w ON g.week_id = w.week_id
            JOIN seasons AS s ON w.season_id = s.season_id
            JOIN teams AS home ON g.home_team_id = home.team_id
            JOIN teams AS away ON g.away_team_id = away.team_id
            WHERE s.year = :season
            ORDER BY w.week_number ASC,
                CASE WHEN g.kickoff_ts IS NULL THEN 1 ELSE 0 END,
                g.kickoff_ts ASC
            """
        ),
        {"season": season},
    ).mappings()

    return [
        GameResponse(
            game_id=row["game_id"],
            nflfast_game_id=row["nflfast_game_id"],
            season=row["season"],
            week=row["week_number"],
            home_team=row["home_team"],
            away_team=row["away_team"],
            home_points=row["home_points"],
            away_points=row["away_points"],
            kickoff_ts=row["kickoff_ts"],
        )
        for row in rows
    ]


@api_router.get(
    "/games/{game_id}",
    response_model=GameResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse},
    },
)
def get_game(
    game_id: int,
    session: Session = Depends(get_session),
) -> GameResponse:
    row = (
        session.execute(
            text(
                """
            SELECT
                g.game_id,
                g.nflfast_game_id,
                s.year AS season,
                w.week_number,
                home.team_code AS home_team,
                away.team_code AS away_team,
                g.home_points,
                g.away_points,
                g.kickoff_ts
            FROM games AS g
            JOIN weeks AS w ON g.week_id = w.week_id
            JOIN seasons AS s ON w.season_id = s.season_id
            JOIN teams AS home ON g.home_team_id = home.team_id
            JOIN teams AS away ON g.away_team_id = away.team_id
            WHERE g.game_id = :game_id
            """
            ),
            {"game_id": game_id},
        )
        .mappings()
        .first()
    )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found"
        )

    return GameResponse(
        game_id=row["game_id"],
        nflfast_game_id=row["nflfast_game_id"],
        season=row["season"],
        week=row["week_number"],
        home_team=row["home_team"],
        away_team=row["away_team"],
        home_points=row["home_points"],
        away_points=row["away_points"],
        kickoff_ts=row["kickoff_ts"],
    )


@api_router.get(
    "/team-stats",
    response_model=List[TeamStatsResponse],
    responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse}},
)
def list_team_stats(
    season: int = Query(..., ge=1920, description="Season year, e.g. 2023"),
    session: Session = Depends(get_session),
) -> List[TeamStatsResponse]:
    rows = session.execute(
        text(
            """
            SELECT
                g.game_id,
                s.year AS season,
                w.week_number,
                t.team_code,
                t.team_name,
                stats.points,
                stats.yards,
                stats.pass_yards,
                stats.rush_yards,
                stats.sacks_made,
                stats.sacks_allowed,
                stats.turnovers
            FROM team_game_stats AS stats
            JOIN games AS g ON stats.game_id = g.game_id
            JOIN weeks AS w ON g.week_id = w.week_id
            JOIN seasons AS s ON w.season_id = s.season_id
            JOIN teams AS t ON stats.team_id = t.team_id
            WHERE s.year = :season
            ORDER BY w.week_number ASC,
                CASE WHEN g.kickoff_ts IS NULL THEN 1 ELSE 0 END,
                g.kickoff_ts ASC,
                t.team_code ASC
            """
        ),
        {"season": season},
    ).mappings()

    return [
        TeamStatsResponse(
            game_id=row["game_id"],
            season=row["season"],
            week=row["week_number"],
            team_code=row["team_code"],
            team_name=row["team_name"],
            points=row["points"],
            yards=row["yards"],
            pass_yards=row["pass_yards"],
            rush_yards=row["rush_yards"],
            sacks_made=row["sacks_made"],
            sacks_allowed=row["sacks_allowed"],
            turnovers=row["turnovers"],
        )
        for row in rows
    ]


@api_router.get(
    "/players",
    response_model=List[PlayerSummaryResponse],
    responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse}},
)
def search_players(
    search: str = Query(..., min_length=2, description="Player name search term"),
    session: Session = Depends(get_session),
) -> List[PlayerSummaryResponse]:
    term = search.strip()
    if not term:
        return []

    pattern = f"%{term.lower()}%"
    rows = session.execute(
        text(
            """
            WITH latest_team AS (
                SELECT
                    stats.player_id,
                    t.team_code,
                    t.team_name,
                    ROW_NUMBER() OVER (
                        PARTITION BY stats.player_id
                        ORDER BY s.year DESC,
                                 w.week_number DESC,
                                 CASE WHEN g.kickoff_ts IS NULL THEN 1 ELSE 0 END ASC,
                                 g.kickoff_ts DESC,
                                 stats.game_id DESC
                    ) AS row_num
                FROM player_game_stats AS stats
                JOIN weeks AS w ON stats.week_id = w.week_id
                JOIN seasons AS s ON w.season_id = s.season_id
                JOIN teams AS t ON stats.team_id = t.team_id
                LEFT JOIN games AS g ON stats.game_id = g.game_id
            )
            SELECT
                p.player_id,
                p.full_name,
                p.position,
                lt.team_code,
                lt.team_name
            FROM players AS p
            LEFT JOIN (
                SELECT player_id, team_code, team_name
                FROM latest_team
                WHERE row_num = 1
            ) AS lt ON lt.player_id = p.player_id
            WHERE LOWER(p.full_name) LIKE :pattern
            ORDER BY p.full_name ASC
            LIMIT 25
            """
        ),
        {"pattern": pattern},
    ).mappings()

    return [
        PlayerSummaryResponse(
            player_id=row["player_id"],
            full_name=row["full_name"],
            position=row["position"],
            team_code=row["team_code"],
            team_name=row["team_name"],
        )
        for row in rows
    ]


@api_router.get(
    "/players/{player_id}/timeline",
    response_model=PlayerTimelineResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse},
    },
)
def get_player_timeline(
    player_id: int,
    season: Optional[int] = Query(
        None, ge=1920, description="Optional season filter (e.g. 2023)"
    ),
    session: Session = Depends(get_session),
) -> PlayerTimelineResponse:
    player_row = (
        session.execute(
            text(
                """
            SELECT player_id, full_name, position
            FROM players
            WHERE player_id = :player_id
            """
            ),
            {"player_id": player_id},
        )
        .mappings()
        .first()
    )

    if player_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Player not found"
        )

    params = {"player_id": player_id}
    season_filter = ""
    if season is not None:
        season_filter = "AND s.year = :season"
        params["season"] = season

    timeline_rows = session.execute(
        text(
            f"""
            SELECT
                s.year AS season,
                w.week_number AS week,
                t.team_code AS team_code,
                t.team_name AS team_name,
                MIN(g.kickoff_ts) AS kickoff_ts,
                COUNT(DISTINCT stats.game_id) AS games_played,
                SUM(COALESCE(stats.pass_att, 0)) AS pass_att,
                SUM(COALESCE(stats.pass_cmp, 0)) AS pass_cmp,
                SUM(COALESCE(stats.pass_yds, 0)) AS pass_yds,
                SUM(COALESCE(stats.pass_td, 0)) AS pass_td,
                SUM(COALESCE(stats.int_thrown, 0)) AS int_thrown,
                SUM(COALESCE(stats.rush_att, 0)) AS rush_att,
                SUM(COALESCE(stats.rush_yds, 0)) AS rush_yds,
                SUM(COALESCE(stats.rush_td, 0)) AS rush_td,
                SUM(COALESCE(stats.targets, 0)) AS targets,
                SUM(COALESCE(stats.receptions, 0)) AS receptions,
                SUM(COALESCE(stats.rec_yds, 0)) AS rec_yds,
                SUM(COALESCE(stats.rec_td, 0)) AS rec_td,
                SUM(COALESCE(stats.tackles, 0)) AS tackles,
                SUM(COALESCE(stats.sacks, 0)) AS sacks,
                SUM(COALESCE(stats.interceptions, 0)) AS interceptions,
                SUM(COALESCE(stats.fumbles, 0)) AS fumbles,
                SUM(COALESCE(stats.fantasy_ppr, 0)) AS fantasy_ppr,
                SUM(COALESCE(stats.snaps_off, 0)) AS snaps_off,
                SUM(COALESCE(stats.snaps_def, 0)) AS snaps_def,
                SUM(COALESCE(stats.snaps_st, 0)) AS snaps_st
            FROM player_game_stats AS stats
            JOIN weeks AS w ON stats.week_id = w.week_id
            JOIN seasons AS s ON w.season_id = s.season_id
            JOIN teams AS t ON stats.team_id = t.team_id
            LEFT JOIN games AS g ON stats.game_id = g.game_id
            WHERE stats.player_id = :player_id
            {season_filter}
            GROUP BY s.year, w.week_number, t.team_code, t.team_name
            ORDER BY s.year ASC, w.week_number ASC
            """
        ),
        params,
    ).mappings()

    timeline: List[PlayerTimelineEntryResponse] = []
    for row in timeline_rows:
        kickoff = row["kickoff_ts"]
        kickoff_dt: Optional[datetime]
        if isinstance(kickoff, datetime):
            kickoff_dt = kickoff
        elif isinstance(kickoff, str):
            try:
                kickoff_dt = datetime.fromisoformat(kickoff)
            except ValueError:
                kickoff_dt = None
        else:
            kickoff_dt = None

        timeline.append(
            PlayerTimelineEntryResponse(
                season=row["season"],
                week=row["week"],
                team_code=row["team_code"],
                team_name=row["team_name"],
                kickoff_ts=kickoff_dt,
                games_played=row["games_played"],
                pass_att=row["pass_att"],
                pass_cmp=row["pass_cmp"],
                pass_yds=row["pass_yds"],
                pass_td=row["pass_td"],
                int_thrown=row["int_thrown"],
                rush_att=row["rush_att"],
                rush_yds=row["rush_yds"],
                rush_td=row["rush_td"],
                targets=row["targets"],
                receptions=row["receptions"],
                rec_yds=row["rec_yds"],
                rec_td=row["rec_td"],
                tackles=row["tackles"],
                sacks=row["sacks"],
                interceptions=row["interceptions"],
                fumbles=row["fumbles"],
                fantasy_ppr=row["fantasy_ppr"],
                snaps_off=row["snaps_off"],
                snaps_def=row["snaps_def"],
                snaps_st=row["snaps_st"],
            )
        )

    team_events_data: List[dict[str, object]] = []
    for entry in timeline:
        if entry.team_code is None:
            continue
        if not team_events_data or team_events_data[-1]["team_code"] != entry.team_code:
            team_events_data.append(
                {
                    "team_code": entry.team_code,
                    "team_name": entry.team_name,
                    "start_season": entry.season,
                    "start_week": entry.week,
                    "end_season": entry.season,
                    "end_week": entry.week,
                }
            )
        else:
            team_events_data[-1]["end_season"] = entry.season
            team_events_data[-1]["end_week"] = entry.week

    team_events = [
        PlayerTeamEventResponse(**event_data) for event_data in team_events_data
    ]

    return PlayerTimelineResponse(
        player_id=player_row["player_id"],
        full_name=player_row["full_name"],
        position=player_row["position"],
        timeline=timeline,
        team_events=team_events,
    )


app.include_router(api_router)

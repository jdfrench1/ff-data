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


app.include_router(api_router)

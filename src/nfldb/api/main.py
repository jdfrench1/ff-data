from __future__ import annotations

from datetime import datetime
from typing import Generator, List, Optional

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db import session_scope

app = FastAPI(title="NFL Database API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"]
)


class SeasonResponse(BaseModel):
    season_id: int
    year: int


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


def get_session() -> Generator[Session, None, None]:
    with session_scope() as session:
        yield session


@app.get("/health", response_model=dict)
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/seasons", response_model=List[SeasonResponse])
def list_seasons(session: Session = Depends(get_session)) -> List[SeasonResponse]:
    rows = session.execute(
        text("SELECT season_id, year FROM seasons ORDER BY year DESC")
    ).mappings()
    return [
        SeasonResponse(season_id=row["season_id"], year=row["year"]) for row in rows
    ]


@app.get("/api/games", response_model=List[GameResponse])
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
            FROM games g
            JOIN weeks w ON g.week_id = w.week_id
            JOIN seasons s ON w.season_id = s.season_id
            JOIN teams home ON g.home_team_id = home.team_id
            JOIN teams away ON g.away_team_id = away.team_id
            WHERE s.year = :season
            ORDER BY w.week_number ASC, g.kickoff_ts ASC NULLS LAST
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

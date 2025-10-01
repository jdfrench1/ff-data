export interface Season {
  season_id: number;
  year: number;
}

export interface Game {
  game_id: number;
  nflfast_game_id: string | null;
  season: number;
  week: number;
  home_team: string;
  away_team: string;
  home_points: number | null;
  away_points: number | null;
  kickoff_ts: string | null;
}

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`API ${response.status}: ${body || response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export function fetchSeasons(): Promise<Season[]> {
  return request<Season[]>('/api/seasons');
}

export function fetchGames(season: number): Promise<Game[]> {
  const params = new URLSearchParams({ season: season.toString() });
  return request<Game[]>(`/api/games?${params.toString()}`);
}

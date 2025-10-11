export interface PlayerSummary {
  player_id: number
  full_name: string
  position: string | null
  team_code: string | null
  team_name: string | null
}

export interface PlayerTimelineEntry {
  season: number
  week: number
  team_code: string | null
  team_name: string | null
  kickoff_ts: string | null
  games_played: number
  pass_att: number | null
  pass_cmp: number | null
  pass_yds: number | null
  pass_td: number | null
  int_thrown: number | null
  rush_att: number | null
  rush_yds: number | null
  rush_td: number | null
  targets: number | null
  receptions: number | null
  rec_yds: number | null
  rec_td: number | null
  tackles: number | null
  sacks: number | null
  interceptions: number | null
  fumbles: number | null
  fantasy_ppr: number | null
  snaps_off: number | null
  snaps_def: number | null
  snaps_st: number | null
}

export interface PlayerTeamEvent {
  team_code: string
  team_name: string | null
  start_season: number
  start_week: number
  end_season: number
  end_week: number
}

export interface PlayerTimelineResponse {
  player_id: number
  full_name: string
  position: string | null
  timeline: PlayerTimelineEntry[]
  team_events: PlayerTeamEvent[]
}

const API_BASE =
  import.meta.env.VITE_API_BASE?.replace(/\/$/, '') ?? 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
    },
    ...init,
  })

  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || response.statusText)
  }

  return response.json() as Promise<T>
}

export function searchPlayers(search: string): Promise<PlayerSummary[]> {
  const params = new URLSearchParams({ search })
  return request<PlayerSummary[]>(`/api/v1/players?${params.toString()}`)
}

export function fetchPlayerTimeline(
  playerId: number,
  season?: number,
): Promise<PlayerTimelineResponse> {
  const params = new URLSearchParams()
  if (season) {
    params.set('season', String(season))
  }
  const query = params.toString()
  const suffix = query ? `?${query}` : ''
  return request<PlayerTimelineResponse>(
    `/api/v1/players/${playerId}/timeline${suffix}`,
  )
}

import { useCallback, useEffect, useMemo, useState } from 'react';
import './App.css';
import { fetchGames, fetchSeasons } from './api';
import type { Game, Season } from './api';

type RetryContext = 'seasons' | 'games' | null;

function formatKickoff(value: string | null): string {
  if (!value) return 'TBD';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function parseKickoff(value: string | null): number | null {
  if (!value) {
    return null;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date.getTime();
}

function App() {
  const [seasons, setSeasons] = useState<Season[]>([]);
  const [selectedSeason, setSelectedSeason] = useState<number | null>(null);
  const [games, setGames] = useState<Game[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryContext, setRetryContext] = useState<RetryContext>(null);
  const [weekFilter, setWeekFilter] = useState<number | 'all'>('all');
  const [teamQuery, setTeamQuery] = useState('');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  const loadSeasons = useCallback(async () => {
    setLoading(true);
    setError(null);
    setRetryContext(null);
    try {
      const data = await fetchSeasons();
      setSeasons(data);
      setSelectedSeason((previous) => {
        if (previous !== null && data.some((season) => season.year === previous)) {
          return previous;
        }
        return data[0]?.year ?? null;
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to load seasons.';
      setError(message);
      setRetryContext('seasons');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadGames = useCallback(async (season: number) => {
    setLoading(true);
    setError(null);
    setRetryContext(null);
    try {
      const data = await fetchGames(season);
      setGames(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to load games.';
      setError(message);
      setRetryContext('games');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSeasons();
  }, [loadSeasons]);

  useEffect(() => {
    if (selectedSeason === null) {
      setGames([]);
      return;
    }
    loadGames(selectedSeason);
  }, [selectedSeason, loadGames]);

  useEffect(() => {
    setWeekFilter('all');
    setTeamQuery('');
    setSortOrder('asc');
  }, [selectedSeason]);

  const availableWeeks = useMemo(() => {
    return Array.from(new Set(games.map((game) => game.week))).sort((a, b) => a - b);
  }, [games]);

  const filteredWeeks = useMemo(() => {
    const query = teamQuery.trim().toLowerCase();
    const filtered = games.filter((game) => {
      const matchesWeek = weekFilter === 'all' || game.week === weekFilter;
      if (!matchesWeek) {
        return false;
      }
      if (!query) {
        return true;
      }
      return (
        game.home_team.toLowerCase().includes(query) ||
        game.away_team.toLowerCase().includes(query)
      );
    });

    const sorted = filtered.slice().sort((a, b) => {
      const aTime = parseKickoff(a.kickoff_ts);
      const bTime = parseKickoff(b.kickoff_ts);
      if (aTime === bTime) {
        return a.game_id - b.game_id;
      }
      if (aTime === null) {
        return 1;
      }
      if (bTime === null) {
        return -1;
      }
      if (sortOrder === 'asc') {
        return aTime - bTime;
      }
      return bTime - aTime;
    });

    const grouped = new Map<number, Game[]>();
    sorted.forEach((game) => {
      const bucket = grouped.get(game.week) ?? [];
      bucket.push(game);
      grouped.set(game.week, bucket);
    });

    return Array.from(grouped.entries()).sort((a, b) => a[0] - b[0]);
  }, [games, weekFilter, teamQuery, sortOrder]);

  const noGamesForSeason = !loading && !error && games.length === 0 && selectedSeason !== null;
  const noGamesForFilters = !loading && !error && games.length > 0 && filteredWeeks.length === 0;

  const handleRetry = useCallback(() => {
    if (retryContext === 'seasons') {
      loadSeasons();
      return;
    }
    if (retryContext === 'games' && selectedSeason !== null) {
      loadGames(selectedSeason);
    }
  }, [retryContext, loadSeasons, loadGames, selectedSeason]);

  return (
    <div className='app'>
      <header className='app__header'>
        <h1>NFL Season Dashboard</h1>
        <div className='app__controls'>
          <label htmlFor='season-select'>Season</label>
          <select
            id='season-select'
            value={selectedSeason ?? ''}
            onChange={(event) => {
              const value = Number(event.target.value);
              setSelectedSeason(Number.isNaN(value) ? null : value);
            }}
          >
            {seasons.map((season) => (
              <option key={season.season_id} value={season.year}>
                {season.year}
              </option>
            ))}
          </select>
        </div>
      </header>

      <div className='filters'>
        <div className='filters__group'>
          <label htmlFor='week-filter'>Week</label>
          <select
            id='week-filter'
            value={weekFilter === 'all' ? 'all' : weekFilter.toString()}
            onChange={(event) => {
              const value = event.target.value;
              setWeekFilter(value === 'all' ? 'all' : Number(value));
            }}
            disabled={availableWeeks.length === 0}
          >
            <option value='all'>All weeks</option>
            {availableWeeks.map((week) => (
              <option key={week} value={week.toString()}>
                Week {week}
              </option>
            ))}
          </select>
        </div>

        <div className='filters__group'>
          <label htmlFor='team-filter'>Team</label>
          <input
            id='team-filter'
            type='search'
            placeholder='Search by team'
            value={teamQuery}
            onChange={(event) => setTeamQuery(event.target.value)}
            disabled={games.length === 0}
          />
        </div>

        <div className='filters__group'>
          <label htmlFor='sort-order'>Sort by kickoff</label>
          <select
            id='sort-order'
            value={sortOrder}
            onChange={(event) => setSortOrder(event.target.value as 'asc' | 'desc')}
            disabled={games.length === 0}
          >
            <option value='asc'>Earliest first</option>
            <option value='desc'>Latest first</option>
          </select>
        </div>
      </div>

      {error ? (
        <div className='app__status app__status--error'>
          <span>{error}</span>
          {retryContext ? (
            <button type='button' onClick={handleRetry} disabled={loading}>
              Retry
            </button>
          ) : null}
        </div>
      ) : null}

      {loading ? <div className='app__status'>Loading data...</div> : null}

      {noGamesForSeason ? (
        <div className='app__status'>No games found for this season.</div>
      ) : null}

      {noGamesForFilters ? (
        <div className='app__status'>No games match the current filters.</div>
      ) : null}

      <div className='week-grid'>
        {filteredWeeks.map(([weekNumber, weekGames]) => (
          <section key={weekNumber} className='week'>
            <h2>Week {weekNumber}</h2>
            <table>
              <thead>
                <tr>
                  <th>Kickoff</th>
                  <th>Matchup</th>
                  <th>Score</th>
                </tr>
              </thead>
              <tbody>
                {weekGames.map((game) => {
                  const isFinal = game.home_points !== null && game.away_points !== null;
                  return (
                    <tr key={game.game_id} className={isFinal ? 'game-row game-row--final' : 'game-row'}>
                      <td>{formatKickoff(game.kickoff_ts)}</td>
                      <td>
                        {game.away_team} @ {game.home_team}
                      </td>
                      <td className='game-row__score'>
                        {isFinal ? (
                          <>
                            <span>
                              {game.away_points} - {game.home_points}
                            </span>
                            <span className='game-row__badge game-row__badge--final'>Final</span>
                          </>
                        ) : (
                          <>
                            <span>-</span>
                            <span className='game-row__badge game-row__badge--scheduled'>Scheduled</span>
                          </>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </section>
        ))}
      </div>
    </div>
  );
}

export default App;

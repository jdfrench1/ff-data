import { useEffect, useMemo, useState } from 'react';
import './App.css';
import { fetchGames, fetchSeasons } from './api';
import type { Game, Season } from './api';

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

function App() {
  const [seasons, setSeasons] = useState<Season[]>([]);
  const [selectedSeason, setSelectedSeason] = useState<number | null>(null);
  const [games, setGames] = useState<Game[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSeasons()
      .then((data) => {
        setSeasons(data);
        if (data.length > 0) {
          setSelectedSeason(data[0].year);
        }
      })
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!selectedSeason) {
      return;
    }
    setLoading(true);
    setError(null);
    fetchGames(selectedSeason)
      .then((data) => {
        setGames(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [selectedSeason]);

  const weeks = useMemo(() => {
    const grouped = new Map<number, Game[]>();
    games.forEach((game) => {
      const list = grouped.get(game.week) ?? [];
      list.push(game);
      grouped.set(game.week, list);
    });
    return Array.from(grouped.entries()).sort((a, b) => a[0] - b[0]);
  }, [games]);

  return (
    <div className="app">
      <header className="app__header">
        <h1>NFL Season Dashboard</h1>
        <div className="app__controls">
          <label htmlFor="season-select">Season</label>
          <select
            id="season-select"
            value={selectedSeason ?? ''}
            onChange={(event) => setSelectedSeason(Number(event.target.value))}
          >
            {seasons.map((season) => (
              <option key={season.season_id} value={season.year}>
                {season.year}
              </option>
            ))}
          </select>
        </div>
      </header>

      {error ? (
        <div className="app__status app__status--error">{error}</div>
      ) : null}
      {loading ? <div className="app__status">Loading games…</div> : null}

      {!loading && weeks.length === 0 ? (
        <div className="app__status">No games found for this season.</div>
      ) : null}

      <div className="week-grid">
        {weeks.map(([weekNumber, weekGames]) => (
          <section key={weekNumber} className="week">
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
                {weekGames.map((game) => (
                  <tr key={game.game_id}>
                    <td>{formatKickoff(game.kickoff_ts)}</td>
                    <td>{game.away_team} @ {game.home_team}</td>
                    <td>
                      {game.home_points !== null && game.away_points !== null
                        ? `${game.away_points} - ${game.home_points}`
                        : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        ))}
      </div>
    </div>
  );
}

export default App;



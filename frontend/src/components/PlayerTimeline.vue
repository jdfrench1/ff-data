<template>
  <section class="panel panel--timeline">
    <div v-if="loading" class="panel__status">Loading player timeline&hellip;</div>
    <div v-else-if="error" class="panel__status panel__status--error">{{ error }}</div>
    <div v-else-if="!timeline" class="panel__status">
      Select a player to view their weekly production.
    </div>
    <div v-else class="timeline">
      <header class="timeline__header">
        <div>
          <h2>{{ timeline.full_name }}</h2>
          <p class="timeline__meta">
            <span v-if="timeline.position">{{ timeline.position }}</span>
            <span v-if="timeline.team_events.length">
              Current team: {{ latestTeamLabel }}
            </span>
            <span v-else>No team history recorded</span>
          </p>
        </div>
      </header>

      <section class="timeline__chart" v-if="sparklinePath">
        <header class="timeline__chart-header">
          <h3>Fantasy PPR Trend</h3>
          <p>Weekly totals aggregated per team assignment.</p>
        </header>
        <svg viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden="true">
          <defs>
            <linearGradient id="sparklineGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#4cc0f6" stop-opacity="0.6" />
              <stop offset="100%" stop-color="#4cc0f6" stop-opacity="0.05" />
            </linearGradient>
          </defs>
          <path class="timeline__sparkline" :d="sparklinePath" />
          <path class="timeline__sparkline-fill" :d="sparklineFillPath" />
        </svg>
        <footer class="timeline__chart-footer">
          <span>Min: {{ fantasySummary.min }}</span>
          <span>Avg: {{ fantasySummary.avg }}</span>
          <span>Max: {{ fantasySummary.max }}</span>
        </footer>
      </section>

      <section v-if="timeline.team_events.length" class="timeline__events">
        <header>
          <h3>Team Assignments</h3>
          <p>
            Highlights indicate when the player changed teams during the selected
            seasons.
          </p>
        </header>
        <ul>
          <li v-for="event in timeline.team_events" :key="eventKey(event)">
            <strong>{{ event.team_code }}</strong>
            <span>{{ event.team_name ?? 'Unnamed team' }}</span>
            <span>
              {{ event.start_season }} wk {{ event.start_week }}
              &ndash;
              {{ formatEnd(event) }}
            </span>
          </li>
        </ul>
      </section>

      <section class="timeline__table" v-if="rows.length">
        <header>
          <h3>Weekly Production</h3>
          <p>Totals are aggregated per team each week.</p>
        </header>
        <table>
          <thead>
            <tr>
              <th scope="col">Season</th>
              <th scope="col">Week</th>
              <th scope="col">Team</th>
              <th scope="col">Fantasy</th>
              <th scope="col">Pass Yds</th>
              <th scope="col">Rush Yds</th>
              <th scope="col">Rec Yds</th>
              <th scope="col">TDs</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in rows"
              :key="`${row.entry.season}-${row.entry.week}-${row.entry.team_code ?? 'NA'}`"
              :class="{ 'timeline__row--change': row.isTeamChange }"
            >
              <td>{{ row.entry.season }}</td>
              <td>{{ row.entry.week }}</td>
              <td>
                <span class="team-chip">
                  {{ row.entry.team_code ?? 'N/A' }}
                </span>
                <span v-if="row.isTeamChange" class="team-chip team-chip--alert">
                  Team change
                </span>
              </td>
              <td>{{ formatDecimal(row.entry.fantasy_ppr) }}</td>
              <td>{{ formatInteger(row.entry.pass_yds) }}</td>
              <td>{{ formatInteger(row.entry.rush_yds) }}</td>
              <td>{{ formatInteger(row.entry.rec_yds) }}</td>
              <td>{{ formatInteger(totalTouchdowns(row.entry)) }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { PlayerTimelineResponse, PlayerTimelineEntry, PlayerTeamEvent } from '@/api'

const props = defineProps<{
  timeline: PlayerTimelineResponse | null
  loading: boolean
  error: string | null
}>()

const sparklinePoints = computed<string[] | undefined>(() => {
  if (!props.timeline?.timeline.length) {
    return undefined
  }
  const entries = props.timeline.timeline
  const values = entries.map((entry) => entry.fantasy_ppr ?? 0)
  if (!values.length) {
    return undefined
  }
  const max = Math.max(...values)
  const min = Math.min(...values)
  const range = Math.max(max - min, 1)
  const denominator = Math.max(values.length - 1, 1)

  return values.map((value, index) => {
    const x = (index / denominator) * 100
    const normalized = range === 0 ? 0 : ((value - min) / range) * 100
    const y = 100 - normalized
    return `${x},${y}`
  })
})

const sparklinePath = computed<string | undefined>(() => {
  const points = sparklinePoints.value
  if (!points) {
    return undefined
  }
  if (points.length === 1) {
    const [point] = points
    return `M0,100 L${point} L100,100`
  }
  return `M${points[0]} ${points.slice(1).map((point) => `L${point}`).join(' ')}`
})

const sparklineFillPath = computed<string | undefined>(() => {
  const points = sparklinePoints.value
  if (!points || points.length === 0) {
    return undefined
  }
  if (points.length === 1) {
    const [point] = points
    return `M${point} L${point.split(',')[0]},100 L0,100 Z`
  }
  const path = [`M${points[0]}`]
  for (let i = 1; i < points.length; i += 1) {
    path.push(`L${points[i]}`)
  }
  const last = points[points.length - 1].split(',')[0]
  path.push(`L${last},100`, 'L0,100', 'Z')
  return path.join(' ')
})

const fantasySummary = computed(() => {
  if (!props.timeline?.timeline.length) {
    return { min: '—', max: '—', avg: '—' }
  }
  const values = props.timeline.timeline
    .map((entry) => entry.fantasy_ppr ?? 0)
    .filter((value) => Number.isFinite(value))
  if (!values.length) {
    return { min: '—', max: '—', avg: '—' }
  }
  const min = Math.min(...values)
  const max = Math.max(...values)
  const avg = values.reduce((total, value) => total + value, 0) / values.length
  return {
    min: formatDecimal(min),
    max: formatDecimal(max),
    avg: formatDecimal(avg),
  }
})

const rows = computed(() => {
  if (!props.timeline?.timeline.length) {
    return []
  }
  const grouped: { entry: PlayerTimelineEntry; isTeamChange: boolean }[] = []
  let previousTeam: string | null = null
  for (const entry of props.timeline.timeline) {
    const teamCode = entry.team_code ?? null
    const isChange = teamCode !== null && teamCode !== previousTeam
    if (teamCode !== null) {
      previousTeam = teamCode
    }
    grouped.push({ entry, isTeamChange: isChange })
  }
  return grouped
})

const latestTeamLabel = computed(() => {
  if (!props.timeline?.team_events.length) {
    return 'Unknown'
  }
  const last = props.timeline.team_events[props.timeline.team_events.length - 1]
  const endLabel =
    last.end_season === last.start_season && last.end_week === last.start_week
      ? `since ${last.start_season} wk ${last.start_week}`
      : `through ${last.end_season} wk ${last.end_week}`
  return `${last.team_code} (${endLabel})`
})

const integerFormatter = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 0,
})
const decimalFormatter = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 1,
})

function formatInteger(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return '—'
  }
  return integerFormatter.format(value)
}

function formatDecimal(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return '—'
  }
  return decimalFormatter.format(value)
}

function totalTouchdowns(entry: PlayerTimelineEntry): number {
  return (
    (entry.pass_td ?? 0) + (entry.rush_td ?? 0) + (entry.rec_td ?? 0)
  )
}

function eventKey(event: PlayerTeamEvent): string {
  return `${event.team_code}-${event.start_season}-${event.start_week}-${event.end_season}-${event.end_week}`
}

function formatEnd(event: PlayerTeamEvent): string {
  if (event.end_season === event.start_season && event.end_week === event.start_week) {
    return `${event.end_season} wk ${event.end_week}`
  }
  return `${event.end_season} wk ${event.end_week}`
}
</script>

<style scoped>
.panel {
  background: rgba(8, 17, 29, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 1rem;
  padding: clamp(1.5rem, 2vw, 2.5rem);
  box-shadow: 0 16px 38px rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(12px);
  min-height: 100%;
}

.panel__status {
  margin: 0;
  font-size: 1rem;
  color: rgba(246, 248, 250, 0.75);
}

.panel__status--error {
  color: #ff9c9c;
}

.timeline {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.timeline__header h2 {
  font-size: clamp(1.5rem, 2.5vw, 2.25rem);
  margin-bottom: 0.5rem;
}

.timeline__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
  color: rgba(246, 248, 250, 0.7);
}

.timeline__chart {
  background: rgba(13, 24, 37, 0.85);
  border-radius: 1rem;
  padding: 1.5rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.timeline__chart-header h3 {
  margin: 0 0 0.35rem;
  font-size: 1.1rem;
}

.timeline__chart-header p {
  margin: 0 0 1.25rem;
  color: rgba(246, 248, 250, 0.65);
  font-size: 0.9rem;
}

.timeline__sparkline {
  fill: none;
  stroke: #4cc0f6;
  stroke-width: 0.9;
}

.timeline__sparkline-fill {
  fill: url(#sparklineGradient);
  stroke: none;
}

.timeline__chart-footer {
  display: flex;
  gap: 1.5rem;
  margin-top: 1rem;
  font-size: 0.9rem;
  color: rgba(246, 248, 250, 0.7);
}

.timeline__events header h3,
.timeline__table header h3 {
  margin-bottom: 0.35rem;
  font-size: 1.1rem;
}

.timeline__events header p,
.timeline__table header p {
  margin: 0 0 1rem;
  color: rgba(246, 248, 250, 0.65);
  font-size: 0.9rem;
}

.timeline__events ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 0.75rem;
}

.timeline__events li {
  display: grid;
  gap: 0.25rem;
  padding: 0.75rem 1rem;
  border: 1px solid rgba(76, 192, 246, 0.2);
  background: rgba(76, 192, 246, 0.08);
  border-radius: 0.75rem;
}

.timeline__table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.95rem;
  background: rgba(13, 24, 37, 0.65);
  border-radius: 1rem;
  overflow: hidden;
}

.timeline__table th,
.timeline__table td {
  padding: 0.75rem 1rem;
  text-align: left;
}

.timeline__table thead th {
  background: rgba(8, 17, 29, 0.85);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-size: 0.8rem;
}

.timeline__table tbody tr:nth-child(even) {
  background: rgba(255, 255, 255, 0.02);
}

.timeline__row--change {
  background: rgba(76, 192, 246, 0.08);
}

.team-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  background: rgba(76, 192, 246, 0.15);
  border: 1px solid rgba(76, 192, 246, 0.35);
  border-radius: 999px;
  padding: 0.15rem 0.6rem;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.team-chip--alert {
  margin-left: 0.5rem;
  background: rgba(255, 201, 87, 0.2);
  border-color: rgba(255, 201, 87, 0.5);
  color: #ffd879;
}

@media (max-width: 768px) {
  .timeline__chart-footer {
    flex-direction: column;
    gap: 0.35rem;
  }

  .timeline__table th,
  .timeline__table td {
    padding: 0.6rem 0.75rem;
  }
}
</style>

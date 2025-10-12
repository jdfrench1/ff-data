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

      <section class="timeline__chart" v-if="chartGeometry">
        <header class="timeline__chart-header">
          <h3>Fantasy PPR Trend</h3>
          <p>Weekly totals aggregated per team assignment.</p>
        </header>

        <div class="timeline__chart-controls">
          <fieldset class="chart-control">
            <legend>Scale</legend>
            <label>
              <input
                type="radio"
                name="timelineScale"
                value="auto"
                v-model="chartOptions.scaleMode"
              />
              Auto
            </label>
            <label>
              <input
                type="radio"
                name="timelineScale"
                value="manual"
                v-model="chartOptions.scaleMode"
              />
              Manual
            </label>
            <div
              v-if="chartOptions.scaleMode === 'manual'"
              class="chart-control__range"
            >
              <label>
                Min
                <input
                  type="number"
                  step="0.1"
                  v-model.number="chartOptions.manualMin"
                />
              </label>
              <label>
                Max
                <input
                  type="number"
                  step="0.1"
                  v-model.number="chartOptions.manualMax"
                />
              </label>
            </div>
            <p
              v-if="chartOptions.scaleMode === 'manual' && !manualScaleValid"
              class="chart-control__warning"
            >
              Max must be greater than min.
            </p>
          </fieldset>

          <fieldset class="chart-control">
            <legend>Overlays</legend>
            <label>
              <input type="checkbox" v-model="chartOptions.showAverageLine" />
              Average line
            </label>
            <label>
              <input type="checkbox" v-model="chartOptions.showTeamEvents" />
              Team changes
            </label>
            <label>
              <input
                type="checkbox"
                v-model="chartOptions.showSeasonIndicators"
              />
              Season markers
            </label>
          </fieldset>
        </div>

        <svg viewBox="0 0 120 80" preserveAspectRatio="none" aria-hidden="true">
          <defs>
            <linearGradient id="sparklineGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#4cc0f6" stop-opacity="0.6" />
              <stop offset="100%" stop-color="#4cc0f6" stop-opacity="0.05" />
            </linearGradient>
          </defs>

          <g class="timeline__chart-grid">
            <line
              class="timeline__axis-line"
              :x1="chartGeometry.leftX"
              :y1="chartGeometry.topY"
              :x2="chartGeometry.leftX"
              :y2="chartGeometry.bottomY"
            />
            <line
              class="timeline__axis-line"
              :x1="chartGeometry.leftX"
              :y1="chartGeometry.bottomY"
              :x2="chartGeometry.rightX"
              :y2="chartGeometry.bottomY"
            />
            <g v-for="tick in yTicks" :key="`y-${tick.value}`">
              <line
                class="timeline__grid-line"
                :x1="chartGeometry.leftX"
                :x2="chartGeometry.rightX"
                :y1="tick.y"
                :y2="tick.y"
              />
              <text
                class="timeline__tick-label"
                :x="chartGeometry.leftX - 2"
                :y="tick.y"
                dominant-baseline="middle"
                text-anchor="end"
              >
                {{ tick.label }}
              </text>
            </g>
          </g>

          <g
            v-if="chartOptions.showSeasonIndicators && seasonIndicators.length"
            class="timeline__season-markers"
          >
            <g
              v-for="marker in seasonIndicators"
              :key="`season-${marker.season}`"
            >
              <line
                v-if="marker.isBoundary"
                class="timeline__season-line"
                :x1="marker.x"
                :x2="marker.x"
                :y1="chartGeometry.topY"
                :y2="chartGeometry.bottomY"
              />
              <text
                class="timeline__season-label"
                :x="marker.x"
                :y="chartGeometry.bottomY + 6"
                text-anchor="middle"
              >
                {{ marker.season }}
              </text>
            </g>
          </g>

          <g
            v-if="chartOptions.showTeamEvents && teamChangeMarkers.length"
            class="timeline__team-markers"
          >
            <g v-for="marker in teamChangeMarkers" :key="marker.key">
              <line
                class="timeline__team-marker-line"
                :x1="marker.x"
                :x2="marker.x"
                :y1="chartGeometry.topY"
                :y2="chartGeometry.bottomY"
              />
              <text
                class="timeline__team-marker-label"
                :x="marker.x"
                :y="marker.labelY"
                text-anchor="middle"
              >
                {{ marker.team }}
              </text>
            </g>
          </g>

          <path
            v-if="chartGeometry.fillPath"
            class="timeline__sparkline-fill"
            :d="chartGeometry.fillPath"
          />
          <path
            v-if="chartGeometry.path"
            class="timeline__sparkline"
            :d="chartGeometry.path"
          />

          <line
            v-if="averageLine"
            class="timeline__average-line"
            :x1="chartGeometry.leftX"
            :x2="chartGeometry.rightX"
            :y1="averageLine.y"
            :y2="averageLine.y"
          />
          <text
            v-if="averageLine"
            class="timeline__average-label"
            :x="chartGeometry.rightX + 4"
            :y="averageLine.y"
            dominant-baseline="middle"
          >
            Avg {{ averageLine.label }}
          </text>

          <g v-if="axisLabelPositions" class="timeline__axis-labels">
            <text
              class="timeline__axis-label timeline__axis-label--x"
              :x="axisLabelPositions.x.x"
              :y="axisLabelPositions.x.y"
              text-anchor="middle"
            >
              {{ axisLabels.x }}
            </text>
            <text
              class="timeline__axis-label timeline__axis-label--y"
              :x="axisLabelPositions.y.x"
              :y="axisLabelPositions.y.y"
              :transform="axisLabelPositions.y.transform"
              text-anchor="middle"
              dominant-baseline="middle"
            >
              {{ axisLabels.y }}
            </text>
          </g>
        </svg>

        <footer class="timeline__chart-footer">
          <span>Min: {{ fantasySummary.minLabel }}</span>
          <span>Avg: {{ fantasySummary.avgLabel }}</span>
          <span>Max: {{ fantasySummary.maxLabel }}</span>
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
import { computed, reactive, watch } from 'vue'
import type { PlayerTimelineResponse, PlayerTimelineEntry, PlayerTeamEvent } from '@/api'

const props = defineProps<{
  timeline: PlayerTimelineResponse | null
  loading: boolean
  error: string | null
}>()

type ScaleMode = 'auto' | 'manual'

const chartOptions = reactive({
  scaleMode: 'auto' as ScaleMode,
  manualMin: 0,
  manualMax: 40,
  showAverageLine: true,
  showTeamEvents: true,
  showSeasonIndicators: true,
})

const CHART_VIEWBOX_WIDTH = 120
const CHART_VIEWBOX_HEIGHT = 80
const CHART_PADDING = {
  top: 16,
  right: 12,
  bottom: 28,
  left: 20,
} as const

const AXIS_LABELS = {
  x: 'Week',
  y: 'Fantasy PPR',
} as const
const axisLabels = AXIS_LABELS

interface ChartPoint {
  entry: PlayerTimelineEntry
  index: number
  value: number
  x: number
  y: number
}

interface ChartGeometry {
  points: ChartPoint[]
  path: string
  fillPath: string
  leftX: number
  rightX: number
  topY: number
  bottomY: number
  domainMin: number
  domainMax: number
  range: number
  valueToY: (value: number) => number
  indexToX: (index: number) => number
  yTicks: number[]
}

watch(
  () => props.timeline?.player_id,
  () => {
    if (!props.timeline?.timeline.length) {
      return
    }
    const values = props.timeline.timeline.map((entry) => entry.fantasy_ppr ?? 0)
    if (!values.length) {
      return
    }
    const min = Math.min(...values)
    const max = Math.max(...values)
    const correctedMax = max === min ? max + 5 : max
    chartOptions.manualMin = Math.floor(min)
    chartOptions.manualMax = Math.ceil(correctedMax)
  },
  { immediate: true },
)

const manualScaleValid = computed(
  () => chartOptions.manualMax > chartOptions.manualMin,
)

const fantasySummary = computed(() => {
  if (!props.timeline?.timeline.length) {
    return {
      minLabel: '--',
      avgLabel: '--',
      maxLabel: '--',
      averageValue: null as number | null,
    }
  }
  const values = props.timeline.timeline.map((entry) => entry.fantasy_ppr ?? 0)
  if (!values.length) {
    return {
      minLabel: '--',
      avgLabel: '--',
      maxLabel: '--',
      averageValue: null,
    }
  }
  const min = Math.min(...values)
  const max = Math.max(...values)
  const avg =
    values.reduce((total, value) => total + value, 0) / values.length

  return {
    minLabel: formatDecimal(min),
    avgLabel: formatDecimal(avg),
    maxLabel: formatDecimal(max),
    averageValue: avg,
  }
})

const chartGeometry = computed<ChartGeometry | null>(() => {
  if (!props.timeline?.timeline.length) {
    return null
  }

  const entries = props.timeline.timeline
  const values = entries.map((entry) => entry.fantasy_ppr ?? 0)
  if (!values.length) {
    return null
  }

  const autoMin = Math.min(...values)
  const autoMax = Math.max(...values)

  let domainMin = autoMin
  let domainMax = autoMax

  if (chartOptions.scaleMode === 'manual' && manualScaleValid.value) {
    domainMin = chartOptions.manualMin
    domainMax = chartOptions.manualMax
  } else {
    const range = autoMax - autoMin
    if (range === 0) {
      const padding = Math.max(Math.abs(autoMax) * 0.1, 5)
      domainMin = autoMin - padding
      domainMax = autoMax + padding
    } else {
      const padding = range * 0.1
      domainMin = autoMin - padding
      domainMax = autoMax + padding
    }
  }

  if (domainMin === domainMax) {
    domainMin -= 5
    domainMax += 5
  }

  const range = domainMax - domainMin || 1
  const denominator = Math.max(entries.length - 1, 1)
  const plotWidth =
    CHART_VIEWBOX_WIDTH - CHART_PADDING.left - CHART_PADDING.right
  const plotHeight =
    CHART_VIEWBOX_HEIGHT - CHART_PADDING.top - CHART_PADDING.bottom
  const leftX = CHART_PADDING.left
  const rightX = leftX + plotWidth
  const topY = CHART_PADDING.top
  const bottomY = topY + plotHeight

  const clamp = (value: number, min: number, max: number) =>
    Math.min(Math.max(value, min), max)

  const indexToX = (index: number) => {
    if (entries.length === 1) {
      return leftX + plotWidth / 2
    }
    return leftX + (index / denominator) * plotWidth
  }

  const valueToY = (value: number) => {
    const normalized = (value - domainMin) / range
    const clamped = clamp(normalized, 0, 1)
    return topY + (1 - clamped) * plotHeight
  }

  const points: ChartPoint[] = entries.map((entry, index) => {
    const value = entry.fantasy_ppr ?? 0
    return {
      entry,
      index,
      value,
      x: indexToX(index),
      y: valueToY(value),
    }
  })

  let path = ''
  let fillPath = ''
  if (points.length === 1) {
    const point = points[0]
    const y = point.y
    path = `M${leftX},${y} L${rightX},${y}`
    fillPath = `M${leftX},${bottomY} L${leftX},${y} L${rightX},${y} L${rightX},${bottomY} Z`
  } else if (points.length > 1) {
    path = points
      .map((point, index) => `${index === 0 ? 'M' : 'L'}${point.x},${point.y}`)
      .join(' ')
    const commands = [
      `M${points[0].x},${bottomY}`,
      `L${points[0].x},${points[0].y}`,
    ]
    for (let i = 1; i < points.length; i += 1) {
      commands.push(`L${points[i].x},${points[i].y}`)
    }
    commands.push(
      `L${points[points.length - 1].x},${bottomY}`,
      `L${points[0].x},${bottomY}`,
      'Z',
    )
    fillPath = commands.join(' ')
  }

  const rawTicks = [domainMin, domainMin + range / 2, domainMax]
  const yTicks = rawTicks.filter((value, index, arr) => {
    const previousIndex = arr.findIndex(
      (candidate) =>
        Math.abs(candidate - value) < Math.max(range * 0.05, 1e-6),
    )
    return previousIndex === index
  })

  yTicks.sort((a, b) => a - b)

  return {
    points,
    path,
    fillPath,
    leftX,
    rightX,
    topY,
    bottomY,
    domainMin,
    domainMax,
    range,
    valueToY,
    indexToX,
    yTicks,
  }
})

const yTicks = computed(() => {
  const geometry = chartGeometry.value
  if (!geometry) {
    return []
  }
  const ticks =
    geometry.yTicks.length > 0
      ? geometry.yTicks
      : [geometry.domainMin, geometry.domainMax]

  return ticks.map((value) => ({
    value,
    y: geometry.valueToY(value),
    label: formatDecimal(value),
  }))
})

const seasonIndicators = computed(() => {
  const geometry = chartGeometry.value
  if (!geometry || !chartOptions.showSeasonIndicators) {
    return []
  }
  const markers: {
    season: number
    x: number
    isBoundary: boolean
  }[] = []
  let previousSeason: number | null = null
  for (const point of geometry.points) {
    const season = point.entry.season
    const isBoundary = previousSeason !== null && season !== previousSeason
    if (previousSeason === null || season !== previousSeason) {
      markers.push({
        season,
        x: point.x,
        isBoundary,
      })
      previousSeason = season
    }
  }
  return markers
})

const teamChangeMarkers = computed(() => {
  const geometry = chartGeometry.value
  if (
    !geometry ||
    !props.timeline?.team_events.length ||
    !chartOptions.showTeamEvents
  ) {
    return []
  }

  const labelY = Math.max(geometry.topY - 4, 6)
  const pointsByKey = new Map<string, ChartPoint>()
  for (const point of geometry.points) {
    const key = `${point.entry.season}-${point.entry.week}`
    pointsByKey.set(key, point)
  }

  return props.timeline.team_events
    .map((event, index) => {
      if (index === 0) {
        return null
      }
      const point = pointsByKey.get(
        `${event.start_season}-${event.start_week}`,
      )
      if (!point) {
        return null
      }
      return {
        key: eventKey(event),
        team: event.team_code,
        x: point.x,
        labelY,
      }
    })
    .filter(
      (
        marker,
      ): marker is { key: string; team: string; x: number; labelY: number } =>
        marker !== null,
    )
})

const averageLine = computed(() => {
  const geometry = chartGeometry.value
  if (!geometry || !chartOptions.showAverageLine) {
    return null
  }
  if (fantasySummary.value.averageValue === null) {
    return null
  }
  return {
    y: geometry.valueToY(fantasySummary.value.averageValue),
    label: fantasySummary.value.avgLabel,
  }
})

const axisLabelPositions = computed(() => {
  const geometry = chartGeometry.value
  if (!geometry) {
    return null
  }
  const xLabelX = (geometry.leftX + geometry.rightX) / 2
  const xLabelY = geometry.bottomY + 12
  const yLabelX = geometry.leftX - 12
  const yLabelY = (geometry.topY + geometry.bottomY) / 2

  return {
    x: {
      x: xLabelX,
      y: xLabelY,
    },
    y: {
      x: yLabelX,
      y: yLabelY,
      transform: `rotate(-90, ${yLabelX}, ${yLabelY})`,
    },
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
    return '--'
  }
  return integerFormatter.format(value)
}

function formatDecimal(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return '--'
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
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
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

.timeline__chart-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem 1.5rem;
  align-items: flex-end;
}

.chart-control {
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 0.75rem;
  padding: 0.75rem 1rem;
  display: grid;
  gap: 0.5rem;
  min-width: 12rem;
}

.chart-control legend {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: rgba(246, 248, 250, 0.6);
  padding: 0 0.25rem;
}

.chart-control label {
  display: flex;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: rgba(246, 248, 250, 0.9);
  align-items: center;
}

.chart-control input[type='number'] {
  margin-top: 0.35rem;
  width: 6rem;
  border-radius: 0.5rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(8, 17, 29, 0.85);
  color: #f6f8fa;
  padding: 0.25rem 0.5rem;
  font-size: 0.85rem;
}

.chart-control__range {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.chart-control__warning {
  margin: 0;
  font-size: 0.8rem;
  color: #ff9c9c;
}

.timeline__chart svg {
  width: 100%;
  height: auto;
}

.timeline__chart-grid {
  stroke-linecap: round;
}

.timeline__axis-line {
  stroke: rgba(246, 248, 250, 0.5);
  stroke-width: 0.6;
}

.timeline__grid-line {
  stroke: rgba(246, 248, 250, 0.14);
  stroke-dasharray: 2 2;
  stroke-width: 0.4;
}

.timeline__tick-label {
  fill: rgba(246, 248, 250, 0.7);
  font-size: 3px;
}

.timeline__season-line {
  stroke: rgba(255, 201, 87, 0.35);
  stroke-width: 0.5;
  stroke-dasharray: 3 3;
}

.timeline__season-label {
  fill: rgba(255, 201, 87, 0.85);
  font-size: 3px;
}

.timeline__team-marker-line {
  stroke: rgba(76, 192, 246, 0.45);
  stroke-width: 0.6;
  stroke-dasharray: 4 2;
}

.timeline__team-marker-label {
  fill: rgba(76, 192, 246, 0.95);
  font-size: 3px;
}

.timeline__sparkline {
  fill: none;
  stroke: #4cc0f6;
  stroke-width: 1.2;
}

.timeline__sparkline-fill {
  fill: url(#sparklineGradient);
  stroke: none;
}

.timeline__average-line {
  stroke: rgba(255, 255, 255, 0.5);
  stroke-width: 0.6;
  stroke-dasharray: 3 2;
}

.timeline__average-label {
  fill: rgba(255, 255, 255, 0.75);
  font-size: 3px;
}

.timeline__axis-labels text {
  fill: rgba(246, 248, 250, 0.7);
  font-size: 3.2px;
}

.timeline__chart-footer {
  display: flex;
  gap: 1.5rem;
  margin-top: 0.5rem;
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
  .timeline__chart-controls {
    flex-direction: column;
    align-items: stretch;
  }

  .chart-control {
    min-width: 0;
  }

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




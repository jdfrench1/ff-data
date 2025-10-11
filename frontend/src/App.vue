<template>
  <div class="app">
    <header class="app__header">
      <div>
        <h1>NFL Player Timeline Explorer</h1>
        <p>
          Search for a player to view their weekly production, fantasy trajectory, and team transitions—all in one place.
        </p>
      </div>
    </header>

    <main class="app__main">
      <PlayerSearchPanel
        v-model="searchTerm"
        :results="searchResults"
        :is-loading="isSearching"
        :error="searchError"
        :selected-id="selectedPlayer?.player_id ?? null"
        @select="handleSelect"
      />

      <PlayerTimeline
        :timeline="timeline"
        :loading="isTimelineLoading"
        :error="timelineError"
      />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import PlayerSearchPanel from './components/PlayerSearchPanel.vue'
import PlayerTimeline from './components/PlayerTimeline.vue'
import {
  type PlayerSummary,
  type PlayerTimelineResponse,
  searchPlayers,
  fetchPlayerTimeline,
} from './api'

const searchTerm = ref('')
const searchResults = ref<PlayerSummary[]>([])
const searchError = ref<string | null>(null)
const isSearching = ref(false)

const selectedPlayer = ref<PlayerSummary | null>(null)
const timeline = ref<PlayerTimelineResponse | null>(null)
const isTimelineLoading = ref(false)
const timelineError = ref<string | null>(null)

let searchTimeout: number | undefined
let activeSearchToken = 0
let activeTimelineToken = 0

watch(
  searchTerm,
  (value) => {
    if (searchTimeout) {
      window.clearTimeout(searchTimeout)
    }

    const trimmed = value.trim()
    if (trimmed.length < 2) {
      searchResults.value = []
      searchError.value = null
      isSearching.value = false
      return
    }

    searchTimeout = window.setTimeout(async () => {
      const token = ++activeSearchToken
      isSearching.value = true
      searchError.value = null
      try {
        const results = await searchPlayers(trimmed)
        if (token === activeSearchToken) {
          searchResults.value = results
        }
      } catch (error) {
        if (token === activeSearchToken) {
          searchResults.value = []
          searchError.value =
            error instanceof Error ? error.message : 'Unable to search players.'
        }
      } finally {
        if (token === activeSearchToken) {
          isSearching.value = false
        }
      }
    }, 275)
  },
  { immediate: true },
)

async function loadTimeline(player: PlayerSummary) {
  const token = ++activeTimelineToken
  isTimelineLoading.value = true
  timelineError.value = null
  timeline.value = null
  try {
    const response = await fetchPlayerTimeline(player.player_id)
    if (token === activeTimelineToken) {
      timeline.value = response
    }
  } catch (error) {
    if (token === activeTimelineToken) {
      timeline.value = null
      timelineError.value =
        error instanceof Error ? error.message : 'Unable to load player timeline.'
    }
  } finally {
    if (token === activeTimelineToken) {
      isTimelineLoading.value = false
    }
  }
}

function handleSelect(player: PlayerSummary) {
  selectedPlayer.value = player
  searchTerm.value = player.full_name
  void loadTimeline(player)
}
</script>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: radial-gradient(circle at top, #16324f 0%, #0b1622 60%, #050b12 100%);
  color: #f6f8fa;
  padding: clamp(1.5rem, 5vw, 3rem) clamp(1rem, 4vw, 4rem);
  box-sizing: border-box;
  gap: 2rem;
}

.app__header {
  display: flex;
  justify-content: center;
  text-align: center;
}

.app__header h1 {
  font-size: clamp(2.25rem, 4vw, 3.25rem);
  margin-bottom: 0.75rem;
}

.app__header p {
  max-width: 46rem;
  margin: 0 auto;
  font-size: clamp(1rem, 2vw, 1.25rem);
  color: rgba(246, 248, 250, 0.82);
  line-height: 1.5;
}

.app__main {
  display: grid;
  grid-template-columns: minmax(20rem, 26rem) minmax(0, 1fr);
  gap: clamp(1.5rem, 3vw, 2.5rem);
  max-width: 1100px;
  margin: 0 auto;
  width: 100%;
}

@media (max-width: 980px) {
  .app__main {
    grid-template-columns: 1fr;
  }
}
</style>

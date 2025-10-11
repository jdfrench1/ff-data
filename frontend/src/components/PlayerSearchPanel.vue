<template>
  <section class="panel">
    <header class="panel__header">
      <h2>Player Search</h2>
      <p>Find a player by name to explore their weekly production timeline.</p>
    </header>

    <div class="panel__body">
      <label class="field">
        <span class="field__label">Player name</span>
        <input
          v-model="model"
          type="search"
          name="playerSearch"
          autocomplete="off"
          placeholder="Start typing &hellip;"
          class="field__input"
        />
      </label>

      <p v-if="error" class="panel__status panel__status--error">{{ error }}</p>
      <p v-else-if="isLoading" class="panel__status">Searching players&hellip;</p>
      <p
        v-else-if="!results.length && model.trim().length >= 2"
        class="panel__status"
      >
        No players matched that search.
      </p>

      <ul v-if="results.length" class="result-list" role="listbox">
        <li
          v-for="player in results"
          :key="player.player_id"
          :class="[
            'result-list__item',
            { 'result-list__item--active': player.player_id === selectedId },
          ]"
        >
          <button type="button" class="result-list__button" @click="select(player)">
            <span class="result-list__name">{{ player.full_name }}</span>
            <span class="result-list__meta">
              <span v-if="player.position" class="result-list__badge">
                {{ player.position }}
              </span>
              <span v-if="player.team_code" class="result-list__badge">
                {{ player.team_code }}
              </span>
            </span>
          </button>
        </li>
      </ul>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { PlayerSummary } from '@/api'

const props = defineProps<{
  modelValue: string
  results: PlayerSummary[]
  isLoading: boolean
  error: string | null
  selectedId: number | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  select: [player: PlayerSummary]
}>()

const model = computed({
  get: () => props.modelValue,
  set: (value: string) => emit('update:modelValue', value),
})

function select(player: PlayerSummary) {
  emit('select', player)
}
</script>

<style scoped>
.panel {
  background: rgba(8, 17, 29, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 1rem;
  padding: clamp(1.5rem, 2vw, 2rem);
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  box-shadow: 0 16px 38px rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(12px);
  min-height: 100%;
}

.panel__header h2 {
  font-size: 1.35rem;
  margin-bottom: 0.35rem;
}

.panel__header p {
  margin: 0;
  color: rgba(246, 248, 250, 0.75);
  font-size: 0.95rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field__label {
  text-transform: uppercase;
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  color: rgba(246, 248, 250, 0.6);
}

.field__input {
  border-radius: 0.75rem;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(13, 24, 37, 0.85);
  color: #f6f8fa;
  padding: 0.75rem 1rem;
  font-size: 1rem;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.field__input:focus {
  outline: none;
  border-color: #4cc0f6;
  box-shadow: 0 0 0 3px rgba(76, 192, 246, 0.25);
}

.panel__status {
  margin: 0;
  font-size: 0.9rem;
  color: rgba(246, 248, 250, 0.75);
}

.panel__status--error {
  color: #ff9c9c;
}

.result-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.result-list__item {
  border-radius: 0.75rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  overflow: hidden;
  background: rgba(12, 22, 34, 0.8);
}

.result-list__item--active {
  border-color: rgba(76, 192, 246, 0.5);
  box-shadow: 0 0 0 2px rgba(76, 192, 246, 0.25);
}

.result-list__button {
  all: unset;
  display: flex;
  width: 100%;
  padding: 0.85rem 1rem;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
}

.result-list__name {
  font-weight: 600;
  font-size: 1rem;
}

.result-list__meta {
  display: flex;
  gap: 0.5rem;
}

.result-list__badge {
  background: rgba(76, 192, 246, 0.15);
  border: 1px solid rgba(76, 192, 246, 0.35);
  border-radius: 999px;
  padding: 0.2rem 0.6rem;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
</style>

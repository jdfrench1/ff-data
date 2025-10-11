<template>
  <div class="app">
    <header class="app__header">
      <h1>Player Timeline Explorer</h1>
      <p>
        Rebuilt frontend in Vue + TypeScript. Select a player to view season-by-season production and
        highlight key transitions.
      </p>
    </header>

    <main class="app__main">
      <section class="app__panel">
        <h2>Player Search</h2>
        <p class="app__placeholder">Interactive search arrives in the next phase.</p>
      </section>

      <section class="app__panel">
        <h2>Timeline</h2>
        <p class="app__placeholder">Stats timeline and team-change highlights coming soon.</p>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
// Placeholder component until the player timeline feature lands in Phase 3.
</script>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: radial-gradient(circle at top, #16324f 0%, #0b1622 60%, #050b12 100%);
  color: #f6f8fa;
  padding: 2rem clamp(1rem, 4vw, 4rem);
  box-sizing: border-box;
}

.app__header {
  max-width: 60rem;
  margin: 0 auto 2.5rem;
  text-align: center;
}

.app__header h1 {
  font-size: clamp(2rem, 4vw, 3rem);
  margin-bottom: 0.75rem;
}

.app__header p {
  font-size: clamp(1rem, 2vw, 1.25rem);
  color: rgba(246, 248, 250, 0.82);
}

.app__main {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(20rem, 1fr));
  gap: 1.5rem;
  max-width: 80rem;
  margin: 0 auto;
  width: 100%;
}

.app__panel {
  background: rgba(8, 17, 29, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 1rem;
  padding: 1.75rem;
  box-shadow: 0 20px 35px rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(12px);
}

.app__panel h2 {
  margin: 0 0 0.75rem;
  font-size: 1.35rem;
}

.app__placeholder {
  margin: 0;
  color: rgba(246, 248, 250, 0.7);
  line-height: 1.5;
}

@media (max-width: 768px) {
  .app {
    padding-inline: 1.25rem;
  }

  .app__main {
    grid-template-columns: 1fr;
  }
}
</style>

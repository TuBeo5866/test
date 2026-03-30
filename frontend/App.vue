<template>
  <div class="app">
    <header class="app-header">
      <div class="header-inner">
        <div class="logo">
          <span class="logo-icon">⬡</span>
          <span class="logo-text">Extension<em>Studio</em></span>
        </div>
        <div class="header-meta">
          <span class="badge">HorizonUI / NekoUI</span>
          <span class="version">by Han's404</span>
        </div>
      </div>
    </header>

    <main class="app-main">
      <div class="layout">
        <section class="panel panel-form">
          <BuildForm @submitted="onSubmitted" :disabled="isBuilding" />
        </section>

        <section class="panel panel-progress">
          <ProgressPanel
            :task-id="taskId"
            :is-building="isBuilding"
            @done="onDone"
            @error="onError"
          />
          <DownloadCard
            v-if="downloadReady || buildError"
            :task-id="taskId"
            :error="buildError"
            @reset="onReset"
          />
        </section>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import BuildForm from './components/BuildForm.vue'
import ProgressPanel from './components/ProgressPanel.vue'
import DownloadCard from './components/DownloadCard.vue'

const taskId = ref(null)
const isBuilding = ref(false)
const downloadReady = ref(false)
const buildError = ref(null)

function onSubmitted(id) {
  taskId.value = id
  isBuilding.value = true
  downloadReady.value = false
  buildError.value = null
}

function onDone() {
  isBuilding.value = false
  downloadReady.value = true
}

function onError(msg) {
  isBuilding.value = false
  buildError.value = msg
}

function onReset() {
  taskId.value = null
  isBuilding.value = false
  downloadReady.value = false
  buildError.value = null
}
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:        #0d0f14;
  --bg2:       #13161e;
  --bg3:       #1a1e2a;
  --border:    #252a38;
  --border2:   #2e3447;
  --accent:    #5b7cfa;
  --accent2:   #7c5bf4;
  --green:     #31c98e;
  --amber:     #f5a623;
  --red:       #f05c5c;
  --text:      #e2e6f0;
  --text2:     #8892aa;
  --text3:     #4e566a;
  --font:      'Syne', sans-serif;
  --mono:      'JetBrains Mono', monospace;
  --radius:    10px;
  --radius-lg: 16px;
}

html { font-size: 16px; }
body {
  font-family: var(--font);
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  overflow-x: hidden;
}

.app-header {
  border-bottom: 1px solid var(--border);
  background: var(--bg2);
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(12px);
}

.header-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 32px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.logo-icon {
  font-size: 1.4rem;
  color: var(--accent);
  line-height: 1;
}

.logo-text em {
  font-style: normal;
  color: var(--accent);
}

.header-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.badge {
  background: #1e2436;
  border: 1px solid var(--border2);
  color: var(--text2);
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 4px 10px;
  border-radius: 20px;
}

.version {
  color: var(--text3);
  font-size: 0.78rem;
}

.app-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 32px 64px;
}

.layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  align-items: start;
}

.panel {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

@media (max-width: 900px) {
  .layout { grid-template-columns: 1fr; }
  .app-main { padding: 20px 16px 48px; }
}
</style>

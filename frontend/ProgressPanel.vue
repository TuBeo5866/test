<template>
  <div class="progress-panel">
    <div class="pp-header">
      <h2>Build Output</h2>
      <div class="pp-status">
        <span class="status-dot" :class="statusClass"></span>
        <span class="status-text">{{ statusLabel }}</span>
      </div>
    </div>

    <!-- Idle state -->
    <div v-if="!taskId && !isBuilding" class="pp-idle">
      <div class="idle-icon">⬡</div>
      <p>Điền form bên trái và bấm <strong>Build Pack</strong> để bắt đầu</p>
    </div>

    <!-- Active / done state -->
    <template v-else>
      <!-- Progress bar -->
      <div class="pp-progress-wrap">
        <div class="pp-progress-bar">
          <div
            class="pp-progress-fill"
            :style="{ width: progress + '%' }"
            :class="{ done: !isBuilding && !error }"
          ></div>
        </div>
        <span class="pp-progress-pct">{{ progress }}%</span>
      </div>

      <!-- Log output -->
      <div class="pp-log" ref="logEl">
        <div
          v-for="(line, i) in logs"
          :key="i"
          class="log-line"
          :class="getLineClass(line)"
        >
          <span class="log-prefix">›</span>
          <span class="log-text">{{ line }}</span>
        </div>
        <div v-if="isBuilding" class="log-line log-cursor">
          <span class="log-prefix">›</span>
          <span class="cursor-blink">▊</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onUnmounted } from 'vue'

const props = defineProps({
  taskId:     { type: String, default: null },
  isBuilding: { type: Boolean, default: false },
})

const emit = defineEmits(['done', 'error'])

const logs     = ref([])
const progress = ref(0)
const error    = ref(null)
const logEl    = ref(null)

let sse = null

const statusClass = computed(() => {
  if (!props.taskId && !props.isBuilding) return 'idle'
  if (props.isBuilding) return 'building'
  if (error.value) return 'error'
  return 'done'
})

const statusLabel = computed(() => {
  if (!props.taskId && !props.isBuilding) return 'Idle'
  if (props.isBuilding) return 'Building…'
  if (error.value) return 'Failed'
  return 'Done'
})

watch(() => props.taskId, (id) => {
  if (!id) return
  logs.value = []
  progress.value = 0
  error.value = null
  startSSE(id)
})

function startSSE(taskId) {
  if (sse) { sse.close(); sse = null }

  sse = new EventSource(`/api/progress/${taskId}`)

  sse.addEventListener('log', (e) => {
    const data = JSON.parse(e.data)
    logs.value.push(data.message)
    scrollToBottom()
  })

  sse.addEventListener('progress', (e) => {
    const data = JSON.parse(e.data)
    progress.value = data.value
  })

  sse.addEventListener('done', (e) => {
    const data = JSON.parse(e.data)
    sse.close()
    sse = null
    if (data.success) {
      progress.value = 100
      logs.value.push('✅ Build completed successfully!')
      emit('done')
    } else {
      error.value = data.message
      logs.value.push('❌ ' + data.message)
      emit('error', data.message)
    }
  })

  sse.onerror = () => {
    if (sse?.readyState === EventSource.CLOSED) return
    sse.close()
    sse = null
    const msg = 'SSE connection lost'
    error.value = msg
    logs.value.push('⚠️ ' + msg)
    emit('error', msg)
  }
}

async function scrollToBottom() {
  await nextTick()
  if (logEl.value) {
    logEl.value.scrollTop = logEl.value.scrollHeight
  }
}

function getLineClass(line) {
  if (line.startsWith('✅') || line.includes('successfully')) return 'log-success'
  if (line.startsWith('❌') || line.includes('Error') || line.includes('failed')) return 'log-error'
  if (line.startsWith('⚠️') || line.includes('Warning') || line.includes('WARN')) return 'log-warn'
  if (line.startsWith('[') && line.includes(']')) return 'log-tag'
  return ''
}

onUnmounted(() => { if (sse) sse.close() })
</script>

<style scoped>
.progress-panel { display: flex; flex-direction: column; min-height: 320px; }

.pp-header {
  padding: 24px 28px 16px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.pp-header h2 { font-size: 1.05rem; font-weight: 700; letter-spacing: -0.01em; }

.pp-status { display: flex; align-items: center; gap: 7px; }
.status-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--text3);
  transition: background 0.3s;
}
.status-dot.building {
  background: var(--accent);
  box-shadow: 0 0 0 0 rgba(91,124,250,0.4);
  animation: pulse 1.2s ease-in-out infinite;
}
.status-dot.done    { background: var(--green); }
.status-dot.error   { background: var(--red); }

@keyframes pulse {
  0%   { box-shadow: 0 0 0 0 rgba(91,124,250,0.4); }
  70%  { box-shadow: 0 0 0 7px rgba(91,124,250,0); }
  100% { box-shadow: 0 0 0 0 rgba(91,124,250,0); }
}

.status-text { font-size: 0.78rem; font-weight: 600; color: var(--text2); }

.pp-idle {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px 28px;
  color: var(--text3);
}
.idle-icon { font-size: 2.5rem; opacity: 0.3; }
.pp-idle p { font-size: 0.82rem; text-align: center; line-height: 1.6; }
.pp-idle strong { color: var(--text2); }

.pp-progress-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 28px 10px;
}

.pp-progress-bar {
  flex: 1;
  height: 6px;
  background: var(--border);
  border-radius: 3px;
  overflow: hidden;
}

.pp-progress-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 3px;
  transition: width 0.4s ease;
  position: relative;
  overflow: hidden;
}

.pp-progress-fill::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.25) 50%, transparent 100%);
  animation: shimmer 1.5s linear infinite;
}

.pp-progress-fill.done {
  background: var(--green);
}
.pp-progress-fill.done::after { display: none; }

@keyframes shimmer {
  from { transform: translateX(-100%); }
  to   { transform: translateX(100%); }
}

.pp-progress-pct {
  font-family: var(--mono);
  font-size: 0.75rem;
  color: var(--text2);
  min-width: 36px;
  text-align: right;
}

.pp-log {
  flex: 1;
  font-family: var(--mono);
  font-size: 0.75rem;
  line-height: 1.7;
  padding: 12px 20px 20px;
  max-height: 320px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--border2) transparent;
}

.pp-log::-webkit-scrollbar { width: 4px; }
.pp-log::-webkit-scrollbar-track { background: transparent; }
.pp-log::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }

.log-line {
  display: flex;
  gap: 8px;
  color: var(--text2);
  animation: fadeSlide 0.15s ease both;
}

@keyframes fadeSlide {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}

.log-prefix { color: var(--text3); flex-shrink: 0; }

.log-success .log-text { color: var(--green); }
.log-error   .log-text { color: var(--red); }
.log-warn    .log-text { color: var(--amber); }
.log-tag     .log-text { color: var(--accent); }

.log-cursor { opacity: 0.6; }
.cursor-blink { animation: blink 1s step-end infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
</style>

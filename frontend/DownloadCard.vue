<template>
  <div class="download-card" :class="error ? 'state-error' : 'state-success'">
    <!-- Success -->
    <template v-if="!error">
      <div class="dc-icon success-icon">✓</div>
      <div class="dc-body">
        <p class="dc-title">.mcpack đã sẵn sàng!</p>
        <p class="dc-sub">File sẽ tự xoá khỏi server sau khi tải về</p>
      </div>
      <div class="dc-actions">
        <a
          :href="`/api/download/${taskId}`"
          class="btn-download"
          download
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          Tải xuống
        </a>
        <button type="button" class="btn-reset" @click="$emit('reset')">
          Tạo pack mới
        </button>
      </div>
    </template>

    <!-- Error -->
    <template v-else>
      <div class="dc-icon error-icon">✕</div>
      <div class="dc-body">
        <p class="dc-title">Build thất bại</p>
        <p class="dc-sub dc-error-msg">{{ error }}</p>
      </div>
      <div class="dc-actions">
        <button type="button" class="btn-reset" @click="$emit('reset')">
          Thử lại
        </button>
      </div>
    </template>
  </div>
</template>

<script setup>
defineProps({
  taskId: { type: String, default: null },
  error:  { type: String, default: null },
})
defineEmits(['reset'])
</script>

<style scoped>
.download-card {
  margin: 0 20px 20px;
  border-radius: var(--radius);
  padding: 16px 18px;
  display: flex;
  align-items: center;
  gap: 14px;
  animation: slideUp 0.25s ease both;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

.state-success {
  background: rgba(49, 201, 142, 0.08);
  border: 1px solid rgba(49, 201, 142, 0.25);
}
.state-error {
  background: rgba(240, 92, 92, 0.08);
  border: 1px solid rgba(240, 92, 92, 0.25);
}

.dc-icon {
  width: 36px; height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  font-weight: 800;
  flex-shrink: 0;
}

.success-icon { background: rgba(49,201,142,0.15); color: var(--green); }
.error-icon   { background: rgba(240,92,92,0.15);  color: var(--red); }

.dc-body { flex: 1; min-width: 0; }

.dc-title {
  font-size: 0.85rem;
  font-weight: 700;
  margin-bottom: 2px;
}
.state-success .dc-title { color: var(--green); }
.state-error   .dc-title { color: var(--red); }

.dc-sub {
  font-size: 0.75rem;
  color: var(--text3);
}

.dc-error-msg {
  color: var(--red);
  opacity: 0.75;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dc-actions { display: flex; gap: 8px; flex-shrink: 0; }

.btn-download {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--green);
  color: #041a10;
  border: none;
  border-radius: 8px;
  font-family: var(--font);
  font-size: 0.82rem;
  font-weight: 700;
  padding: 8px 16px;
  cursor: pointer;
  text-decoration: none;
  transition: background 0.15s, transform 0.1s;
}
.btn-download:hover { background: #28b07d; transform: translateY(-1px); }
.btn-download:active { transform: translateY(0); }

.btn-reset {
  background: var(--bg3);
  color: var(--text2);
  border: 1px solid var(--border2);
  border-radius: 8px;
  font-family: var(--font);
  font-size: 0.82rem;
  font-weight: 600;
  padding: 8px 14px;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.btn-reset:hover { border-color: var(--accent); color: var(--accent); }
</style>

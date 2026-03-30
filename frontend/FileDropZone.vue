<template>
  <div
    class="dropzone"
    :class="{
      'dz-over': isDragging,
      'dz-has-files': hasFiles,
      'dz-disabled': disabled
    }"
    @dragover.prevent="isDragging = true"
    @dragleave.prevent="isDragging = false"
    @drop.prevent="onDrop"
    @click="!disabled && $refs.fileInput.click()"
  >
    <input
      ref="fileInput"
      type="file"
      :accept="accept"
      :multiple="multiple"
      :disabled="disabled"
      style="display:none"
      @change="onFileChange"
    />

    <!-- Empty state -->
    <div v-if="!hasFiles" class="dz-empty">
      <div class="dz-icon">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
      </div>
      <p class="dz-text">
        {{ isDragging ? 'Thả file vào đây' : label }}
      </p>
      <p class="dz-hint">Kéo thả hoặc click để chọn</p>
    </div>

    <!-- Has files state -->
    <div v-else class="dz-files">
      <!-- Single image preview -->
      <div v-if="preview && previewUrl" class="dz-preview-img">
        <img :src="previewUrl" alt="preview" />
      </div>

      <div class="dz-file-list">
        <div v-for="(f, i) in fileList" :key="i" class="dz-file-item">
          <span class="dz-file-icon">{{ getFileIcon(f) }}</span>
          <span class="dz-file-name">{{ f.name }}</span>
          <span class="dz-file-size">{{ formatSize(f.size) }}</span>
          <button
            v-if="!disabled"
            type="button"
            class="dz-remove"
            @click.stop="removeFile(i)"
          >✕</button>
        </div>
      </div>

      <button
        v-if="!disabled"
        type="button"
        class="dz-add-more"
        @click.stop="$refs.fileInput.click()"
      >
        + Thêm file
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'

const props = defineProps({
  label:    { type: String, default: 'Upload file' },
  accept:   { type: String, default: '*' },
  multiple: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  modelValue: { default: null },
  preview:  { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const isDragging = ref(false)
const fileList   = ref([])
const previewUrl = ref(null)

const hasFiles = computed(() =>
  props.multiple
    ? fileList.value.length > 0
    : fileList.value.length > 0 || (props.modelValue && !(props.modelValue instanceof Array))
)

function syncOut() {
  if (props.multiple) {
    emit('update:modelValue', fileList.value)
  } else {
    emit('update:modelValue', fileList.value[0] ?? null)
  }
}

function addFiles(files) {
  const arr = Array.from(files)
  if (props.multiple) {
    fileList.value = [...fileList.value, ...arr]
  } else {
    fileList.value = arr.slice(0, 1)
  }
  syncOut()
  updatePreview()
}

function removeFile(i) {
  fileList.value.splice(i, 1)
  syncOut()
  updatePreview()
}

function onDrop(e) {
  isDragging.value = false
  if (props.disabled) return
  addFiles(e.dataTransfer.files)
}

function onFileChange(e) {
  addFiles(e.target.files)
  e.target.value = ''
}

function updatePreview() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  if (props.preview && fileList.value[0]) {
    previewUrl.value = URL.createObjectURL(fileList.value[0])
  }
}

function getFileIcon(f) {
  if (f.type.startsWith('video/'))  return '🎬'
  if (f.type.startsWith('audio/'))  return '🎵'
  if (f.type.startsWith('image/'))  return '🖼'
  return '📄'
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

onBeforeUnmount(() => {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
})
</script>

<style scoped>
.dropzone {
  border: 1.5px dashed var(--border2);
  border-radius: var(--radius);
  background: var(--bg3);
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
  position: relative;
  min-height: 90px;
}

.dropzone:hover:not(.dz-disabled),
.dz-over { border-color: var(--accent); background: rgba(91,124,250,0.05); }

.dz-disabled { opacity: 0.45; cursor: not-allowed; pointer-events: none; }

.dz-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 22px 16px;
  gap: 6px;
}

.dz-icon { color: var(--text3); transition: color 0.15s; }
.dropzone:hover .dz-icon { color: var(--accent); }

.dz-text { font-size: 0.82rem; font-weight: 600; color: var(--text2); }
.dz-hint { font-size: 0.72rem; color: var(--text3); }

.dz-files { padding: 12px; }

.dz-preview-img {
  width: 80px; height: 80px;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 10px;
  border: 1px solid var(--border);
}
.dz-preview-img img { width: 100%; height: 100%; object-fit: cover; }

.dz-file-list { display: flex; flex-direction: column; gap: 6px; }

.dz-file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 7px 10px;
  font-size: 0.78rem;
}

.dz-file-icon { font-size: 14px; flex-shrink: 0; }
.dz-file-name { flex: 1; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dz-file-size { color: var(--text3); flex-shrink: 0; font-family: var(--mono); font-size: 0.72rem; }

.dz-remove {
  background: none;
  border: none;
  color: var(--text3);
  cursor: pointer;
  font-size: 0.7rem;
  padding: 2px 4px;
  border-radius: 4px;
  transition: color 0.15s, background 0.15s;
  line-height: 1;
  flex-shrink: 0;
}
.dz-remove:hover { color: var(--red); background: rgba(240,92,92,0.12); }

.dz-add-more {
  background: none;
  border: 1px dashed var(--border2);
  border-radius: 6px;
  color: var(--text2);
  font-family: var(--font);
  font-size: 0.75rem;
  font-weight: 600;
  padding: 6px 12px;
  cursor: pointer;
  width: 100%;
  margin-top: 8px;
  transition: border-color 0.15s, color 0.15s;
}
.dz-add-more:hover { border-color: var(--accent); color: var(--accent); }
</style>

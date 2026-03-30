<template>
  <div class="build-form">
    <div class="form-header">
      <h2>Pack Configuration</h2>
      <p>Điền thông tin để tạo .mcpack extension</p>
    </div>

    <form @submit.prevent="handleSubmit" class="form-body">

      <!-- SECTION: Basic Info -->
      <div class="form-section">
        <div class="section-label">
          <span class="section-num">01</span>
          <span>Basic Info</span>
        </div>

        <div class="field-row">
          <div class="field">
            <label>Pack Name <span class="req">*</span></label>
            <input
              v-model="form.packName"
              type="text"
              placeholder="My Awesome Pack"
              :disabled="disabled"
              required
            />
          </div>
        </div>

        <div class="field-row two-col">
          <div class="field">
            <label>
              UUID
              <button type="button" class="btn-inline" @click="genUUID" :disabled="disabled">
                ↻ Gen
              </button>
            </label>
            <input
              v-model="form.uuid"
              type="text"
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              class="mono"
              :disabled="disabled"
            />
          </div>
          <div class="field">
            <label>
              UUID 2
              <button type="button" class="btn-inline" @click="genUUID2" :disabled="disabled">
                ↻ Gen
              </button>
            </label>
            <input
              v-model="form.uuid2"
              type="text"
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              class="mono"
              :disabled="disabled"
            />
          </div>
        </div>

        <div class="field-row two-col">
          <div class="field">
            <label>Version</label>
            <input v-model="form.version" type="text" placeholder="1.0.0" :disabled="disabled" />
          </div>
          <div class="field">
            <label>Min Engine Version</label>
            <input v-model="form.minEngine" type="text" placeholder="1.20.0" :disabled="disabled" />
          </div>
        </div>

        <div class="field-row">
          <div class="field">
            <label>Description</label>
            <input v-model="form.description" type="text" placeholder="Mô tả pack..." :disabled="disabled" />
          </div>
        </div>
      </div>

      <!-- SECTION: Animated Background -->
      <div class="form-section">
        <div class="section-label">
          <span class="section-num">02</span>
          <span>Animated Background</span>
          <span class="section-toggle">
            <label class="toggle">
              <input type="checkbox" v-model="form.enableAnimBg" :disabled="disabled" />
              <span class="toggle-track"></span>
            </label>
          </span>
        </div>

        <div v-if="form.enableAnimBg" class="section-content">
          <div class="field-row">
            <div class="field">
              <label>Nguồn video</label>
              <div class="radio-group">
                <label class="radio-opt" :class="{ active: form.animSource === 'file' }">
                  <input type="radio" v-model="form.animSource" value="file" :disabled="disabled" />
                  <span>Upload file</span>
                </label>
                <label class="radio-opt" :class="{ active: form.animSource === 'youtube' }">
                  <input type="radio" v-model="form.animSource" value="youtube" :disabled="disabled" />
                  <span>YouTube URL</span>
                </label>
              </div>
            </div>
          </div>

          <div v-if="form.animSource === 'file'" class="field-row">
            <FileDropZone
              label="Video / GIF / Ảnh frames"
              accept="video/*,image/*,.gif"
              :multiple="true"
              :disabled="disabled"
              v-model="form.animFiles"
            />
          </div>

          <div v-if="form.animSource === 'youtube'" class="field-row">
            <div class="field">
              <label>YouTube URL</label>
              <input
                v-model="form.youtubeUrl"
                type="url"
                placeholder="https://www.youtube.com/watch?v=..."
                :disabled="disabled"
              />
            </div>
          </div>

          <div class="field-row two-col">
            <div class="field">
              <label>FPS <span class="hint">mặc định 20</span></label>
              <input v-model.number="form.fps" type="number" min="1" max="60" :disabled="disabled" />
            </div>
            <div class="field">
              <label>Max frames <span class="hint">mặc định 9999</span></label>
              <input v-model.number="form.maxFrames" type="number" min="1" :disabled="disabled" />
            </div>
          </div>

          <div class="field-row two-col">
            <div class="field">
              <label>Start time <span class="hint">mm:ss</span></label>
              <input v-model="form.startTime" type="text" placeholder="0:00" class="mono" :disabled="disabled" />
            </div>
            <div class="field">
              <label>End time <span class="hint">mm:ss</span></label>
              <input v-model="form.endTime" type="text" placeholder="0:30" class="mono" :disabled="disabled" />
            </div>
          </div>
        </div>
      </div>

      <!-- SECTION: Loading Background -->
      <div class="form-section">
        <div class="section-label">
          <span class="section-num">03</span>
          <span>Loading Background</span>
          <span class="section-toggle">
            <label class="toggle">
              <input type="checkbox" v-model="form.enableLoadingBg" :disabled="disabled" />
              <span class="toggle-track"></span>
            </label>
          </span>
        </div>

        <div v-if="form.enableLoadingBg" class="section-content">
          <FileDropZone
            label="Ảnh loading screen (PNG/JPG)"
            accept="image/*"
            :multiple="true"
            :disabled="disabled"
            v-model="form.loadingFiles"
          />
        </div>
      </div>

      <!-- SECTION: Background Music -->
      <div class="form-section">
        <div class="section-label">
          <span class="section-num">04</span>
          <span>Background Music</span>
          <span class="section-toggle">
            <label class="toggle">
              <input type="checkbox" v-model="form.enableBgm" :disabled="disabled" />
              <span class="toggle-track"></span>
            </label>
          </span>
        </div>

        <div v-if="form.enableBgm" class="section-content">
          <div class="field-row">
            <div class="field">
              <label>Nguồn nhạc</label>
              <div class="radio-group">
                <label class="radio-opt" :class="{ active: form.bgmSource === 'file' }">
                  <input type="radio" v-model="form.bgmSource" value="file" :disabled="disabled" />
                  <span>Upload file</span>
                </label>
                <label class="radio-opt" :class="{ active: form.bgmSource === 'youtube' }">
                  <input type="radio" v-model="form.bgmSource" value="youtube" :disabled="disabled" />
                  <span>YouTube URL</span>
                </label>
              </div>
            </div>
          </div>

          <div v-if="form.bgmSource === 'file'" class="field-row">
            <FileDropZone
              label="Audio file (MP3/WAV/OGG/FLAC)"
              accept="audio/*"
              :multiple="false"
              :disabled="disabled"
              v-model="form.bgmFile"
            />
          </div>

          <div v-if="form.bgmSource === 'youtube'" class="field-row">
            <div class="field">
              <label>YouTube URL (chỉ lấy audio)</label>
              <input
                v-model="form.bgmYoutubeUrl"
                type="url"
                placeholder="https://www.youtube.com/watch?v=..."
                :disabled="disabled"
              />
            </div>
          </div>

          <div class="field-row two-col">
            <div class="field">
              <label>Start time <span class="hint">mm:ss</span></label>
              <input v-model="form.bgmStart" type="text" placeholder="0:00" class="mono" :disabled="disabled" />
            </div>
            <div class="field">
              <label>End time <span class="hint">mm:ss</span></label>
              <input v-model="form.bgmEnd" type="text" placeholder="1:00" class="mono" :disabled="disabled" />
            </div>
          </div>
        </div>
      </div>

      <!-- SECTION: Pack Icon -->
      <div class="form-section">
        <div class="section-label">
          <span class="section-num">05</span>
          <span>Pack Icon</span>
          <span class="section-toggle">
            <label class="toggle">
              <input type="checkbox" v-model="form.enableIcon" :disabled="disabled" />
              <span class="toggle-track"></span>
            </label>
          </span>
        </div>

        <div v-if="form.enableIcon" class="section-content">
          <FileDropZone
            label="Pack icon (PNG, sẽ crop 256×256)"
            accept="image/png,image/jpeg,image/webp"
            :multiple="false"
            :disabled="disabled"
            v-model="form.iconFile"
            :preview="true"
          />
        </div>
      </div>

      <!-- SECTION: Output -->
      <div class="form-section">
        <div class="section-label">
          <span class="section-num">06</span>
          <span>Output</span>
        </div>
        <div class="section-content">
          <div class="field-row two-col">
            <div class="field">
              <label>Output filename</label>
              <input v-model="form.outputName" type="text" placeholder="my_extension" :disabled="disabled" />
            </div>
            <div class="field">
              <label>Format</label>
              <select v-model="form.outputFormat" :disabled="disabled">
                <option value="mcpack">.mcpack</option>
                <option value="zip">.zip</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <!-- Submit -->
      <div class="form-footer">
        <button type="submit" class="btn-build" :disabled="disabled || !isValid">
          <span v-if="!disabled">
            <span class="btn-icon">▶</span> Build Pack
          </span>
          <span v-else class="btn-building">
            <span class="spinner"></span> Building…
          </span>
        </button>
        <p v-if="!isValid && !disabled" class="validation-hint">
          Pack name là bắt buộc
        </p>
      </div>

    </form>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import FileDropZone from './FileDropZone.vue'

const props = defineProps({ disabled: Boolean })
const emit = defineEmits(['submitted'])

const form = ref({
  // Basic
  packName: '',
  uuid: '',
  uuid2: '',
  version: '1.0.0',
  minEngine: '1.20.0',
  description: '',
  // Anim BG
  enableAnimBg: true,
  animSource: 'file',
  animFiles: [],
  youtubeUrl: '',
  fps: 20,
  maxFrames: 9999,
  startTime: '',
  endTime: '',
  // Loading BG
  enableLoadingBg: false,
  loadingFiles: [],
  // BGM
  enableBgm: true,
  bgmSource: 'file',
  bgmFile: null,
  bgmYoutubeUrl: '',
  bgmStart: '',
  bgmEnd: '',
  // Icon
  enableIcon: true,
  iconFile: null,
  // Output
  outputName: '',
  outputFormat: 'mcpack',
})

const isValid = computed(() => form.value.packName.trim().length > 0)

function uuidv4() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16)
  })
}

function genUUID()  { form.value.uuid  = uuidv4() }
function genUUID2() { form.value.uuid2 = uuidv4() }

async function handleSubmit() {
  if (!isValid.value || props.disabled) return

  const fd = new FormData()

  // Text fields
  const meta = {
    pack_name:    form.value.packName,
    uuid:         form.value.uuid  || uuidv4(),
    uuid2:        form.value.uuid2 || uuidv4(),
    version:      form.value.version,
    min_engine:   form.value.minEngine,
    description:  form.value.description,
    fps:          form.value.fps,
    max_frames:   form.value.maxFrames,
    start_time:   form.value.startTime,
    end_time:     form.value.endTime,
    output_name:  form.value.outputName || form.value.packName.replace(/\s+/g, '_'),
    output_format: form.value.outputFormat,
    // Feature flags
    enable_anim_bg:    form.value.enableAnimBg,
    anim_source:       form.value.animSource,
    youtube_url:       form.value.youtubeUrl,
    enable_loading_bg: form.value.enableLoadingBg,
    enable_bgm:        form.value.enableBgm,
    bgm_source:        form.value.bgmSource,
    bgm_youtube_url:   form.value.bgmYoutubeUrl,
    bgm_start:         form.value.bgmStart,
    bgm_end:           form.value.bgmEnd,
    enable_icon:       form.value.enableIcon,
  }
  fd.append('meta', JSON.stringify(meta))

  // Files
  if (form.value.enableAnimBg && form.value.animSource === 'file') {
    for (const f of form.value.animFiles) fd.append('anim_files', f)
  }
  if (form.value.enableLoadingBg) {
    for (const f of form.value.loadingFiles) fd.append('loading_files', f)
  }
  if (form.value.enableBgm && form.value.bgmSource === 'file' && form.value.bgmFile) {
    fd.append('bgm_file', form.value.bgmFile)
  }
  if (form.value.enableIcon && form.value.iconFile) {
    fd.append('icon_file', form.value.iconFile)
  }

  try {
    const res = await fetch('/api/build', { method: 'POST', body: fd })
    if (!res.ok) throw new Error(`Server error: ${res.status}`)
    const { task_id } = await res.json()
    emit('submitted', task_id)
  } catch (e) {
    alert('Lỗi kết nối backend: ' + e.message)
  }
}
</script>

<style scoped>
.build-form { display: flex; flex-direction: column; }

.form-header {
  padding: 24px 28px 16px;
  border-bottom: 1px solid var(--border);
}
.form-header h2 {
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  margin-bottom: 3px;
}
.form-header p { font-size: 0.8rem; color: var(--text2); }

.form-body { padding: 4px 0 0; }

.form-section {
  border-bottom: 1px solid var(--border);
  padding: 0;
}

.section-label {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 28px;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text2);
  user-select: none;
}

.section-num {
  font-family: var(--mono);
  font-size: 0.7rem;
  color: var(--accent);
  font-weight: 500;
  opacity: 0.8;
}

.section-toggle { margin-left: auto; }

.section-content { padding: 4px 28px 20px; }

.field-row { margin-bottom: 14px; }
.field-row.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.field { display: flex; flex-direction: column; gap: 6px; }

label {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--text2);
  display: flex;
  align-items: center;
  gap: 8px;
}

.req { color: var(--red); }
.hint {
  font-weight: 400;
  letter-spacing: 0;
  text-transform: none;
  color: var(--text3);
  font-size: 0.7rem;
}

input[type="text"],
input[type="url"],
input[type="number"],
select {
  background: var(--bg3);
  border: 1px solid var(--border2);
  border-radius: var(--radius);
  color: var(--text);
  font-family: var(--font);
  font-size: 0.88rem;
  padding: 9px 12px;
  width: 100%;
  transition: border-color 0.15s, box-shadow 0.15s;
  outline: none;
  -webkit-appearance: none;
}

input:focus, select:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(91, 124, 250, 0.15);
}

input:disabled, select:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

input.mono { font-family: var(--mono); font-size: 0.8rem; }

select {
  cursor: pointer;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%238892aa' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 32px;
}

option { background: var(--bg2); }

/* Radio group */
.radio-group { display: flex; gap: 8px; }
.radio-opt {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border: 1px solid var(--border2);
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.82rem;
  font-weight: 500;
  letter-spacing: 0;
  text-transform: none;
  color: var(--text2);
  background: var(--bg3);
  transition: all 0.15s;
  user-select: none;
}
.radio-opt input { display: none; }
.radio-opt:hover { border-color: var(--accent); color: var(--text); }
.radio-opt.active {
  background: rgba(91,124,250,0.12);
  border-color: var(--accent);
  color: var(--accent);
}

/* Toggle switch */
.toggle { display: inline-flex; align-items: center; cursor: pointer; }
.toggle input { display: none; }
.toggle-track {
  width: 36px;
  height: 20px;
  background: var(--border2);
  border-radius: 10px;
  position: relative;
  transition: background 0.2s;
}
.toggle-track::after {
  content: '';
  position: absolute;
  top: 3px;
  left: 3px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--text3);
  transition: transform 0.2s, background 0.2s;
}
.toggle input:checked + .toggle-track { background: var(--accent); }
.toggle input:checked + .toggle-track::after {
  transform: translateX(16px);
  background: #fff;
}

/* Inline button */
.btn-inline {
  background: var(--bg3);
  border: 1px solid var(--border2);
  color: var(--accent);
  font-family: var(--font);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  padding: 2px 8px;
  border-radius: 5px;
  cursor: pointer;
  text-transform: uppercase;
  transition: background 0.15s;
}
.btn-inline:hover { background: var(--border); }
.btn-inline:disabled { opacity: 0.4; cursor: not-allowed; }

/* Form footer */
.form-footer {
  padding: 24px 28px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
}

.btn-build {
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: var(--radius);
  font-family: var(--font);
  font-size: 0.92rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  padding: 12px 28px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: background 0.15s, transform 0.1s;
}
.btn-build:hover:not(:disabled) { background: #4a6be8; transform: translateY(-1px); }
.btn-build:active:not(:disabled) { transform: translateY(0); }
.btn-build:disabled { opacity: 0.45; cursor: not-allowed; }

.btn-icon { font-size: 0.8rem; }

.btn-building { display: flex; align-items: center; gap: 8px; }

.spinner {
  width: 14px; height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  display: inline-block;
}
@keyframes spin { to { transform: rotate(360deg); } }

.validation-hint { font-size: 0.78rem; color: var(--red); }
</style>

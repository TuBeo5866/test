# mcpack-studio

HorizonUI / NekoUI Extension Studio — web version.

```
mcpack-studio/
├── Dockerfile          ← build cả frontend + backend thành 1 image
├── .dockerignore
├── frontend/           ← Vue 3 + Vite
│   ├── src/
│   │   ├── App.vue
│   │   └── components/
│   │       ├── BuildForm.vue
│   │       ├── FileDropZone.vue
│   │       ├── ProgressPanel.vue
│   │       └── DownloadCard.vue
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
└── backend/            ← FastAPI + Python
    ├── main.py         ← routes, SSE, file upload/download
    ├── worker.py       ← build logic (ffmpeg, yt-dlp, Pillow)
    ├── task_manager.py ← in-memory task store
    ├── schemas.py      ← Pydantic models
    └── requirements.txt
```

---

## Dev local (2 terminal)

**Terminal 1 — backend:**
```bash
cd backend
pip install -r requirements.txt
# cần ffmpeg và yt-dlp trong PATH
uvicorn main:app --reload --port 8000
```

**Terminal 2 — frontend:**
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
# /api/* tự proxy sang localhost:8000
```

---

## Build & chạy bằng Docker

```bash
# từ root repo
docker build -t mcpack-studio .
docker run -p 8000:8000 mcpack-studio
# → http://localhost:8000
```

---

## Deploy Railway / Render

1. Push repo lên GitHub
2. **Railway**: New Project → Deploy from repo → tự detect `Dockerfile`
3. **Render**: New Web Service → Docker → port `8000`
4. Không cần biến môi trường — ffmpeg và yt-dlp đã có trong image

---

## Luồng hoạt động

```
Browser (Vue)
  │  POST /api/build  (multipart: files + JSON meta)
  ▼
FastAPI (main.py)
  │  lưu file tạm → tạo Task → chạy Worker trong thread
  ▼
Worker (worker.py)          ── stream log/progress qua SSE
  │  yt-dlp / ffmpeg / Pillow
  │  build thư mục Minecraft
  │  zip → .mcpack
  ▼
GET /api/download/{task_id} → trả file → xoá temp
```

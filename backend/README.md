# mcpack-studio — Backend

FastAPI backend cho HorizonUI/NekoUI Extension Studio.

## Cấu trúc project (monorepo)

```
project-root/
├── Dockerfile          ← dùng file Dockerfile.root này (đổi tên)
├── frontend/           ← Vue 3 + Vite
│   ├── src/
│   ├── package.json
│   └── vite.config.js
└── backend/            ← FastAPI
    ├── main.py
    ├── worker.py
    ├── task_manager.py
    ├── schemas.py
    ├── requirements.txt
    └── static/         ← Vue build output (tự sinh khi build)
```

---

## Chạy local (dev mode)

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
# ffmpeg và yt-dlp phải có sẵn trong PATH
uvicorn main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173  (proxy /api → backend:8000)
```

---

## Build production (Docker)

```bash
# Từ project root — đổi tên Dockerfile.root → Dockerfile
mv backend/Dockerfile.root Dockerfile

docker build -t mcpack-studio .
docker run -p 8000:8000 mcpack-studio
# → http://localhost:8000
```

---

## Deploy lên Railway

1. Push code lên GitHub
2. Tạo project mới trên Railway → "Deploy from GitHub repo"
3. Railway tự detect `Dockerfile` ở root → build & deploy
4. Set port: `8000` (Railway tự detect từ `EXPOSE 8000`)
5. Không cần thêm biến môi trường (ffmpeg đã có trong image)

### Deploy lên Render

1. New Web Service → Connect GitHub repo
2. **Environment**: Docker
3. **Dockerfile Path**: `Dockerfile` (root)
4. **Port**: `8000`
5. Deploy

---

## API Reference

### `POST /api/build`

Multipart form data:

| Field | Type | Mô tả |
|---|---|---|
| `meta` | string (JSON) | BuildMeta object |
| `anim_files` | file[] | Video/ảnh animated background |
| `loading_files` | file[] | Ảnh loading screen |
| `bgm_file` | file | Audio file |
| `icon_file` | file | Pack icon PNG |

Response: `{ "task_id": "uuid" }`

### `GET /api/progress/{task_id}`

Server-Sent Events stream:

```
event: log
data: {"message": "Extracting frames..."}

event: progress
data: {"value": 42}

event: done
data: {"success": true, "message": "✅ Build completed!"}
```

### `GET /api/download/{task_id}`

Trả về file `.mcpack` / `.zip`.  
File và task bị xoá tự động sau khi download.

---

## Lưu ý

- **Concurrency**: Tối đa 4 build đồng thời (ThreadPoolExecutor).
- **Storage**: Temp files trong `/tmp`, tự xoá sau mỗi download.
- **ffmpeg**: Phải cài sẵn trong môi trường — Docker image đã bao gồm.
- **yt-dlp**: Tương tự — có trong Docker image.
- **Không có DB**: Task state chỉ tồn tại trong RAM. Restart server = mất task đang chờ.

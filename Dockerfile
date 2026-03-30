# ── Stage 1: Build Vue frontend ──────────────────────────────────────────────
FROM node:20-alpine AS frontend

WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build
# → /build/dist/


# ── Stage 2: Python + ffmpeg runtime ─────────────────────────────────────────
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir yt-dlp

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Vue dist → /app/static/ (FastAPI tự serve)
COPY --from=frontend /build/dist ./static

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

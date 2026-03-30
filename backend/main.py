"""
main.py
-------
FastAPI backend cho mcpack-studio.

Endpoints:
  POST /api/build                     — nhận files + meta JSON, tạo build task
  GET  /api/progress/{task_id}        — SSE stream (log / progress / done)
  GET  /api/status/{task_id}          — quick poll (optional)
  GET  /api/download/{task_id}        — tải file .mcpack
  GET  /                              — serve Vue SPA (khi deploy)
"""

import asyncio
import json
import os
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import task_manager as tm
from schemas import BuildMeta, BuildResponse, TaskStatusResponse
from worker import Worker

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(title="mcpack-studio API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thread pool — max 4 concurrent builds
_executor = ThreadPoolExecutor(max_workers=4)

# ── Helper: save uploaded file ────────────────────────────────────────────────

async def _save_upload(upload: UploadFile, dest_dir: Path) -> Path:
    dest = dest_dir / upload.filename
    content = await upload.read()
    dest.write_bytes(content)
    return dest


# ── POST /api/build ───────────────────────────────────────────────────────────

@app.post("/api/build", response_model=BuildResponse)
async def build(
    meta: str = Form(...),
    anim_files:    list[UploadFile] = File(default=[]),
    loading_files: list[UploadFile] = File(default=[]),
    bgm_file:      UploadFile       = File(default=None),
    icon_file:     UploadFile       = File(default=None),
):
    # Parse meta JSON
    try:
        raw = json.loads(meta)
        build_meta = BuildMeta(**raw)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid meta: {e}")

    # Create task
    task = tm.create_task()
    task.status = "running"

    # Create per-task temp directory
    work_dir = Path(tempfile.mkdtemp(prefix=f"mcpack_{task.id}_"))

    # Save uploaded files
    uploads_dir = work_dir / "uploads"
    uploads_dir.mkdir()

    anim_paths:    list[str] = []
    loading_paths: list[str] = []
    bgm_path:      str | None = None
    icon_path:     str | None = None

    for f in anim_files:
        if f and f.filename:
            p = await _save_upload(f, uploads_dir)
            anim_paths.append(str(p))

    for f in loading_files:
        if f and f.filename:
            p = await _save_upload(f, uploads_dir)
            loading_paths.append(str(p))

    if bgm_file and bgm_file.filename:
        bgm_path = str(await _save_upload(bgm_file, uploads_dir))

    if icon_file and icon_file.filename:
        icon_path = str(await _save_upload(icon_file, uploads_dir))

    # Build cfg dict for Worker
    cfg = {
        # Basic
        "pack_name":    build_meta.pack_name,
        "uuid":         build_meta.uuid,
        "uuid2":        build_meta.uuid2,
        "version":      build_meta.version,
        "min_engine":   build_meta.min_engine,
        "description":  build_meta.description,
        "creator":      "Web User",
        # Work dir
        "work_dir":     str(work_dir),
        # Animated BG
        "enable_anim_bg":    build_meta.enable_anim_bg,
        "anim_source":       build_meta.anim_source,
        "anim_file_paths":   anim_paths,
        "youtube_url":       build_meta.youtube_url,
        "fps":               build_meta.fps,
        "anim_frames":       build_meta.max_frames,
        "load_frames":       build_meta.max_frames,
        # Time range
        "start_seconds": _parse_time_safe(build_meta.start_time),
        "end_seconds":   _parse_time_safe(build_meta.end_time),
        # Loading BG
        "enable_loading_bg":  build_meta.enable_loading_bg,
        "loading_file_paths": loading_paths,
        # BGM
        "enable_bgm":        build_meta.enable_bgm,
        "bgm_source":        build_meta.bgm_source,
        "bgm_file_path":     bgm_path,
        "bgm_youtube_url":   build_meta.bgm_youtube_url,
        "bgm_name":          "bgm",
        "bgm_start_seconds": _parse_time_safe(build_meta.bgm_start),
        "bgm_end_seconds":   _parse_time_safe(build_meta.bgm_end),
        # Icon
        "enable_icon":    build_meta.enable_icon,
        "icon_file_path": icon_path,
        # Output
        "output_name":   build_meta.output_name or build_meta.pack_name.replace(" ", "_"),
        "output_format": build_meta.output_format,
    }

    # Thread-safe callbacks — bridge Worker (sync thread) → Task store → SSE
    loop = asyncio.get_event_loop()

    def on_log(msg: str):
        task.logs.append(msg)
        loop.call_soon_threadsafe(task.notify)

    def on_progress(pct: int):
        task.progress = pct
        loop.call_soon_threadsafe(task.notify)

    def on_done(success: bool, msg: str):
        task.status = "done" if success else "error"
        if success:
            task.result = Path(cfg.get("output_path", ""))
        else:
            task.error = msg
        task.logs.append(msg)
        loop.call_soon_threadsafe(task.notify)

    # Submit to thread pool
    worker = Worker(cfg, on_log, on_progress, on_done)
    loop.run_in_executor(_executor, worker.run)

    return BuildResponse(task_id=task.id)


def _parse_time_safe(value: str | None) -> int | None:
    if not value or not str(value).strip():
        return None
    try:
        parts = str(value).strip().split(":")
        parts = [int(p) for p in parts]
        if len(parts) == 1:
            return parts[0]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
    except Exception:
        pass
    return None


# ── GET /api/progress/{task_id}  (SSE) ───────────────────────────────────────

@app.get("/api/progress/{task_id}")
async def progress_sse(task_id: str):
    task = tm.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        sent_log_idx = 0

        while True:
            # Flush pending logs
            while sent_log_idx < len(task.logs):
                msg = task.logs[sent_log_idx]
                sent_log_idx += 1
                payload = json.dumps({"message": msg})
                yield f"event: log\ndata: {payload}\n\n"

            # Send current progress
            yield f"event: progress\ndata: {json.dumps({'value': task.progress})}\n\n"

            # Check terminal state
            if task.status in ("done", "error"):
                payload = json.dumps({
                    "success": task.status == "done",
                    "message": task.error or "Build completed",
                })
                yield f"event: done\ndata: {payload}\n\n"
                return

            # Wait for next notification (with timeout to send keepalives)
            try:
                event = task.get_event()
                await asyncio.wait_for(event.wait(), timeout=15)
            except asyncio.TimeoutError:
                # Keepalive comment
                yield ": keepalive\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # Tắt nginx buffering
        },
    )


# ── GET /api/status/{task_id}  (quick poll fallback) ─────────────────────────

@app.get("/api/status/{task_id}", response_model=TaskStatusResponse)
async def task_status(task_id: str):
    task = tm.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskStatusResponse(
        task_id=task_id,
        status=task.status,
        progress=task.progress,
        error=task.error,
    )


# ── GET /api/download/{task_id} ───────────────────────────────────────────────

@app.get("/api/download/{task_id}")
async def download(task_id: str):
    task = tm.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "done":
        raise HTTPException(status_code=400, detail=f"Task not done yet (status={task.status})")
    if not task.result or not task.result.exists():
        raise HTTPException(status_code=404, detail="Output file not found")

    out_file = task.result
    filename = out_file.name

    # Cleanup task sau khi download
    async def cleanup_after_send():
        # Xoá thư mục work sau khi FileResponse stream xong
        work_dir = out_file.parent
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass
        tm.delete_task(task_id)

    # Sử dụng background task để cleanup
    from starlette.background import BackgroundTask
    return FileResponse(
        path=str(out_file),
        filename=filename,
        media_type="application/octet-stream",
        background=BackgroundTask(cleanup_after_send),
    )


# ── Serve Vue SPA (production) ────────────────────────────────────────────────

_STATIC_DIR = Path(__file__).parent / "static"

if _STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(_STATIC_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        index = _STATIC_DIR / "index.html"
        if index.exists():
            return FileResponse(str(index))
        raise HTTPException(status_code=404)


# ── Dev entrypoint ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

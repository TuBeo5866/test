"""
task_manager.py
---------------
In-memory store cho mỗi build task.
Mỗi task có:
  - status : "pending" | "running" | "done" | "error"
  - logs   : list[str]          (append-only)
  - progress: int 0-100
  - result : Path | None        (đường dẫn file .mcpack khi xong)
  - error  : str | None
  - event  : asyncio.Event      (SSE dùng để wake up stream)
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Task:
    id: str
    status: str = "pending"
    logs: list = field(default_factory=list)
    progress: int = 0
    result: Optional[Path] = None
    error: Optional[str] = None
    # asyncio.Event — được set mỗi khi có log/progress/done mới
    _event: Optional[asyncio.Event] = field(default=None, repr=False)

    def get_event(self) -> asyncio.Event:
        if self._event is None:
            self._event = asyncio.Event()
        return self._event

    def notify(self):
        """Wake up tất cả SSE listener đang chờ task này."""
        if self._event:
            self._event.set()
            self._event.clear()


# ── Global store ──────────────────────────────────────────────────────────────

_tasks: dict[str, Task] = {}


def create_task() -> Task:
    tid = str(uuid.uuid4())
    t = Task(id=tid)
    _tasks[tid] = t
    return t


def get_task(tid: str) -> Optional[Task]:
    return _tasks.get(tid)


def delete_task(tid: str):
    _tasks.pop(tid, None)

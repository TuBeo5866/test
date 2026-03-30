"""
schemas.py
----------
Pydantic models cho request meta và response.
"""

from pydantic import BaseModel
from typing import Optional


class BuildMeta(BaseModel):
    # Basic
    pack_name: str
    uuid: str = ""
    uuid2: str = ""
    version: str = "1.0.0"
    min_engine: str = "1.20.0"
    description: str = ""

    # Animated background
    enable_anim_bg: bool = True
    anim_source: str = "file"        # "file" | "youtube"
    youtube_url: str = ""
    fps: int = 20
    max_frames: int = 9999
    start_time: str = ""             # "mm:ss" hoặc seconds string
    end_time: str = ""

    # Loading background
    enable_loading_bg: bool = False

    # BGM
    enable_bgm: bool = True
    bgm_source: str = "file"         # "file" | "youtube"
    bgm_youtube_url: str = ""
    bgm_start: str = ""
    bgm_end: str = ""

    # Icon
    enable_icon: bool = True

    # Output
    output_name: str = ""
    output_format: str = "mcpack"    # "mcpack" | "zip"

    # Pack type (frontend có thể expose sau)
    pack_type: str = "horizon"       # "horizon" | "neko"


class BuildResponse(BaseModel):
    task_id: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    error: Optional[str] = None

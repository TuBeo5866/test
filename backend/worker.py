"""
worker.py
---------
Worker thuần Python (không PyQt5, không QThread).

Chạy trong ThreadPoolExecutor.
Thay vì emit signal → gọi callback:
  - on_log(msg: str)
  - on_progress(pct: int)
  - on_done(success: bool, msg: str)

Toàn bộ logic xử lý (ffmpeg, yt-dlp, Pillow, zip) được giữ nguyên
từ new.py, chỉ bỏ mọi import/dependency liên quan đến PyQt5.
"""

import os, sys, json, shutil, subprocess, uuid, re, tempfile, zipfile, stat
from pathlib import Path
from typing import Callable, Optional
from PIL import Image, ImageFilter

# ── Constants (giữ nguyên từ new.py) ─────────────────────────────────────────

MAX_FRAMES       = 9999
DEFAULT_FPS      = 20
MEMORY_THRESHOLD = 80

ANIM_BG_DIR      = "hrzn_animated_background"
LOADING_BG_DIR   = "hrzn_loading_background"
CONTAINER_BG_DIR = "hrzn_container_background"
SOUNDS_DIR       = "sounds/music/bgm"
UI_DIR           = "ui"

CONTAINER_BG_URL = "https://tubeo5866.github.io/files/hrzn_container_background.zip"
FRAME_PREFIX_ANIM = "hans_common_"


def _get_ffmpeg_exe() -> str:
    env_path = os.environ.get("_HRZN_FFMPEG_EXE", "")
    if env_path and Path(env_path).exists():
        return env_path
    return "ffmpeg"


def _parse_time(value) -> Optional[int]:
    if not value:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).strip()
    if not s:
        return None
    parts = s.split(":")
    try:
        parts = [int(p) for p in parts]
    except ValueError:
        raise ValueError(f"Invalid time format: {value!r}")
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    raise ValueError(f"Invalid time format: {value!r}")


# ── Base Worker ───────────────────────────────────────────────────────────────

class Worker:
    """
    Worker base class cho HorizonUI pack.
    Được chạy trong thread pool — KHÔNG phải async, KHÔNG phải coroutine.
    """

    def __init__(
        self,
        cfg: dict,
        on_log: Callable[[str], None],
        on_progress: Callable[[int], None],
        on_done: Callable[[bool, str], None],
    ):
        self.cfg          = cfg
        self._on_log      = on_log
        self._on_progress = on_progress
        self._on_done     = on_done
        self._stop        = False
        self._temp_files: list[Path] = []

    # ── Public entry point ────────────────────────────────────────────────────

    def run(self):
        """Được gọi từ ThreadPoolExecutor."""
        try:
            self.process()
            self._on_done(True, "✅ .mcpack created successfully!")
        except Exception as e:
            import traceback
            self.log(traceback.format_exc())
            self._on_done(False, f"❌ {e}")
        finally:
            self._cleanup()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def log(self, msg: str):
        self._on_log(str(msg))

    def progress(self, pct: int):
        self._on_progress(min(100, max(0, pct)))

    def _ensure_dir(self, p: Path):
        p.mkdir(parents=True, exist_ok=True)

    def _cleanup(self):
        for p in self._temp_files:
            try:
                if p.is_dir():
                    shutil.rmtree(p, ignore_errors=True)
                elif p.exists():
                    p.unlink()
            except Exception:
                pass

    def _run_subprocess(self, cmd, **kwargs):
        result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
        if result.returncode != 0:
            raise RuntimeError(
                f"Command failed: {' '.join(str(c) for c in cmd)}\n"
                f"stderr: {result.stderr[-2000:]}"
            )
        return result

    def _run_ffmpeg(self, args):
        return self._run_subprocess([_get_ffmpeg_exe()] + args)

    # ── YouTube / yt-dlp ──────────────────────────────────────────────────────

    def _download_youtube(self, url: str, output_dir: Path) -> Path:
        if self._stop:
            raise RuntimeError("Cancelled.")
        self._ensure_dir(output_dir)
        out_path = output_dir / "input_video.%(ext)s"
        start = self.cfg.get("start_seconds")
        end   = self.cfg.get("end_seconds")
        cmd = [
            "yt-dlp",
            "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "--merge-output-format", "mp4",
            "-o", str(out_path), url,
        ]
        if start is not None and end is not None and end > start:
            cmd += ["--download-sections", f"*{start}-{end}"]
            self.cfg["is_trimmed"] = True
        else:
            self.cfg["is_trimmed"] = False
        self.log("Downloading YouTube video…")
        self._run_subprocess(cmd)
        mp4s = list(output_dir.glob("input_video*.mp4"))
        if not mp4s:
            raise RuntimeError("❌ YouTube download failed — no mp4 produced.")
        self.log(f"Downloaded → {mp4s[0].name}")
        return mp4s[0]

    # ── Frame extraction ──────────────────────────────────────────────────────

    def _extract_frames_anim(self, video: Path, pack_root: Path) -> Path:
        if self._stop:
            raise RuntimeError("Cancelled.")
        dst = pack_root / ANIM_BG_DIR
        if dst.exists():
            shutil.rmtree(dst)
        self._ensure_dir(dst)
        n   = int(self.cfg.get("anim_frames", MAX_FRAMES))
        fps = self.cfg.get("fps", DEFAULT_FPS)
        out_pattern = dst / f"{FRAME_PREFIX_ANIM}%03d.png"
        self.log(f"Extracting up to {n} anim frames @ {fps}fps…")
        args = ["-y"]
        if not self.cfg.get("is_trimmed"):
            ss = self.cfg.get("start_seconds")
            en = self.cfg.get("end_seconds")
            if ss is not None:
                args += ["-ss", str(ss)]
            if en is not None and ss is not None:
                args += ["-t", str(en - ss)]
        args += ["-i", str(video), "-vf", f"fps={fps}", "-frames:v", str(n), str(out_pattern)]
        self._run_ffmpeg(args)
        return dst

    def _extract_frames_loading(self, video: Path, pack_root: Path) -> Path:
        if self._stop:
            raise RuntimeError("Cancelled.")
        dst = pack_root / LOADING_BG_DIR
        if dst.exists():
            shutil.rmtree(dst)
        self._ensure_dir(dst)
        n   = int(self.cfg.get("load_frames", MAX_FRAMES))
        fps = self.cfg.get("fps", DEFAULT_FPS)
        tmp_pat = dst / "load_%03d.png"
        args = ["-y"]
        if not self.cfg.get("is_trimmed"):
            ss = self.cfg.get("start_seconds")
            en = self.cfg.get("end_seconds")
            if ss is not None:
                args += ["-ss", str(ss)]
            if en is not None and ss is not None:
                args += ["-t", str(en - ss)]
        args += ["-i", str(video), "-vf", f"fps={fps}", "-frames:v", str(n), str(tmp_pat)]
        self._run_ffmpeg(args)
        for f in sorted(dst.glob("load_*.png")):
            m = re.match(r"load_(\d+)\.png", f.name)
            if m:
                f.rename(dst / f"{int(m.group(1))}.png")
        self.log(f"Loading frames extracted → {dst}")
        return dst

    def _extract_frame_static(self, video: Path, pack_root: Path) -> Path:
        if self._stop:
            raise RuntimeError("Cancelled.")
        dst = pack_root / ANIM_BG_DIR
        if dst.exists():
            shutil.rmtree(dst)
        self._ensure_dir(dst)
        out_pattern = dst / f"{FRAME_PREFIX_ANIM}%03d.png"
        self.log("Static mode: extracting 1 frame…")
        args = ["-y"]
        if not self.cfg.get("is_trimmed"):
            ss = self.cfg.get("start_seconds")
            if ss is not None:
                args += ["-ss", str(ss)]
        args += ["-i", str(video), "-vf", "fps=1", "-frames:v", "1", str(out_pattern)]
        self._run_ffmpeg(args)
        return dst

    def _use_image_as_background(self, img_src: Path, pack_root: Path) -> Path:
        if self._stop:
            raise RuntimeError("Cancelled.")
        dst = pack_root / ANIM_BG_DIR
        if dst.exists():
            shutil.rmtree(dst)
        self._ensure_dir(dst)
        out_path = dst / f"{FRAME_PREFIX_ANIM}001.png"
        if img_src.suffix.lower() == ".png":
            shutil.copy2(img_src, out_path)
            self.log(f"Image is already PNG — copied as {out_path.name}")
        else:
            self.log(f"Converting {img_src.name} → PNG…")
            Image.open(str(img_src)).convert("RGBA").save(str(out_path), "PNG")
        return dst

    def _gen_black_loading_frame(self, load_dir: Path):
        self._ensure_dir(load_dir)
        Image.new("RGB", (1, 1), (0, 0, 0)).save(str(load_dir / "1.png"), "PNG")
        self.log("Loading background: black frame generated ✓")

    # ── Copy loading BG images ────────────────────────────────────────────────

    def _copy_loading_bg_images(self, pack_root: Path, images: list[Path]):
        """
        images: list[Path] đã upload, sẽ được copy theo thứ tự index.
        Web không có dialog → user sắp xếp order trực tiếp trên frontend
        (frontend gửi theo thứ tự đúng).
        """
        dst = pack_root / LOADING_BG_DIR
        if dst.exists():
            shutil.rmtree(dst)
        self._ensure_dir(dst)
        for idx, img in enumerate(images, start=1):
            dst_name = dst / f"{idx}{img.suffix.lower()}"
            shutil.copy2(img, dst_name)
            self.log(f"Loading BG: copied {img.name} → {dst_name.name}")
        self.log(f"✓ {len(images)} loading BG image(s) copied.")
        return dst

    # ── blur.png ──────────────────────────────────────────────────────────────

    def _make_blur_png_for_dir(self, anim_dir: Path):
        if self._stop:
            raise RuntimeError("Cancelled.")
        frames = sorted(anim_dir.glob(f"{FRAME_PREFIX_ANIM}*.png"))
        if not frames:
            raise FileNotFoundError(f"No frames in {anim_dir} to create blur.png.")
        src      = frames[0]
        blur_out = anim_dir / "blur.png"
        try:
            import cv2
            img = cv2.imread(str(src))
            if img is not None:
                cv2.GaussianBlur(img, (31, 31), 0)
                cv2.imwrite(str(blur_out), cv2.GaussianBlur(img, (31, 31), 0))
                self.log(f"blur.png created via OpenCV → {blur_out}")
                return
        except Exception as e:
            self.log(f"OpenCV blur failed ({e}), falling back to Pillow…")
        Image.open(src).filter(ImageFilter.GaussianBlur(radius=15)).save(blur_out)
        self.log(f"blur.png created via Pillow → {blur_out}")

    # ── Audio ─────────────────────────────────────────────────────────────────

    def _copy_bgm_file(self, pack_root: Path, bgm_path: Path):
        if self._stop:
            raise RuntimeError("Cancelled.")
        bgm_name = re.sub(r'[\\/:*?"<>|]', "_", bgm_path.stem).strip() or "bgm"
        self.cfg["bgm_name"] = bgm_name
        dst_dir = pack_root / SOUNDS_DIR
        self._ensure_dir(dst_dir)
        dst = dst_dir / f"{bgm_name}.ogg"
        if bgm_path.suffix.lower() == ".ogg":
            shutil.copy2(bgm_path, dst)
            self.log(f"BGM copied: {bgm_path.name} → {dst.name}")
        else:
            self.log(f"Converting {bgm_path.name} → OGG Vorbis…")
            self._run_ffmpeg(["-y", "-i", str(bgm_path), "-acodec", "libvorbis", "-q:a", "6", str(dst)])
            self.log("BGM conversion done ✓")

    def _extract_audio_from_video(self, video: Path, pack_root: Path):
        bgm_name = re.sub(r'[\\/:*?"<>|]', "_", self.cfg.get("bgm_name", "bgm").strip()) or "bgm"
        sounds_path = pack_root / SOUNDS_DIR / f"{bgm_name}.ogg"
        self._ensure_dir(sounds_path.parent)
        bgm_start = self.cfg.get("bgm_start_seconds")
        bgm_end   = self.cfg.get("bgm_end_seconds")
        args = ["-y"]
        if bgm_start is not None:
            args += ["-ss", str(bgm_start)]
        if bgm_end is not None and bgm_start is not None:
            args += ["-t", str(bgm_end - bgm_start)]
        args += ["-i", str(video), "-vn", "-acodec", "libvorbis", "-q:a", "6", str(sounds_path)]
        self.log(f"Extracting audio → {sounds_path.name}")
        self._run_ffmpeg(args)
        self.cfg["bgm_name"] = bgm_name
        self.log("Audio extracted ✓")

    def _download_youtube_audio(self, url: str, pack_root: Path):
        bgm_name = re.sub(r'[\\/:*?"<>|]', "_", self.cfg.get("bgm_name", "bgm").strip()) or "bgm"
        dst = pack_root / SOUNDS_DIR
        self._ensure_dir(dst)
        out_tmpl = dst / f"{bgm_name}.%(ext)s"
        cmd = ["yt-dlp", "-x", "--audio-format", "vorbis", "-o", str(out_tmpl), url]
        self.log("Downloading YouTube audio…")
        self._run_subprocess(cmd)
        self.cfg["bgm_name"] = bgm_name
        self.log("YouTube audio downloaded ✓")

    # ── Pack icon ─────────────────────────────────────────────────────────────

    def _copy_pack_icon(self, pack_root: Path, icon_path: Optional[Path]):
        if not icon_path or not icon_path.exists():
            self.log("No pack icon specified — skipping.")
            return
        dst = pack_root / "pack_icon.png"
        img = Image.open(str(icon_path)).convert("RGBA")
        img = img.resize((256, 256), Image.LANCZOS)
        img.save(str(dst), "PNG")
        self.log(f"pack_icon.png saved (256×256) → {dst}")

    # ── Container background ──────────────────────────────────────────────────

    def _download_container_bg(self, pack_root: Path):
        if self._stop:
            raise RuntimeError("Cancelled.")
        import requests as req
        dst = pack_root / CONTAINER_BG_DIR
        self._ensure_dir(dst)
        self.log(f"Downloading container background…")
        try:
            r = req.get(CONTAINER_BG_URL, timeout=60)
            r.raise_for_status()
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                tmp.write(r.content)
                tmp_path = Path(tmp.name)
            with zipfile.ZipFile(tmp_path) as zf:
                zf.extractall(dst)
            tmp_path.unlink(missing_ok=True)
            self.log(f"Container background extracted → {dst}")
        except Exception as e:
            self.log(f"⚠️ Failed to download container background: {e}")

    # ── JSON generators (giữ nguyên logic từ new.py) ─────────────────────────

    def _gen_bg_anim_json(self, anim_dir: Path, pack_root: Path):
        _ANIM_EXTS = [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tga"]
        frames = []
        for ext in _ANIM_EXTS:
            frames = sorted(anim_dir.glob(f"{FRAME_PREFIX_ANIM}*{ext}"))
            if frames:
                break
        n = len(frames)
        if n == 0:
            self.log("⚠️ No anim frames found, skipping .hrzn_public_bg_anim.json")
            return
        lines = [
            '  "namespace": "hrzn_ui_wextension",',
            '  "hrzn_ui_settings_bg@core_img": { "texture": "hrzn_animated_background/blur" },',
            '  "img": { "type": "image", "fill": true, "property_bag": {"#true": "0"}, "bindings": [ { "binding_name": "#collection_index", "binding_type": "collection_details", "binding_collection_name": "animated_background" }, { "binding_type": "view", "source_property_name": "(\'#\' + (#collection_index < 9))", "target_property_name": "#pad00" }, { "binding_type": "view", "source_property_name": "(\'#\' + (#collection_index < 99))", "target_property_name": "#pad0" }, { "binding_type": "view", "source_property_name": "(\'hrzn_animated_background/hans\' + \'_common_\' + #pad00 + #pad0 + (#collection_index + 1))", "target_property_name": "#texture" } ] },',
            f'  "hrzn_ui_main_bg": {{ "size": [ "100%", "100%" ], "type": "stack_panel", "anchor_from": "top_left", "anchor_to": "top_left", "offset": "@hrzn_ui_wextension.01", "$duration_per_frame|default": 0.03333333, "$frames|default": {n}, "collection_name": "animated_background", "factory": {{"name": "test", "control_name": "hrzn_ui_wextension.img"}}, "property_bag": {{"#frames": "$frames"}}, "bindings": [ {{ "binding_type": "view", "source_property_name": "(#frames*1)", "target_property_name": "#collection_length" }} ] }},',
            '  "hans_anim_base": { "destroy_at_end": "@hrzn_ui_wextension.bg_anim", "anim_type": "offset", "easing": "linear", "duration": "$duration_per_frame", "from": "$anm_offset", "to": "$anm_offset" },',
            '',
        ]
        for i in range(1, n + 1):
            key      = f"{i:02d}"
            y_pct    = "0%" if i == 1 else f"-{(i-1)*100}%"
            next_key = f"{(i % n) + 1:02d}"
            lines.append(
                f'  "{key}@hrzn_ui_wextension.hans_anim_base":{{"$anm_offset": [ "0px", "{y_pct}" ],"next": "@hrzn_ui_wextension.{next_key}"}},')
        lines[-1] = lines[-1].rstrip(",")
        out_path = pack_root / ".hrzn_public_bg_anim.json"
        out_path.write_text("{\n" + "\n".join(lines) + "\n}", encoding="utf-8")
        self.log(f".hrzn_public_bg_anim.json generated ({n} frames)")

    def _gen_bg_load_json(self, load_dir: Path, pack_root: Path):
        IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        all_imgs = [f for f in load_dir.iterdir() if f.suffix.lower() in IMG_EXT]
        frames   = sorted(all_imgs, key=lambda p: int(p.stem) if p.stem.isdigit() else 0)
        n = len(frames)
        if n == 0:
            self.log("⚠️ No loading frames found, skipping .hrzn_public_bg_load.json")
            return
        ctrl_lines = [
            f'      {{ "{i}@hrzn_ui_load_wextension.img": {{ "$img": "{i}" }} }}{"," if i < n else ""}'
            for i in range(1, n + 1)
        ]
        anim_lines = []
        for i in range(1, n + 1):
            key      = f"{i:02d}"
            y_pct    = "0%" if i == 1 else f"-{(i-1)*100}%"
            next_key = f"{(i % n) + 1:02d}"
            trailing = "," if i < n else ""
            anim_lines.append(
                f'  "{key}@hrzn_ui_load_wextension.anim_base":{{"$anm_offset": [ 0, "{y_pct}" ],"next": "@hrzn_ui_load_wextension.{next_key}"}}{trailing}')
        content = (
            '{\n'
            '  "namespace": "hrzn_ui_load_wextension",\n\n'
            '  "anim_base": {\n'
            '    "anim_type": "offset",\n'
            '    "easing": "linear",\n'
            '    "duration": "$duration_loading_per_frame",\n'
            '    "from": "$anm_offset",\n'
            '    "to": "$anm_offset"\n'
            '  },\n\n'
            '  "img": {\n'
            '    "type": "image",\n'
            '    "fill": true,\n'
            '    "bilinear": true,\n'
            '    "size": [ "100%", "100%" ],\n'
            '    "texture": "(\'hrzn_loading_background/\' + $img )"\n'
            '  },\n\n'
            '  "hans_load_background": {\n'
            '    "type": "stack_panel",\n'
            '    "size": [ "100%", "100%" ],\n'
            '    "anchor_from": "top_left",\n'
            '    "anchor_to": "top_left",\n'
            '    "offset": "@hrzn_ui_load_wextension.01",\n'
            '    "$duration_per_frame|default": 1.5,\n'
            '    "controls": [\n'
            + "\n".join(ctrl_lines) + "\n"
            '    ]\n'
            '  },\n'
            '  /*///// FRAMES /////*/\n'
            + "\n".join(anim_lines) + "\n"
            "}"
        )
        out_path = pack_root / ".hrzn_public_bg_load.json"
        out_path.write_text(content, encoding="utf-8")
        self.log(f".hrzn_public_bg_load.json generated ({n} frames)")

    def _gen_manifest(self, pack_root: Path):
        ext_name = self.cfg.get("pack_name", "MyExtension")
        ver_str  = self.cfg.get("version", "1.0.0")
        try:
            ver_parts = [int(x) for x in ver_str.split(".")]
            while len(ver_parts) < 3:
                ver_parts.append(0)
        except Exception:
            ver_parts = [1, 0, 0]
        min_eng  = self.cfg.get("min_engine", "1.20.0")
        try:
            min_eng_parts = [int(x) for x in min_eng.split(".")]
            while len(min_eng_parts) < 3:
                min_eng_parts.append(0)
        except Exception:
            min_eng_parts = [1, 20, 0]

        desc = (
            "§lFirst use restart the game!\n"
            "Original Creator : Han's404 | Youtube: @zxyn404 ( Han's )\n"
            f"Extension Creator : {self.cfg.get('creator', 'Unknown')}\n"
            "Built with TuBeo5866's HorizonUI/NekoUI Extension Studio"
        )
        data = {
            "format_version": 2,
            "header": {
                "description": desc,
                "name": f"§l§dHorizon§bUI: {ext_name}",
                "uuid": self.cfg.get("uuid") or str(uuid.uuid4()),
                "version": ver_parts,
                "min_engine_version": min_eng_parts,
            },
            "modules": [{
                "description": desc,
                "type": "resources",
                "uuid": self.cfg.get("uuid2") or str(uuid.uuid4()),
                "version": ver_parts,
            }],
        }
        (pack_root / "manifest.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8"
        )
        self.log("manifest.json generated ✓")

    def _gen_global_variables(self, pack_root: Path):
        ver   = self.cfg.get("version", "1.0.0")
        creator = self.cfg.get("creator", "Unknown")
        content = f"""{{
  "$hrzn.ui.use_extension": true,
  "$hrzn.ui.creator_name": "{creator}",
  "$hrzn.ui.extension_version": "{ver}",
  "$duration_per_frame": 0.05,
  "$duration_loading_per_frame": 2,
  "$horizon_radio_unchecked_color": [1, 1, 1, 0],
  "$horizon_radio_unchecked_hover_color": [1, 1, 1, 0],
  "$horizon_radio_checked_color": [1, 1, 1, 0],
  "$horizon_radio_checked_hover_color": [1, 1, 1, 0],
  "$horizon_slider_step_background_color": [1, 1, 1, 0],
  "$horizon_slider_step_background_hover_color": [1, 1, 1, 0],
  "$horizon_slider_step_progress_progress_color": [1, 1, 1, 0],
  "$horizon_slider_step_progress_progress_hover_color": [1, 1, 1, 0],
  "$horizon_slider_background_color": [1, 1, 1, 0],
  "$horizon_slider_background_hover_color": [1, 1, 1, 0],
  "$horizon_slider_progress_color": [1, 1, 1, 0],
  "$horizon_slider_progress_hover_color": [1, 1, 1, 0],
  "$horizon_slider_slider_border_color": [1, 1, 1, 0],
  "$horizon_toggle_on_hover_color": [1, 1, 1, 0],
  "$horizon_toggle_on_color": [1, 1, 1, 0],
  "$horizon_toggle_off_color": [1, 1, 1, 0],
  "$horizon_toggle_off_hover_color": [1, 1, 1, 0],
  "$light_toggle_default_text_color": [1, 1, 1, 0],
  "$light_toggle_hover_text_color": [1, 1, 1, 0],
  "$light_toggle_checked_hover_text_color": [1, 1, 1, 0],
  "$light_toggle_checked_default_text_color": [1, 1, 1, 0],
  "$hrzn.ui.force_skin": false,
  "$hrzn.ui.do_not_use_viegnette": false
}}"""
        ui_dir = pack_root / UI_DIR
        self._ensure_dir(ui_dir)
        (ui_dir / "_global_variables.json").write_text(content, encoding="utf-8")
        self.log("ui/_global_variables.json generated ✓")

    def _gen_music_definitions(self, pack_root: Path):
        content = {"menu": {"event_name": "music.menu", "max_delay": 30, "min_delay": 0}}
        out = pack_root / "sounds" / "music_definitions.json"
        self._ensure_dir(out.parent)
        out.write_text(json.dumps(content, ensure_ascii=False, indent=3), encoding="utf-8")
        self.log("sounds/music_definitions.json generated ✓")

    def _gen_sound_definitions(self, pack_root: Path):
        bgm_name = re.sub(r'[\\/:*?"<>|]', "_", self.cfg.get("bgm_name", "bgm").strip()) or "bgm"
        content = {
            "format_version": "1.20.20",
            "sound_definitions": {
                "music.menu": {
                    "__use_legacy_max_distance": "true",
                    "category": "music",
                    "max_distance": None,
                    "min_distance": None,
                    "sounds": [{"name": f"sounds/music/bgm/{bgm_name}", "stream": True, "volume": 0.30}],
                }
            },
        }
        out = pack_root / "sounds" / "sound_definitions.json"
        self._ensure_dir(out.parent)
        out.write_text(json.dumps(content, ensure_ascii=False, indent=3), encoding="utf-8")
        self.log("sounds/sound_definitions.json generated ✓")

    # ── Main process ──────────────────────────────────────────────────────────

    def process(self):
        total_steps = 14
        step        = [0]

        def tick(label=""):
            step[0] += 1
            self.progress(int(step[0] / total_steps * 100))
            if label:
                self.log(f"[{step[0]}/{total_steps}] {label}")

        # ── Resolve paths ──────────────────────────────────────────────────
        work_dir  = Path(self.cfg["work_dir"])
        ext_name  = self.cfg["pack_name"].strip()
        safe_name = re.sub(r'[\\/:*?"<>|]', "_", ext_name) or "extension"
        pack_root = work_dir / "pack"
        if pack_root.exists():
            shutil.rmtree(pack_root)
        self._ensure_dir(pack_root)
        self._temp_files.append(pack_root)
        tick("Pack folder created")

        for d in [ANIM_BG_DIR, LOADING_BG_DIR, CONTAINER_BG_DIR, SOUNDS_DIR, UI_DIR]:
            self._ensure_dir(pack_root / d)
        tick("Directory structure created")

        # ── Animated background ────────────────────────────────────────────
        anim_dir = None
        if self.cfg.get("enable_anim_bg", True):
            anim_source = self.cfg.get("anim_source", "file")

            if anim_source == "youtube":
                yt_url = self.cfg.get("youtube_url", "").strip()
                if not yt_url:
                    raise ValueError("YouTube URL is empty.")
                yt_tmp = work_dir / "_yt_tmp"
                video  = self._download_youtube(yt_url, yt_tmp)
                self._temp_files.append(yt_tmp)
                anim_dir = self._extract_frames_anim(video, pack_root)

            else:  # file
                anim_files = self.cfg.get("anim_file_paths", [])
                if not anim_files:
                    raise ValueError("No animation files uploaded.")
                first = Path(anim_files[0])
                # Single image → use as static BG
                if first.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"} \
                        and len(anim_files) == 1 \
                        and first.suffix.lower() != ".gif":
                    anim_dir = self._use_image_as_background(first, pack_root)
                else:
                    # Video file or GIF → extract frames
                    anim_dir = self._extract_frames_anim(first, pack_root)

            tick("Animated background prepared")
        else:
            # Create a single black frame as placeholder
            anim_dir = pack_root / ANIM_BG_DIR
            self._ensure_dir(anim_dir)
            Image.new("RGB", (1, 1), (0, 0, 0)).save(
                str(anim_dir / f"{FRAME_PREFIX_ANIM}001.png"), "PNG"
            )
            tick("Animated background skipped (black placeholder)")

        # ── Loading background ─────────────────────────────────────────────
        loading_files = self.cfg.get("loading_file_paths", [])
        if self.cfg.get("enable_loading_bg", False) and loading_files:
            load_dir = self._copy_loading_bg_images(
                pack_root, [Path(p) for p in loading_files]
            )
            tick("Loading background images copied")
        else:
            load_dir = pack_root / LOADING_BG_DIR
            self._ensure_dir(load_dir)
            # Copy first anim frame as loading BG
            src_frame = anim_dir / f"{FRAME_PREFIX_ANIM}001.png"
            if src_frame.exists():
                shutil.copy2(src_frame, load_dir / "1.png")
            else:
                self._gen_black_loading_frame(load_dir)
            tick("Loading background: auto-generated from anim frame")

        # ── blur.png ───────────────────────────────────────────────────────
        self._make_blur_png_for_dir(anim_dir)
        tick("blur.png created")

        # ── Container background ───────────────────────────────────────────
        self._download_container_bg(pack_root)
        tick("Container background downloaded")

        # ── BGM ────────────────────────────────────────────────────────────
        if self.cfg.get("enable_bgm", True):
            bgm_source = self.cfg.get("bgm_source", "file")
            bgm_file_path = self.cfg.get("bgm_file_path")

            if bgm_source == "youtube":
                bgm_url = self.cfg.get("bgm_youtube_url", "").strip()
                if bgm_url:
                    self._download_youtube_audio(bgm_url, pack_root)
                else:
                    self.log("⚠️ BGM YouTube URL empty — skipping audio.")
            elif bgm_file_path and Path(bgm_file_path).exists():
                self._copy_bgm_file(pack_root, Path(bgm_file_path))
            else:
                self.log("⚠️ No BGM file — skipping audio.")
        else:
            self.log("BGM disabled — skipping.")
        tick("Audio prepared")

        # ── Pack icon ──────────────────────────────────────────────────────
        if self.cfg.get("enable_icon", True):
            icon_path = self.cfg.get("icon_file_path")
            self._copy_pack_icon(pack_root, Path(icon_path) if icon_path else None)
        tick("Pack icon processed")

        # ── JSON files ─────────────────────────────────────────────────────
        self._gen_bg_anim_json(anim_dir, pack_root)
        self._gen_bg_load_json(load_dir, pack_root)
        self._gen_manifest(pack_root)
        self._gen_global_variables(pack_root)
        self._gen_music_definitions(pack_root)
        self._gen_sound_definitions(pack_root)
        tick("JSON files generated")

        # ── Pack to .mcpack / .zip ─────────────────────────────────────────
        output_name   = re.sub(r'[\\/:*?"<>|]', "_", self.cfg.get("output_name", safe_name)).strip() or safe_name
        output_format = self.cfg.get("output_format", "mcpack")
        out_file      = work_dir / f"{output_name}.{output_format}"
        if out_file.exists():
            out_file.unlink()

        self.log(f"Packing → {out_file.name}")
        archive_base = str(out_file.with_suffix(""))
        shutil.make_archive(archive_base, "zip", pack_root)
        zip_tmp = out_file.with_suffix(".zip")
        if zip_tmp.exists():
            zip_tmp.rename(out_file)
        tick("Archive created")

        # ── Cleanup pack dir (keep output file) ────────────────────────────
        shutil.rmtree(pack_root, ignore_errors=True)
        self._temp_files = [p for p in self._temp_files if p != pack_root]
        tick("Cleanup done")

        self.cfg["output_path"] = str(out_file)
        self.log(f"\n✅ Done! Output: {out_file.name}")
        self.progress(100)
        return True

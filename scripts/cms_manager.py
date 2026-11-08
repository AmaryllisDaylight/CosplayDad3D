#!/usr/bin/env python3
"""
@cosplaydad3d Automated Content Management System (Zero-API Local Pipeline)
===========================================================================
- Converts .HEIC to .jpg and IMMEDIATELY deletes the .HEIC file (no .HEIC kept).
- Resizes/pads images (1440x1800 4:5) and videos (1080x1350 4:5 Carousel or
  1080x1920 9:16 Reel via ffmpeg) for Instagram.
- Builds TRACKER.md and an interactive Human-Review HTML Dashboard
  (CosplayDad_Dashboard.html) with:
    * '✕' Veto button (immediately removes the pic/video from the HTML carousel)
    * '★ #1' button (promotes any pic/video to Slide #1 Hero)
    * '◀' / '▶' reorder buttons
    * '✓ Approve' batch button
    * One-click "Posted Today" & Archive controls:
        - 📸 Posted IG Today (or IG Only + Archive)
        - 🟢 Posted MW Today (or MW Only + Archive)
        - 🚀 Posted Both Today & Archive
        - Records exact date (YYYY-MM-DD) & platform(s), moves card to Archive tab
    * Editable short captions (<textarea>)
    * 'apply-review' CLI command ("clean up") to physically move archived batches
      to 03_Posted_Archive/, move vetoed slides to _Vetoed_Archive/, renumber
      surviving slides, and record posted dates/platforms in POST_COPY.md & TRACKER.md.
"""

from __future__ import annotations

import argparse
import datetime
import html
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps
import pillow_heif
from mw_pipeline import (
    MW_MODELS_DIR,
    CONCEPT_VAULT_DIR,
    MW_STAGE_FOLDERS,
    auto_organize_all_mw_projects,
    collect_mw_models,
    inspect_stl_file,
    route_cad_file_to_project,
)
from firebase_sync import (
    FIRESTORE_DOC_URL,
    LIVE_DASHBOARD_URL,
    clear_cloud_review_state,
    fetch_cloud_review_state,
    stage_and_deploy_firebase,
)
from path_config import find_drive_root, find_workspace_root

pillow_heif.register_heif_opener()

DRIVE_ROOT = find_drive_root()
WORKSPACE_ROOT = find_workspace_root()

INBOX_DIR = DRIVE_ROOT / "01_Inbox_Drop"
READY_DIR = DRIVE_ROOT / "02_Ready_To_Post"
ARCHIVE_DIR = DRIVE_ROOT / "03_Posted_Archive"
BACKUP_DIR = DRIVE_ROOT / "99_Raw_Originals_Backup"
VETOED_DIR = BACKUP_DIR / "_Vetoed_Archive"
TRACKER_PATH = DRIVE_ROOT / "TRACKER.md"
DASHBOARD_PATH = DRIVE_ROOT / "CosplayDad_Dashboard.html"
REVIEW_JSON_PATH = DRIVE_ROOT / "review_decisions.json"

IG_WIDTH = 1440
IG_HEIGHT = 1800
IG_RATIO = IG_WIDTH / IG_HEIGHT  # 0.80 (4:5)

VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm", ".avi"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
HEIC_EXTS = {".heic", ".heif"}


def ensure_directories() -> None:
    """Create the core directory hierarchy in G:\\My Drive\\!cosplaydad3d."""
    for d in [INBOX_DIR, READY_DIR, ARCHIVE_DIR, BACKUP_DIR, VETOED_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def purge_any_heic_files(folder: Path) -> int:
    """Convert any .HEIC files in a folder to .jpg and delete the .HEIC immediately."""
    if not folder.exists():
        return 0
    count = 0
    seen = set()
    for p in sorted(folder.iterdir()):
        if p.is_file() and p.suffix.lower() in HEIC_EXTS and p.resolve() not in seen:
            seen.add(p.resolve())
            jpg_out = folder / f"{p.stem}.jpg"
            if not jpg_out.exists():
                with Image.open(p) as im:
                    im_rgb = ImageOps.exif_transpose(im).convert("RGB")
                    im_rgb.save(jpg_out, "JPEG", quality=95)
            p.unlink()
            count += 1
            print(f"Converted & deleted HEIC: {p.name} -> {jpg_out.name}")
    return count


def format_for_instagram(
    src_path: Path,
    dst_path: Path,
    mode: str = "auto",
) -> str:
    """Format an image into a 1440x1800 (4:5) Instagram-ready JPEG."""
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src_path) as raw_im:
        im = ImageOps.exif_transpose(raw_im).convert("RGB")
        w, h = im.size
        src_ratio = w / h

        actual_mode = mode
        if actual_mode == "auto":
            actual_mode = "pad" if src_ratio > 0.95 else "crop"

        if actual_mode == "crop":
            if src_ratio > IG_RATIO:
                new_w = int(round(h * IG_RATIO))
                left = (w - new_w) // 2
                cropped = im.crop((left, 0, left + new_w, h))
            else:
                new_h = int(round(w / IG_RATIO))
                top = (h - new_h) // 2
                cropped = im.crop((0, top, w, top + new_h))
            out = cropped.resize((IG_WIDTH, IG_HEIGHT), Image.Resampling.LANCZOS)
            out.save(dst_path, "JPEG", quality=93, optimize=True)
            return "crop"

        bg_scale = max(IG_WIDTH / w, IG_HEIGHT / h)
        bg_w, bg_h = int(round(w * bg_scale)), int(round(h * bg_scale))
        bg = im.resize((bg_w, bg_h), Image.Resampling.BILINEAR)
        bg_left = (bg_w - IG_WIDTH) // 2
        bg_top = (bg_h - IG_HEIGHT) // 2
        bg = bg.crop((bg_left, bg_top, bg_left + IG_WIDTH, bg_top + IG_HEIGHT))
        bg = bg.filter(ImageFilter.GaussianBlur(radius=42))
        bg = ImageEnhance.Brightness(bg).enhance(0.28)
        bg = ImageEnhance.Color(bg).enhance(0.65)

        margin_factor = 0.96
        max_fg_w = int(IG_WIDTH * margin_factor)
        max_fg_h = int(IG_HEIGHT * margin_factor)
        fg_scale = min(max_fg_w / w, max_fg_h / h)
        fg_w = int(round(w * fg_scale))
        fg_h = int(round(h * fg_scale))
        fg = im.resize((fg_w, fg_h), Image.Resampling.LANCZOS)

        canvas = bg.convert("RGBA")
        shadow = Image.new("RGBA", (fg_w + 24, fg_h + 24), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rectangle([12, 12, fg_w + 12, fg_h + 12], fill=(0, 0, 0, 165))
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=10))

        fg_x = (IG_WIDTH - fg_w) // 2
        fg_y = (IG_HEIGHT - fg_h) // 2
        canvas.alpha_composite(shadow, (fg_x - 12, fg_y - 12))
        canvas.paste(fg, (fg_x, fg_y))

        border_draw = ImageDraw.Draw(canvas)
        border_draw.rectangle(
            [fg_x, fg_y, fg_x + fg_w - 1, fg_y + fg_h - 1],
            outline=(255, 255, 255, 38),
            width=2,
        )

        canvas.convert("RGB").save(dst_path, "JPEG", quality=93, optimize=True)
        return "pad"


def format_video_for_instagram(
    src_path: Path,
    dst_path: Path,
    aspect: str = "4x5",
) -> Path:
    """Resize and pad a video (.mov, .mp4, .m4v) for Instagram using ffmpeg."""
    dst_path = dst_path.with_suffix(".mp4")
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    target_w, target_h = (1080, 1350) if aspect == "4x5" else (1080, 1920)

    vf = (
        f"split[bg][fg];"
        f"[bg]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
        f"crop={target_w}:{target_h},boxblur=28:4,eq=brightness=-0.35:saturation=0.65[bg_out];"
        f"[fg]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease[fg_out];"
        f"[bg_out][fg_out]overlay=(W-w)/2:(H-h)/2,format=yuv420p"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src_path),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(dst_path),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    poster_path = dst_path.with_suffix(".poster.jpg")
    poster_cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        "00:00:00.500",
        "-i",
        str(dst_path),
        "-frames:v",
        "1",
        "-q:v",
        "3",
        str(poster_path),
    ]
    res = subprocess.run(poster_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0 or not poster_path.exists():
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(dst_path),
                "-frames:v",
                "1",
                "-q:v",
                "3",
                str(poster_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    print(f"Formatted video for Instagram ({aspect} {target_w}x{target_h}): {dst_path.name}")
    return dst_path


def extract_video_Sheet_for_inspection(video_path: Path, out_jpg: Path) -> Path:
    """Extract 4 keyframes from a video into a 2x2 grid JPEG so Antigravity can inspect it."""
    out_jpg.parent.mkdir(parents=True, exist_ok=True)
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ],
        capture_output=True,
        text=True,
    )
    try:
        dur = max(float(probe.stdout.strip()), 1.0)
    except ValueError:
        dur = 4.0

    fps_val = 4.0 / dur
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"fps={fps_val:.4f},scale=540:-1,tile=2x2",
        "-frames:v",
        "1",
        "-q:v",
        "4",
        str(out_jpg),
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return out_jpg


def parse_post_copy(md_path: Path) -> Dict[str, str]:
    """Extract metadata, posting dates/platforms, Instagram caption, and MakerWorld text from POST_COPY.md."""
    result = {
        "title": md_path.parent.name,
        "category": "Cosplay Build",
        "makerworld_mode": "Make / Build Note",
        "designer_credit": "@cosplaydad3d",
        "approval": "Needs Review",
        "ig_posted_date": "",
        "mw_posted_date": "",
        "posted_platforms": "Not Posted Yet",
        "ig_caption": "",
        "mw_text": "",
    }
    if not md_path.exists():
        return result

    text = md_path.read_text(encoding="utf-8")

    patterns = {
        "title": r"^#\s+(.+)$",
        "category": r"\*\*Category\*\*:\s*(.+)$",
        "makerworld_mode": r"\*\*MakerWorld Type\*\*:\s*(.+)$",
        "designer_credit": r"\*\*Designer Credit\*\*:\s*(.+)$",
        "approval": r"\*\*Review Status\*\*:\s*(.+)$",
        "ig_posted_date": r"\*\*Instagram Posted Date\*\*:\s*(.+)$",
        "mw_posted_date": r"\*\*MakerWorld Posted Date\*\*:\s*(.+)$",
        "posted_platforms": r"\*\*Posted Platforms\*\*:\s*(.+)$",
    }
    for key, pat in patterns.items():
        m = re.search(pat, text, re.MULTILINE)
        if m:
            val = m.group(1).strip().strip("`")
            if val not in ("-", "None", "Pending"):
                result[key] = val

    ig_m = re.search(
        r"##\s*1\.\s*Instagram Caption & Hashtags.*?```(?:text|markdown)?\n(.*?)```",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if ig_m:
        result["ig_caption"] = ig_m.group(1).strip()

    mw_m = re.search(
        r"##\s*2\.\s*MakerWorld Text.*?```(?:text|markdown)?\n(.*?)```",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if mw_m:
        result["mw_text"] = mw_m.group(1).strip()

    return result


def write_updated_post_copy(
    md_path: Path,
    meta: Dict[str, str],
    slide_files: List[Path],
) -> None:
    """Write or update POST_COPY.md with current slides, approval, posting dates/platforms, and captions."""
    slide_lines = []
    for idx, p in enumerate(slide_files, start=1):
        role = "HERO SLIDE (#1)" if idx == 1 else f"Carousel Slide #{idx}"
        kind = "VIDEO (4:5 MP4)" if p.suffix.lower() in VIDEO_EXTS else "PHOTO (4:5 JPG)"
        slide_lines.append(f"- **`{p.name}`** ({role}) — `{kind}`")

    ig_date = meta.get("ig_posted_date", "") or "Pending"
    mw_date = meta.get("mw_posted_date", "") or "Pending"
    platforms = meta.get("posted_platforms", "") or "Not Posted Yet"

    content = f"""# {meta['title']}

- **Batch Folder**: `{md_path.parent.name}`
- **Category**: {meta['category']}
- **Designer Credit**: {meta['designer_credit']}
- **MakerWorld Type**: {meta['makerworld_mode']}
- **Review Status**: {meta.get('approval', 'Needs Review')}
- **Posted Platforms**: {platforms}
- **Instagram Posted Date**: `{ig_date}`
- **MakerWorld Posted Date**: `{mw_date}`
- **Total Slides**: `{len(slide_files)}`

## Slide Manifest (`Instagram_Carousel/`)
{chr(10).join(slide_lines)}

---

## 1. Instagram Caption & Hashtags

```text
{meta['ig_caption'].strip()}
```

---

## 2. MakerWorld Text ({meta['makerworld_mode']})

```markdown
{meta['mw_text'].strip()}
```
"""
    md_path.write_text(content, encoding="utf-8")


def collect_batches(directory: Path, status: str) -> List[Dict]:
    """Scan a directory (02_Ready_To_Post or 03_Posted_Archive) for Batch folders."""
    batches = []
    if not directory.exists():
        return batches

    for folder in sorted(directory.iterdir()):
        if not folder.is_dir() or not folder.name.startswith("Batch_"):
            continue

        ig_dir = folder / "Instagram_Carousel"
        mw_dir = folder / "MakerWorld"
        post_copy_path = folder / "POST_COPY.md"

        ig_slides = []
        if ig_dir.exists():
            for p in sorted(ig_dir.iterdir()):
                if (
                    p.is_file()
                    and p.suffix.lower() in (IMAGE_EXTS | VIDEO_EXTS)
                    and not p.name.endswith(".poster.jpg")
                ):
                    ig_slides.append(p)

        mw_files = sorted(
            [p for p in mw_dir.iterdir() if p.is_file()] if mw_dir.exists() else []
        )
        copy_data = parse_post_copy(post_copy_path)

        batch_num_m = re.match(r"^Batch_(\d+)_(.*)$", folder.name)
        batch_num = batch_num_m.group(1) if batch_num_m else "00"
        slug = batch_num_m.group(2).replace("_", " ") if batch_num_m else folder.name

        slides_info = []
        for p in ig_slides:
            is_vid = p.suffix.lower() in VIDEO_EXTS
            poster = p.with_suffix(".poster.jpg")
            slides_info.append(
                {
                    "name": p.name,
                    "rel": p.relative_to(DRIVE_ROOT).as_posix(),
                    "is_video": is_vid,
                    "poster_rel": (
                        poster.relative_to(DRIVE_ROOT).as_posix()
                        if is_vid and poster.exists()
                        else ""
                    ),
                }
            )

        batches.append(
            {
                "folder_name": folder.name,
                "batch_num": batch_num,
                "slug": slug,
                "status": status,
                "archived": status == "Posted",
                "approval": copy_data.get("approval", "Needs Review"),
                "ig_posted_date": copy_data.get("ig_posted_date", ""),
                "mw_posted_date": copy_data.get("mw_posted_date", ""),
                "posted_platforms": copy_data.get("posted_platforms", "Not Posted Yet"),
                "title": copy_data["title"],
                "category": copy_data["category"],
                "makerworld_mode": copy_data["makerworld_mode"],
                "designer_credit": copy_data["designer_credit"],
                "ig_caption": copy_data["ig_caption"],
                "mw_text": copy_data["mw_text"],
                "slide_count": len(slides_info),
                "mw_file_count": len(mw_files),
                "slides": slides_info,
                "hero_filename": slides_info[0]["name"] if slides_info else "N/A",
                "updated_at": datetime.datetime.fromtimestamp(
                    folder.stat().st_mtime
                ).strftime("%Y-%m-%d"),
            }
        )
    return batches


def build_tracker_and_dashboard() -> None:
    """Regenerate TRACKER.md and CosplayDad_Dashboard.html in G:\\My Drive\\!cosplaydad3d."""
    purge_any_heic_files(BACKUP_DIR)
    auto_organize_all_mw_projects()
    ready_batches = collect_batches(READY_DIR, "Ready to Post")
    posted_batches = collect_batches(ARCHIVE_DIR, "Posted")
    mw_models = collect_mw_models()
    inbox_files = (
        [p for p in INBOX_DIR.iterdir() if p.is_file() and not p.name.startswith(".")]
        if INBOX_DIR.exists()
        else []
    )
    backup_originals = (
        [
            p
            for p in BACKUP_DIR.iterdir()
            if p.is_file() and p.suffix.lower() in (IMAGE_EXTS | VIDEO_EXTS)
        ]
        if BACKUP_DIR.exists()
        else []
    )

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    # 1. Generate TRACKER.md
    lines = [
        "# @cosplaydad3d Master Content Tracker",
        "",
        f"> **Last Updated**: `{now_str}`  ",
        f"> **Ready Queue**: `{len(ready_batches)}` batches | **Posted Archive**: `{len(posted_batches)}` batches | **MakerWorld 3D Models**: `{len(mw_models)}` projects | **Inbox Drop**: `{len(inbox_files)}` files | **JPG/Video Originals Backup**: `{len(backup_originals)}` files (Zero `.HEIC` policy active)",
        "",
        "## Quick Commands (in Antigravity)",
        "- **`do it`** *(or **`process inbox`**)* — Scan `01_Inbox_Drop/`, convert any `.HEIC` to `.jpg` & delete the `.HEIC`, resize any videos (`ffmpeg` 4:5 or 9:16), auto-route `.stl` (`>500k` Tripo vs `<=500k` Final) / `.blend` / `.3mf` files, sort AI paint/finish concepts, and refresh the dashboard.",
        "- **`clean up`** *(or **`apply review`**)* — Apply your photo/video vetoes (`✕`), `#1 Hero` promotions (`★`), caption edits, and **Posted Today / Archive** selections (`Instagram Only`, `MakerWorld Only`, or `Both`) from `CosplayDad_Dashboard.html` directly to the folders on disk.",
        "- **`posted Batch XX [ig|mw|both]`** — Move `Batch_XX_...` to `03_Posted_Archive/`, stamp today's date + platform, and update this tracker & dashboard.",
        "",
        "---",
        "",
        "## Active Queue (`02_Ready_To_Post/`)",
        "",
        "| Batch # | Review Status | IG Posted | MW Posted | Batch Folder | Title & Build | Slides | Slide #1 Hero |",
        "| :---: | :---: | :---: | :---: | :--- | :--- | :---: | :--- |",
    ]

    if ready_batches:
        for b in ready_batches:
            ig_d = f"`{b['ig_posted_date']}`" if b["ig_posted_date"] else "-"
            mw_d = f"`{b['mw_posted_date']}`" if b["mw_posted_date"] else "-"
            lines.append(
                f"| **#{b['batch_num']}** | **{b['approval']}** | {ig_d} | {mw_d} | `{b['folder_name']}` | {b['title']} | {b['slide_count']} | `{b['hero_filename']}` |"
            )
    else:
        lines.append("| - | - | - | - | *No batches in Ready queue* | - | 0 | - |")

    lines.extend(
        [
            "",
            "---",
            "",
            "## MakerWorld 3D Model Pipeline (`04_MakerWorld_Models/`)",
            "",
            "| Model Folder | Title | 01 4-Pose | 02 Paint Concepts | 03 Tripo 90MB | 04 Blender | 05 STL <500k | 06 Bambu .3MF | 07 Print Pics |",
            "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
        ]
    )

    for m in mw_models:
        sc = m["stage_counts"]
        lines.append(
            f"| `{m['folder_name']}` | {m['title']} | {sc.get('01_4Pose_Turnarounds', 0)} | {sc.get('02_Paint_And_Finish_Concepts', 0)} | {sc.get('03_Tripo_Raw_90MB', 0)} | {sc.get('04_Blender_Working', 0)} | **{sc.get('05_Final_STL_Under500k', 0)}** | **{sc.get('06_Bambu_3MF_Profile', 0)}** | **{sc.get('07_Real_Print_Photos', 0)}** |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## Posted Archive (`03_Posted_Archive/`)",
            "",
            "| Batch # | Platforms Used | IG Date | MW Date | Batch Folder | Title & Build | Slides |",
            "| :---: | :---: | :---: | :---: | :--- | :--- | :---: |",
        ]
    )

    if posted_batches:
        for b in posted_batches:
            ig_d = f"`{b['ig_posted_date']}`" if b["ig_posted_date"] else "-"
            mw_d = f"`{b['mw_posted_date']}`" if b["mw_posted_date"] else "-"
            lines.append(
                f"| **#{b['batch_num']}** | **{b['posted_platforms']}** | {ig_d} | {mw_d} | `{b['folder_name']}` | {b['title']} | {b['slide_count']} |"
            )
    else:
        lines.append("| - | - | - | - | *No archived batches yet* | - | 0 |")

    lines.append("")
    TRACKER_PATH.write_text("\n".join(lines), encoding="utf-8")

    # 2. Build interactive CosplayDad_Dashboard.html
    batches_payload = json.dumps(ready_batches + posted_batches)
    mw_models_payload = json.dumps(mw_models)

    dashboard_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>@cosplaydad3d Review &amp; Post Dashboard</title>
    <style>
        :root {{
            --bg-dark: #0b0e14;
            --bg-card: #131822;
            --bg-panel: #0d1118;
            --border: #252f42;
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --accent-blue: #38bdf8;
            --accent-green: #22c55e;
            --accent-red: #ef4444;
            --accent-gold: #f59e0b;
            --accent-ig: #e1306c;
            --accent-mw: #00c853;
        }}
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif;
            background: radial-gradient(circle at top right, #162032 0%, var(--bg-dark) 55%);
            color: var(--text-main);
            min-height: 100vh;
            padding: 24px 28px 90px;
            line-height: 1.45;
        }}
        .top-bar {{
            max-width: 1500px;
            margin: 0 auto 16px;
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 16px;
            background: rgba(19, 24, 34, 0.92);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 18px 24px;
        }}
        .brand-block h1 {{
            font-size: 1.45rem;
            font-weight: 800;
        }}
        .brand-handle {{
            color: var(--accent-blue);
        }}
        .brand-sub {{
            color: var(--text-muted);
            font-size: 0.85rem;
            margin-top: 3px;
        }}
        .top-controls {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            align-items: center;
        }}
        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 8px 14px;
            border-radius: 8px;
            border: 1px solid var(--border);
            background: var(--bg-panel);
            color: var(--text-main);
            font-weight: 600;
            font-size: 0.82rem;
            cursor: pointer;
            transition: all 0.14s ease;
        }}
        .btn:hover {{
            border-color: var(--accent-blue);
            background: rgba(56, 189, 248, 0.12);
        }}
        .btn-primary {{
            background: linear-gradient(135deg, #0284c7, #2563eb);
            border-color: transparent;
            color: #fff;
        }}
        .btn-success {{
            background: linear-gradient(135deg, #16a34a, #059669);
            border-color: transparent;
            color: #fff;
        }}
        .review-bar {{
            max-width: 1500px;
            margin: 0 auto 22px;
            background: rgba(19, 24, 34, 0.85);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 12px 20px;
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            font-size: 0.85rem;
        }}
        .filter-tabs {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}
        .tab-btn {{
            padding: 7px 14px;
            border-radius: 8px;
            border: 1px solid var(--border);
            background: var(--bg-panel);
            color: var(--text-muted);
            font-weight: 700;
            font-size: 0.82rem;
            cursor: pointer;
        }}
        .tab-btn.active {{
            background: rgba(56, 189, 248, 0.16);
            color: #fff;
            border-color: var(--accent-blue);
        }}
        .review-stats {{
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }}
        .pill-stat {{
            background: rgba(15, 23, 42, 0.85);
            border: 1px solid var(--border);
            padding: 4px 10px;
            border-radius: 999px;
            font-weight: 700;
            font-size: 0.76rem;
        }}
        .pill-stat.veto-count {{ color: #fca5a5; border-color: rgba(239, 68, 68, 0.4); }}
        .pill-stat.approved-count {{ color: #86efac; border-color: rgba(34, 197, 94, 0.4); }}
        .pill-stat.archived-count {{ color: #fde68a; border-color: rgba(245, 158, 11, 0.4); }}

        .batches-container {{
            max-width: 1500px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 24px;
        }}
        .batch-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            overflow: hidden;
            display: grid;
            grid-template-columns: 440px 1fr;
            box-shadow: 0 12px 28px rgba(0, 0, 0, 0.35);
            transition: border-color 0.2s ease;
        }}
        .batch-card.is-approved {{
            border-color: rgba(34, 197, 94, 0.55);
        }}
        .batch-card.is-archived {{
            border-color: rgba(148, 163, 184, 0.35);
            opacity: 0.92;
        }}
        @media (max-width: 1100px) {{
            .batch-card {{
                grid-template-columns: 1fr;
            }}
        }}
        @media (max-width: 768px) {{
            body {{
                padding: 10px 10px 70px;
            }}
            .top-bar {{
                padding: 12px 14px;
                margin-bottom: 10px;
                gap: 10px;
            }}
            .brand-block h1 {{
                font-size: 1.15rem;
            }}
            .brand-sub {{
                font-size: 0.75rem;
            }}
            .top-controls {{
                width: 100%;
                overflow-x: auto;
                flex-wrap: nowrap;
                padding-bottom: 2px;
                gap: 6px;
            }}
            .btn {{
                padding: 6px 10px;
                font-size: 0.74rem;
                white-space: nowrap;
                flex-shrink: 0;
            }}
            .review-bar {{
                padding: 10px 12px;
                margin-bottom: 14px;
                gap: 8px;
            }}
            .filter-tabs {{
                width: 100%;
                overflow-x: auto;
                flex-wrap: nowrap;
                gap: 6px;
            }}
            .tab-btn {{
                padding: 6px 11px;
                font-size: 0.76rem;
                white-space: nowrap;
                flex-shrink: 0;
            }}
            .card-visual {{
                padding: 10px;
                border-right: none;
                border-bottom: 1px solid var(--border);
            }}
            .card-content {{
                padding: 14px;
                gap: 12px;
            }}
            .batch-title {{
                font-size: 1.05rem;
            }}
        }}
        .card-visual {{
            background: #070a0f;
            border-right: 1px solid var(--border);
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}
        .hero-stage {{
            position: relative;
            width: 100%;
            aspect-ratio: 4 / 5;
            background: #040609;
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid #1e2636;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .hero-stage img, .hero-stage video {{
            width: 100%;
            height: 100%;
            object-fit: contain;
            display: block;
        }}
        .stage-top-bar {{
            position: absolute;
            top: 10px;
            left: 10px;
            right: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 4;
        }}
        .batch-badge {{
            background: rgba(11, 14, 20, 0.88);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: #fff;
            font-weight: 800;
            font-size: 0.76rem;
            padding: 4px 10px;
            border-radius: 999px;
            backdrop-filter: blur(6px);
        }}
        .stage-actions {{
            display: flex;
            gap: 6px;
        }}
        .stage-btn {{
            background: rgba(15, 23, 42, 0.9);
            border: 1px solid rgba(255, 255, 255, 0.22);
            color: #fff;
            font-weight: 700;
            font-size: 0.75rem;
            padding: 5px 10px;
            border-radius: 7px;
            cursor: pointer;
            backdrop-filter: blur(6px);
        }}
        .stage-btn.veto-main-btn {{
            background: rgba(220, 38, 38, 0.88);
            border-color: #f87171;
        }}
        .stage-btn.hero-main-btn {{
            background: rgba(217, 119, 6, 0.88);
            border-color: #fbbf24;
        }}
        .stage-bottom-bar {{
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            background: linear-gradient(to top, rgba(4, 6, 9, 0.95), transparent);
            padding: 22px 12px 9px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.76rem;
            color: #cbd5e1;
            pointer-events: none;
        }}
        .carousel-strip {{
            display: flex;
            gap: 8px;
            overflow-x: auto;
            padding: 4px 2px 6px;
        }}
        .thumb-wrap {{
            position: relative;
            width: 76px;
            height: 95px;
            flex-shrink: 0;
            border-radius: 8px;
            overflow: hidden;
            border: 2px solid #263044;
            background: #0c1017;
            cursor: pointer;
            transition: all 0.12s ease;
        }}
        .thumb-wrap.active {{
            border-color: var(--accent-blue);
            box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.35);
        }}
        .thumb-wrap.is-vetoed {{
            opacity: 0.32;
            filter: grayscale(1);
            border-color: #ef4444;
        }}
        .thumb-wrap img, .thumb-wrap video {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }}
        .thumb-veto-x {{
            position: absolute;
            top: 3px;
            right: 3px;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            border: none;
            background: rgba(220, 38, 38, 0.92);
            color: #fff;
            font-weight: 900;
            font-size: 0.75rem;
            line-height: 1;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 3;
        }}
        .thumb-star-btn {{
            position: absolute;
            top: 3px;
            left: 3px;
            height: 20px;
            padding: 0 5px;
            border-radius: 4px;
            border: none;
            background: rgba(15, 23, 42, 0.85);
            color: #fbbf24;
            font-size: 0.68rem;
            font-weight: 800;
            cursor: pointer;
            z-index: 3;
        }}
        .thumb-label {{
            position: absolute;
            bottom: 3px;
            left: 3px;
            right: 3px;
            background: rgba(11, 14, 20, 0.88);
            color: #e2e8f0;
            font-size: 0.62rem;
            font-weight: 700;
            text-align: center;
            padding: 2px 0;
            border-radius: 3px;
            pointer-events: none;
        }}
        .thumb-label.hero-lbl {{
            background: linear-gradient(90deg, #f59e0b, #ea580c);
            color: #fff;
        }}
        .card-content {{
            padding: 20px 24px;
            display: flex;
            flex-direction: column;
            gap: 14px;
        }}
        .card-header-top {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 12px;
            flex-wrap: wrap;
        }}
        .batch-title {{
            font-size: 1.25rem;
            font-weight: 800;
            color: #fff;
        }}
        .meta-tags {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 5px;
        }}
        .tag {{
            font-size: 0.73rem;
            font-weight: 600;
            padding: 3px 9px;
            border-radius: 6px;
            background: #1e293b;
            color: #cbd5e1;
        }}
        .tag-credit {{
            color: #fbbf24;
            background: rgba(245, 158, 11, 0.14);
        }}
        .tag-ig-posted {{
            background: rgba(225, 48, 108, 0.2);
            color: #f472b6;
            border: 1px solid rgba(225, 48, 108, 0.45);
        }}
        .tag-mw-posted {{
            background: rgba(0, 200, 83, 0.18);
            color: #4ade80;
            border: 1px solid rgba(0, 200, 83, 0.45);
        }}
        .approve-btn {{
            padding: 7px 13px;
            border-radius: 8px;
            border: 1px solid #334155;
            background: #1e293b;
            color: #cbd5e1;
            font-weight: 700;
            font-size: 0.78rem;
            cursor: pointer;
        }}
        .approve-btn.approved {{
            background: rgba(34, 197, 94, 0.2);
            border-color: #22c55e;
            color: #4ade80;
        }}
        /* Posted Today & Archive Action Bar */
        .post-log-bar {{
            background: rgba(13, 17, 24, 0.9);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 10px 14px;
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
        }}
        .post-log-left {{
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
            font-size: 0.8rem;
            font-weight: 700;
            color: var(--text-muted);
        }}
        .post-action-btn {{
            padding: 6px 11px;
            border-radius: 7px;
            border: 1px solid #2e3b52;
            background: #161f2e;
            color: #e2e8f0;
            font-weight: 700;
            font-size: 0.76rem;
            cursor: pointer;
            transition: all 0.12s ease;
        }}
        .post-action-btn:hover {{
            border-color: var(--accent-blue);
            transform: translateY(-1px);
        }}
        .post-action-btn.ig-active {{
            background: rgba(225, 48, 108, 0.25);
            border-color: #e1306c;
            color: #fbcfe8;
        }}
        .post-action-btn.mw-active {{
            background: rgba(0, 200, 83, 0.22);
            border-color: #00c853;
            color: #bbf7d0;
        }}
        .post-action-btn.both-archive-btn {{
            background: linear-gradient(135deg, #f59e0b, #ea580c);
            border-color: transparent;
            color: #fff;
        }}
        .post-action-btn.archive-toggle-btn {{
            background: #334155;
            color: #f8fafc;
        }}
        .post-action-btn.archive-toggle-btn.is-archived {{
            background: rgba(245, 158, 11, 0.22);
            border-color: #f59e0b;
            color: #fde68a;
        }}
        .date-input {{
            background: #0b0e14;
            border: 1px solid #263147;
            color: #cbd5e1;
            border-radius: 6px;
            padding: 4px 7px;
            font-size: 0.75rem;
            font-family: inherit;
        }}

        .copy-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 14px;
            flex: 1;
        }}
        @media (max-width: 1280px) {{
            .copy-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        .copy-panel {{
            background: var(--bg-panel);
            border: 1px solid var(--border);
            border-radius: 10px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        .panel-header {{
            padding: 10px 14px;
            background: rgba(255, 255, 255, 0.02);
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 8px;
            font-weight: 700;
            font-size: 0.82rem;
        }}
        .copy-action-btn {{
            padding: 6px 12px;
            border-radius: 7px;
            border: none;
            font-weight: 700;
            font-size: 0.78rem;
            cursor: pointer;
            color: #fff;
        }}
        .ig-copy-btn {{
            background: linear-gradient(135deg, #e1306c, #c13584);
        }}
        .mw-copy-btn {{
            background: linear-gradient(135deg, #00c853, #059669);
        }}
        .copy-textarea {{
            width: 100%;
            min-height: 135px;
            flex: 1;
            background: transparent;
            border: none;
            color: #e2e8f0;
            padding: 12px 14px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            font-size: 0.88rem;
            line-height: 1.5;
            resize: vertical;
            outline: none;
        }}
        .panel-footer {{
            padding: 6px 14px;
            border-top: 1px solid #1a2230;
            font-size: 0.72rem;
            color: var(--text-muted);
            display: flex;
            justify-content: space-between;
        }}
        .empty-state {{
            padding: 36px;
            text-align: center;
            color: var(--text-muted);
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>

    <header class="top-bar">
        <div class="brand-block">
            <h1><span class="brand-handle">@cosplaydad3d</span> Review &amp; Post Dashboard</h1>
            <p class="brand-sub">Click <strong>✕</strong> to veto pics • Click <strong>★</strong> for #1 Hero • Mark <strong>Posted Today (IG / MW / Both)</strong> to record date &amp; archive</p>
        </div>
        <div class="top-controls">
            <span class="pill-stat" id="cloudSyncPill" style="color:#38bdf8;border-color:rgba(56,189,248,0.4);">☁️ Cloud Ready</span>
            <button class="btn" id="toggleVetoedBtn" onclick="toggleShowVetoed()">👁️ Show Vetoed Pics (0)</button>
            <button class="btn" onclick="resetReviewState()">↺ Reset Unsaved Clicks</button>
            <button class="btn btn-primary" onclick="copyReviewForAntigravity(this)">📋 Copy Cleanup Command</button>
            <button class="btn btn-success" onclick="downloadReviewJson()">💾 Save JSON</button>
        </div>
    </header>

    <section class="review-bar">
        <div class="filter-tabs">
            <button class="tab-btn active" id="tab-ready" onclick="setFilterTab('ready')">📸 Active Queue (0)</button>
            <button class="tab-btn" id="tab-mw" onclick="setFilterTab('mw')">🟢 MakerWorld 3D Models (0)</button>
            <button class="tab-btn" id="tab-archived" onclick="setFilterTab('archived')">📦 Posted Archive (0)</button>
            <button class="tab-btn" id="tab-all" onclick="setFilterTab('all')">All Social Batches (0)</button>
        </div>
        <div class="review-stats">
            <span class="pill-stat veto-count" id="vetoCounterPill">0 Pics Vetoed</span>
            <span class="pill-stat approved-count" id="approvedCounterPill">0 Approved</span>
            <span class="pill-stat archived-count" id="archivedCounterPill">0 Archived</span>
        </div>
    </section>

    <main class="batches-container" id="batchesRoot"></main>

    <script>
        const INITIAL_BATCHES = {batches_payload};
        const MW_MODELS = {mw_models_payload};
        const STORAGE_KEY = "cosplaydad3d_review_v3";
        const FIRESTORE_URL = "{FIRESTORE_DOC_URL}";
        let showVetoed = false;
        let currentTab = "ready";
        let syncTimer = null;

        // If a previous DuoScribe Service Worker is registered on this origin, trigger an update so /cosplaydad is excluded
        if ("serviceWorker" in navigator) {{
            navigator.serviceWorker.getRegistrations().then(regs => {{
                for (const r of regs) r.update();
            }});
        }}

        function setCloudPill(text, color) {{
            const el = document.getElementById("cloudSyncPill");
            if (!el) return;
            el.textContent = text;
            el.style.color = color || "#38bdf8";
        }}

        async function pushStateToCloud() {{
            try {{
                setCloudPill("☁️ Syncing...", "#f59e0b");
                const exportObj = buildReviewExportObject();
                const body = {{
                    fields: {{
                        updated_at: {{ stringValue: new Date().toISOString() }},
                        payload_json: {{ stringValue: JSON.stringify(exportObj) }}
                    }}
                }};
                const resp = await fetch(FIRESTORE_URL, {{
                    method: "PATCH",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify(body)
                }});
                if (resp.ok) {{
                    setCloudPill("☁️ Cloud Synced", "#4ade80");
                }} else {{
                    setCloudPill("☁️ Local Saved", "#94a3b8");
                }}
            }} catch (e) {{
                setCloudPill("☁️ Local Saved", "#94a3b8");
            }}
        }}

        async function pullStateFromCloud() {{
            try {{
                const resp = await fetch(FIRESTORE_URL);
                if (!resp.ok) return;
                const doc = await resp.json();
                const rawJson = doc.fields && doc.fields.payload_json && doc.fields.payload_json.stringValue;
                if (!rawJson) return;
                const cloudObj = JSON.parse(rawJson);
                if (!cloudObj || !cloudObj.batches) return;

                const mapped = {{}};
                for (const [folderName, bRev] of Object.entries(cloudObj.batches)) {{
                    const allOrder = [...(bRev.keep_order || []), ...(bRev.vetoed || [])];
                    mapped[folderName] = {{
                        archived: bRev.archived,
                        ig_posted_date: bRev.ig_posted_date,
                        mw_posted_date: bRev.mw_posted_date,
                        posted_platforms: bRev.posted_platforms,
                        approval: bRev.approval,
                        ig_caption: bRev.ig_caption,
                        mw_text: bRev.mw_text,
                        vetoed: bRev.vetoed || [],
                        order: allOrder.length ? allOrder : undefined
                    }};
                }}
                localStorage.setItem(STORAGE_KEY, JSON.stringify(mapped));
                state = loadState();
                renderAll();
                setCloudPill("☁️ Cloud Synced", "#4ade80");
            }} catch (e) {{}}
        }}

        function getTodayStr() {{
            const d = new Date();
            const yyyy = d.getFullYear();
            const mm = String(d.getMonth() + 1).padStart(2, "0");
            const dd = String(d.getDate()).padStart(2, "0");
            return `${{yyyy}}-${{mm}}-${{dd}}`;
        }}

        function computePlatformsLabel(igDate, mwDate) {{
            if (igDate && mwDate) return "Both (Instagram + MakerWorld)";
            if (igDate) return "Instagram Only";
            if (mwDate) return "MakerWorld Only";
            return "Not Posted Yet";
        }}

        function loadState() {{
            let saved = {{}};
            try {{
                const raw = localStorage.getItem(STORAGE_KEY);
                if (raw) saved = JSON.parse(raw);
            }} catch (e) {{}}

            return INITIAL_BATCHES.map(b => {{
                const sb = saved[b.folder_name] || {{}};
                const vetoedSet = new Set(sb.vetoed || []);
                let orderedNames = sb.order || b.slides.map(s => s.name);

                const diskMap = new Map(b.slides.map(s => [s.name, s]));
                orderedNames = orderedNames.filter(n => diskMap.has(n));
                for (const s of b.slides) {{
                    if (!orderedNames.includes(s.name)) orderedNames.push(s.name);
                }}

                const slides = orderedNames.map(name => ({{
                    ...diskMap.get(name),
                    vetoed: vetoedSet.has(name)
                }}));

                const firstActiveIdx = slides.findIndex(s => !s.vetoed);
                const igDate = sb.ig_posted_date !== undefined ? sb.ig_posted_date : (b.ig_posted_date || "");
                const mwDate = sb.mw_posted_date !== undefined ? sb.mw_posted_date : (b.mw_posted_date || "");
                const isArchived = sb.archived !== undefined ? sb.archived : Boolean(b.archived);

                return {{
                    ...b,
                    archived: isArchived,
                    ig_posted_date: igDate,
                    mw_posted_date: mwDate,
                    posted_platforms: computePlatformsLabel(igDate, mwDate),
                    approval: sb.approval || b.approval || "Needs Review",
                    ig_caption: sb.ig_caption !== undefined ? sb.ig_caption : b.ig_caption,
                    mw_text: sb.mw_text !== undefined ? sb.mw_text : b.mw_text,
                    slides,
                    selectedIdx: firstActiveIdx >= 0 ? firstActiveIdx : 0
                }};
            }});
        }}

        let state = loadState();

        function saveState() {{
            const payload = {{}};
            for (const b of state) {{
                payload[b.folder_name] = {{
                    archived: b.archived,
                    ig_posted_date: b.ig_posted_date,
                    mw_posted_date: b.mw_posted_date,
                    posted_platforms: computePlatformsLabel(b.ig_posted_date, b.mw_posted_date),
                    approval: b.approval,
                    ig_caption: b.ig_caption,
                    mw_text: b.mw_text,
                    vetoed: b.slides.filter(s => s.vetoed).map(s => s.name),
                    order: b.slides.map(s => s.name)
                }};
            }}
            try {{
                localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
            }} catch (e) {{}}
            updateSummaryCounters();
            if (syncTimer) clearTimeout(syncTimer);
            syncTimer = setTimeout(() => pushStateToCloud(), 400);
        }}

        function buildReviewExportObject() {{
            const out = {{ generated_at: new Date().toISOString(), batches: {{}} }};
            for (const b of state) {{
                out.batches[b.folder_name] = {{
                    archived: b.archived,
                    ig_posted_date: b.ig_posted_date,
                    mw_posted_date: b.mw_posted_date,
                    posted_platforms: computePlatformsLabel(b.ig_posted_date, b.mw_posted_date),
                    approval: b.approval,
                    ig_caption: b.ig_caption,
                    mw_text: b.mw_text,
                    keep_order: b.slides.filter(s => !s.vetoed).map(s => s.name),
                    vetoed: b.slides.filter(s => s.vetoed).map(s => s.name)
                }};
            }}
            return out;
        }}

        function setFilterTab(tab) {{
            currentTab = tab;
            document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));
            const btn = document.getElementById(`tab-${{tab}}`);
            if (btn) btn.classList.add("active");
            renderAll();
        }}

        function updateSummaryCounters() {{
            let totalVetoed = 0;
            let totalApproved = 0;
            let totalArchived = 0;
            let totalReady = 0;

            for (const b of state) {{
                totalVetoed += b.slides.filter(s => s.vetoed).length;
                if (b.approval === "Approved") totalApproved++;
                if (b.archived) totalArchived++;
                else totalReady++;
            }}

            document.getElementById("vetoCounterPill").textContent = `${{totalVetoed}} Pic${{totalVetoed === 1 ? '' : 's'}} Vetoed`;
            document.getElementById("approvedCounterPill").textContent = `${{totalApproved}} Approved`;
            document.getElementById("archivedCounterPill").textContent = `${{totalArchived}} Archived`;
            document.getElementById("tab-ready").textContent = `📸 Active Queue (${{totalReady}})`;
            document.getElementById("tab-mw").textContent = `🟢 MakerWorld 3D Models (${{MW_MODELS.length}})`;
            document.getElementById("tab-archived").textContent = `📦 Posted Archive (${{totalArchived}})`;
            document.getElementById("tab-all").textContent = `All Social Batches (${{state.length}})`;
            document.getElementById("toggleVetoedBtn").textContent = showVetoed
                ? `🙈 Hide Vetoed Pics (${{totalVetoed}})`
                : `👁️ Show Vetoed Pics (${{totalVetoed}})`;
        }}

        function toggleShowVetoed() {{
            showVetoed = !showVetoed;
            renderAll();
        }}

        function resetReviewState() {{
            if (!confirm("Reset unsaved browser review clicks back to current disk state?")) return;
            localStorage.removeItem(STORAGE_KEY);
            fetch(FIRESTORE_URL, {{ method: "DELETE" }}).catch(() => {{}});
            state = loadState();
            renderAll();
        }}

        function selectSlide(batchIdx, slideIdx) {{
            state[batchIdx].selectedIdx = slideIdx;
            renderBatchCard(batchIdx);
        }}

        function toggleVetoSlide(batchIdx, slideIdx, ev) {{
            if (ev) ev.stopPropagation();
            const b = state[batchIdx];
            const target = b.slides[slideIdx];
            target.vetoed = !target.vetoed;

            if (target.vetoed && b.selectedIdx === slideIdx) {{
                const nextActive = b.slides.findIndex((s, idx) => !s.vetoed && idx >= slideIdx);
                const anyActive = b.slides.findIndex(s => !s.vetoed);
                b.selectedIdx = nextActive >= 0 ? nextActive : (anyActive >= 0 ? anyActive : 0);
            }}
            saveState();
            renderBatchCard(batchIdx);
        }}

        function promoteToHero(batchIdx, slideIdx, ev) {{
            if (ev) ev.stopPropagation();
            const b = state[batchIdx];
            const [picked] = b.slides.splice(slideIdx, 1);
            picked.vetoed = false;
            b.slides.unshift(picked);
            b.selectedIdx = 0;
            saveState();
            renderBatchCard(batchIdx);
        }}

        function moveSlide(batchIdx, slideIdx, dir, ev) {{
            if (ev) ev.stopPropagation();
            const b = state[batchIdx];
            const newIdx = slideIdx + dir;
            if (newIdx < 0 || newIdx >= b.slides.length) return;
            const temp = b.slides[slideIdx];
            b.slides[slideIdx] = b.slides[newIdx];
            b.slides[newIdx] = temp;
            b.selectedIdx = newIdx;
            saveState();
            renderBatchCard(batchIdx);
        }}

        function toggleApproveBatch(batchIdx) {{
            const b = state[batchIdx];
            b.approval = b.approval === "Approved" ? "Needs Review" : "Approved";
            saveState();
            renderBatchCard(batchIdx);
        }}

        /* Posting & Archive Controls */
        function markPostedPlatform(batchIdx, mode) {{
            const b = state[batchIdx];
            const today = getTodayStr();

            if (mode === "ig") {{
                b.ig_posted_date = b.ig_posted_date ? "" : today;
            }} else if (mode === "mw") {{
                b.mw_posted_date = b.mw_posted_date ? "" : today;
            }} else if (mode === "ig_archive") {{
                if (!b.ig_posted_date) b.ig_posted_date = today;
                b.archived = true;
                b.approval = "Approved";
            }} else if (mode === "mw_archive") {{
                if (!b.mw_posted_date) b.mw_posted_date = today;
                b.archived = true;
                b.approval = "Approved";
            }} else if (mode === "both_archive") {{
                if (!b.ig_posted_date) b.ig_posted_date = today;
                if (!b.mw_posted_date) b.mw_posted_date = today;
                b.archived = true;
                b.approval = "Approved";
            }} else if (mode === "toggle_archive") {{
                b.archived = !b.archived;
            }}

            b.posted_platforms = computePlatformsLabel(b.ig_posted_date, b.mw_posted_date);
            saveState();
            renderAll();
        }}

        function onDateChange(batchIdx, field, val) {{
            const b = state[batchIdx];
            b[field] = val;
            b.posted_platforms = computePlatformsLabel(b.ig_posted_date, b.mw_posted_date);
            saveState();
            renderBatchCard(batchIdx);
        }}

        function onCaptionInput(batchIdx, field, el) {{
            state[batchIdx][field] = el.value;
            const countEl = el.parentElement.querySelector(".word-count");
            if (countEl) {{
                const words = el.value.trim() ? el.value.trim().split(/\\s+/).length : 0;
                countEl.textContent = `${{words}} words`;
            }}
            saveState();
        }}

        async function copyTextarea(btn, batchIdx, field) {{
            const text = state[batchIdx][field];
            try {{
                await navigator.clipboard.writeText(text);
            }} catch (e) {{
                const ta = document.createElement("textarea");
                ta.value = text;
                document.body.appendChild(ta);
                ta.select();
                document.execCommand("copy");
                document.body.removeChild(ta);
            }}
            const orig = btn.textContent;
            btn.textContent = "✓ Copied!";
            setTimeout(() => btn.textContent = orig, 1600);
        }}

        async function copyReviewForAntigravity(btn) {{
            const obj = buildReviewExportObject();
            const cmdText = "clean up: " + JSON.stringify(obj);
            try {{
                await navigator.clipboard.writeText(cmdText);
            }} catch (e) {{}}
            const orig = btn.textContent;
            btn.textContent = "✓ Copied! Paste in Antigravity";
            setTimeout(() => btn.textContent = orig, 2500);
        }}

        function downloadReviewJson() {{
            const obj = buildReviewExportObject();
            const blob = new Blob([JSON.stringify(obj, null, 2)], {{ type: "application/json" }});
            const a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = "review_decisions.json";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }}

        async function downloadActiveSlides(batchIdx, btn) {{
            const b = state[batchIdx];
            const activeSlides = b.slides.filter(s => !s.vetoed);
            if (!activeSlides.length) return;
            const orig = btn.textContent;
            btn.textContent = "⏳ Downloading...";
            for (let i = 0; i < activeSlides.length; i++) {{
                const s = activeSlides[i];
                const ext = s.rel.substring(s.rel.lastIndexOf("."));
                const num = String(i + 1).padStart(2, "0");
                const dlName = `Batch_${{b.batch_num}}_${{num}}${{i === 0 ? '_Hero' : '_Slide'}}${{ext}}`;
                const a = document.createElement("a");
                a.href = s.rel;
                a.download = dlName;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                await new Promise(r => setTimeout(r, 260));
            }}
            btn.textContent = "✓ Downloaded!";
            setTimeout(() => btn.textContent = orig, 1800);
        }}

        function escapeHtml(str) {{
            return String(str || "")
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;");
        }}

        function buildCardInnerHtml(b, batchIdx) {{
            const activeSlides = b.slides.filter(s => !s.vetoed);
            const curSlide = b.slides[b.selectedIdx] || activeSlides[0] || null;

            let stageMediaHtml = `<div class="empty-state">All pictures in this batch were vetoed. Click "Show Vetoed Pics" above to restore one.</div>`;
            let activeRank = 0;

            if (curSlide && (!curSlide.vetoed || showVetoed)) {{
                activeRank = activeSlides.indexOf(curSlide) + 1;
                if (curSlide.is_video) {{
                    stageMediaHtml = `<video src="${{escapeHtml(curSlide.rel)}}" poster="${{escapeHtml(curSlide.poster_rel)}}" controls playsinline preload="metadata"></video>`;
                }} else {{
                    stageMediaHtml = `<img src="${{escapeHtml(curSlide.rel)}}" alt="${{escapeHtml(curSlide.name)}}">`;
                }}
            }} else if (activeSlides.length > 0) {{
                const fallback = activeSlides[0];
                b.selectedIdx = b.slides.indexOf(fallback);
                activeRank = 1;
                stageMediaHtml = fallback.is_video
                    ? `<video src="${{escapeHtml(fallback.rel)}}" poster="${{escapeHtml(fallback.poster_rel)}}" controls playsinline preload="metadata"></video>`
                    : `<img src="${{escapeHtml(fallback.rel)}}" alt="${{escapeHtml(fallback.name)}}">`;
            }}

            const selectedSlide = b.slides[b.selectedIdx];
            const thumbsHtml = b.slides.map((s, sIdx) => {{
                if (s.vetoed && !showVetoed) return "";
                const activePos = activeSlides.indexOf(s) + 1;
                const isHero = activePos === 1 && !s.vetoed;
                const lbl = s.vetoed ? "VETOED" : (isHero ? "★ #1 HERO" : `#${{activePos}}${{s.is_video ? ' ▶' : ''}}`);
                const mediaThumb = s.is_video
                    ? (s.poster_rel ? `<img src="${{escapeHtml(s.poster_rel)}}" alt="${{escapeHtml(s.name)}}">` : `<video src="${{escapeHtml(s.rel)}}" muted preload="metadata"></video>`)
                    : `<img src="${{escapeHtml(s.rel)}}" alt="${{escapeHtml(s.name)}}" loading="lazy">`;

                return `
                <div class="thumb-wrap ${{b.selectedIdx === sIdx ? 'active' : ''}} ${{s.vetoed ? 'is-vetoed' : ''}}"
                     onclick="selectSlide(${{batchIdx}}, ${{sIdx}})"
                     title="${{escapeHtml(s.name)}}">
                    ${{!isHero && !s.vetoed ? `<button class="thumb-star-btn" onclick="promoteToHero(${{batchIdx}}, ${{sIdx}}, event)" title="Make #1 Hero">★</button>` : ''}}
                    <button class="thumb-veto-x" onclick="toggleVetoSlide(${{batchIdx}}, ${{sIdx}}, event)" title="${{s.vetoed ? 'Restore Picture' : 'Veto / Remove Picture'}}">${{s.vetoed ? '↺' : '✕'}}</button>
                    ${{mediaThumb}}
                    <span class="thumb-label ${{isHero ? 'hero-lbl' : ''}}">${{lbl}}</span>
                </div>`;
            }}).join("");

            const igWords = b.ig_caption.trim() ? b.ig_caption.trim().split(/\\s+/).length : 0;
            const mwWords = b.mw_text.trim() ? b.mw_text.trim().split(/\\s+/).length : 0;
            const isApproved = b.approval === "Approved";

            return `
                <div class="card-visual">
                    <div class="hero-stage">
                        ${{stageMediaHtml}}
                        <div class="stage-top-bar">
                            <span class="batch-badge">BATCH #${{escapeHtml(b.batch_num)}} • ${{activeSlides.length}} Active</span>
                            ${{selectedSlide ? `
                            <div class="stage-actions">
                                <button class="stage-btn" onclick="moveSlide(${{batchIdx}}, ${{b.selectedIdx}}, -1, event)" title="Move Left">◀</button>
                                <button class="stage-btn" onclick="moveSlide(${{batchIdx}}, ${{b.selectedIdx}}, 1, event)" title="Move Right">▶</button>
                                <button class="stage-btn hero-main-btn" onclick="promoteToHero(${{batchIdx}}, ${{b.selectedIdx}}, event)" title="Make Slide #1 Hero">★ Make #1</button>
                                <button class="stage-btn veto-main-btn" onclick="toggleVetoSlide(${{batchIdx}}, ${{b.selectedIdx}}, event)">${{selectedSlide.vetoed ? '↺ Restore Pic' : '✕ Veto Pic'}}</button>
                            </div>` : ''}}
                        </div>
                        <div class="stage-bottom-bar">
                            <span>${{selectedSlide ? `${{selectedSlide.vetoed ? '[VETOED] ' : `Slide #${{activeRank}} — `}}${{escapeHtml(selectedSlide.name)}}` : 'No active slides'}}</span>
                            <span>4:5 IG Ready</span>
                        </div>
                    </div>
                    <div class="carousel-strip">
                        ${{thumbsHtml}}
                    </div>
                </div>

                <div class="card-content">
                    <div class="card-header-top">
                        <div>
                            <h2 class="batch-title">${{escapeHtml(b.title)}}</h2>
                            <div class="meta-tags">
                                <span class="tag">${{escapeHtml(b.category)}}</span>
                                <span class="tag tag-credit">Credit: ${{escapeHtml(b.designer_credit)}}</span>
                                ${{b.ig_posted_date ? `<span class="tag tag-ig-posted">📸 IG Posted: ${{escapeHtml(b.ig_posted_date)}}</span>` : ''}}
                                ${{b.mw_posted_date ? `<span class="tag tag-mw-posted">🟢 MW Posted: ${{escapeHtml(b.mw_posted_date)}}</span>` : ''}}
                                ${{b.archived ? `<span class="tag" style="background:#334155;color:#fde68a;">📦 Archived (${{escapeHtml(b.posted_platforms)}})</span>` : ''}}
                            </div>
                        </div>
                        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
                            <a href="cosplaydad://open/${{b.archived ? '03_Posted_Archive' : '02_Ready_To_Post'}}/${{encodeURIComponent(b.folder_name)}}/Instagram_Carousel"
                               class="btn"
                               style="text-decoration:none;background:rgba(56,189,248,0.14);border-color:#38bdf8;color:#e0f2fe;"
                               title="Opens this Batch's Instagram_Carousel folder directly in Windows File Explorer so you can drag &amp; drop photos into Instagram!">
                                📂 Open IG Folder
                            </a>
                            <button class="btn"
                                    onclick="downloadActiveSlides(${{batchIdx}}, this)"
                                    title="Download all active (non-vetoed) slides in order">
                                ⬇️ Download Slides (${{activeSlides.length}})
                            </button>
                            <button class="approve-btn ${{isApproved ? 'approved' : ''}}" onclick="toggleApproveBatch(${{batchIdx}})">
                                ${{isApproved ? '✓ Approved & Ready' : '○ Approve Batch'}}
                            </button>
                        </div>
                    </div>

                    <!-- Posted Today & Archive Control Bar -->
                    <div class="post-log-bar">
                        <div class="post-log-left">
                            <span>Mark Posted Today:</span>
                            <button class="post-action-btn ${{b.ig_posted_date ? 'ig-active' : ''}}" onclick="markPostedPlatform(${{batchIdx}}, 'ig_archive')" title="Stamp today's date for Instagram and move to Archive">
                                📸 IG Only &amp; Archive
                            </button>
                            <button class="post-action-btn ${{b.mw_posted_date ? 'mw-active' : ''}}" onclick="markPostedPlatform(${{batchIdx}}, 'mw_archive')" title="Stamp today's date for MakerWorld and move to Archive">
                                🟢 MW Only &amp; Archive
                            </button>
                            <button class="post-action-btn both-archive-btn" onclick="markPostedPlatform(${{batchIdx}}, 'both_archive')" title="Stamp today's date for BOTH Instagram + MakerWorld and move to Archive">
                                🚀 Posted Both Today &amp; Archive
                            </button>
                        </div>
                        <div class="post-log-left">
                            <label>IG Date: <input type="date" class="date-input" value="${{escapeHtml(b.ig_posted_date)}}" onchange="onDateChange(${{batchIdx}}, 'ig_posted_date', this.value)"></label>
                            <label>MW Date: <input type="date" class="date-input" value="${{escapeHtml(b.mw_posted_date)}}" onchange="onDateChange(${{batchIdx}}, 'mw_posted_date', this.value)"></label>
                            <button class="post-action-btn archive-toggle-btn ${{b.archived ? 'is-archived' : ''}}" onclick="markPostedPlatform(${{batchIdx}}, 'toggle_archive')">
                                ${{b.archived ? '↺ Unarchive to Queue' : '📦 Archive'}}
                            </button>
                        </div>
                    </div>

                    <div class="copy-grid">
                        <div class="copy-panel">
                            <div class="panel-header">
                                <span>Instagram Caption (Short &amp; Punchy)</span>
                                <div style="display:flex;gap:6px;">
                                    <button class="post-action-btn ${{b.ig_posted_date ? 'ig-active' : ''}}" onclick="markPostedPlatform(${{batchIdx}}, 'ig')" title="Toggle IG Posted Today without archiving yet">
                                        ${{b.ig_posted_date ? `✓ IG: ${{b.ig_posted_date}}` : '📸 Mark IG Today'}}
                                    </button>
                                    <button class="copy-action-btn ig-copy-btn" onclick="copyTextarea(this, ${{batchIdx}}, 'ig_caption')">Copy Instagram</button>
                                </div>
                            </div>
                            <textarea class="copy-textarea" oninput="onCaptionInput(${{batchIdx}}, 'ig_caption', this)">${{escapeHtml(b.ig_caption)}}</textarea>
                            <div class="panel-footer">
                                <span>Editable — auto-saves in browser</span>
                                <span class="word-count">${{igWords}} words</span>
                            </div>
                        </div>

                        <div class="copy-panel">
                            <div class="panel-header">
                                <span>MakerWorld Build Note</span>
                                <div style="display:flex;gap:6px;">
                                    <button class="post-action-btn ${{b.mw_posted_date ? 'mw-active' : ''}}" onclick="markPostedPlatform(${{batchIdx}}, 'mw')" title="Toggle MW Posted Today without archiving yet">
                                        ${{b.mw_posted_date ? `✓ MW: ${{b.mw_posted_date}}` : '🟢 Mark MW Today'}}
                                    </button>
                                    <button class="copy-action-btn mw-copy-btn" onclick="copyTextarea(this, ${{batchIdx}}, 'mw_text')">Copy MakerWorld</button>
                                </div>
                            </div>
                            <textarea class="copy-textarea" oninput="onCaptionInput(${{batchIdx}}, 'mw_text', this)">${{escapeHtml(b.mw_text)}}</textarea>
                            <div class="panel-footer">
                                <span>Editable — auto-saves in browser</span>
                                <span class="word-count">${{mwWords}} words</span>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }}

        function renderBatchCard(batchIdx) {{
            const b = state[batchIdx];
            const el = document.getElementById(`batch-card-${{batchIdx}}`);
            if (!el) return;
            el.className = `batch-card ${{b.approval === 'Approved' ? 'is-approved' : ''}} ${{b.archived ? 'is-archived' : ''}}`;
            el.innerHTML = buildCardInnerHtml(b, batchIdx);
            updateSummaryCounters();
        }}

        function buildMwModelCardHtml(m, mIdx) {{
            const sc = m.stage_counts || {{}};
            const stageDefs = [
                ["01_4Pose_Turnarounds", "01 • 4-Pose Sheets", false],
                ["02_Paint_And_Finish_Concepts", "02 • Paint & Finish Concepts", false],
                ["03_Tripo_Raw_90MB", "03 • Tripo Raw (~90MB)", false],
                ["04_Blender_Working", "04 • Blender (.blend)", false],
                ["05_Final_STL_Under500k", "05 • Final STL (<500k) ✅", true],
                ["06_Bambu_3MF_Profile", "06 • Bambu .3MF ✅", true],
                ["07_Real_Print_Photos", "07 • Real Print Pics ✅", true],
            ];

            const stagesHtml = stageDefs.map(([folderKey, label, isUpload]) => {{
                const cnt = sc[folderKey] || 0;
                const hasFiles = cnt > 0;
                const bg = hasFiles
                    ? (isUpload ? "rgba(0, 200, 83, 0.18)" : "rgba(56, 189, 248, 0.16)")
                    : "rgba(15, 23, 42, 0.7)";
                const border = hasFiles
                    ? (isUpload ? "#22c55e" : "#38bdf8")
                    : "#263147";
                const color = hasFiles ? "#fff" : "#64748b";
                return `<div style="background:${{bg}};border:1px solid ${{border}};color:${{color}};padding:7px 11px;border-radius:8px;font-size:0.76rem;font-weight:700;display:flex;justify-content:space-between;gap:10px;">
                    <span>${{label}}</span>
                    <span>${{cnt}} file${{cnt === 1 ? '' : 's'}}</span>
                </div>`;
            }}).join("");

            const firstMedia = (m.media && m.media[0]) || null;
            let stagePreview = `<div class="empty-state">Drop photos or concept renders into 02_Paint_And_Finish_Concepts or 07_Real_Print_Photos</div>`;
            if (firstMedia) {{
                stagePreview = firstMedia.is_video
                    ? `<video id="mw-main-${{mIdx}}" src="${{escapeHtml(firstMedia.rel)}}" controls playsinline preload="metadata"></video>`
                    : `<img id="mw-main-${{mIdx}}" src="${{escapeHtml(firstMedia.rel)}}" alt="${{escapeHtml(firstMedia.name)}}">`;
            }}

            const thumbsHtml = (m.media || []).map((med, i) => `
                <div class="thumb-wrap ${{i === 0 ? 'active' : ''}}"
                     onclick="selectMwMedia(${{mIdx}}, '${{escapeHtml(med.rel)}}', ${{med.is_video}}, this)"
                     title="${{escapeHtml(med.stage_badge)}}: ${{escapeHtml(med.name)}}">
                    ${{med.is_video
                        ? `<video src="${{escapeHtml(med.rel)}}" muted preload="metadata"></video>`
                        : `<img src="${{escapeHtml(med.rel)}}" alt="${{escapeHtml(med.name)}}" loading="lazy">`}}
                    <span class="thumb-label">${{escapeHtml(med.stage_badge.split(' ')[0])}} #${{i + 1}}</span>
                </div>
            `).join("");

            return `
            <article class="batch-card">
                <div class="card-visual">
                    <div class="hero-stage" id="mw-stage-${{mIdx}}">
                        ${{stagePreview}}
                        <div class="stage-top-bar">
                            <span class="batch-badge">🟢 3D MODEL PROJECT</span>
                            <span class="batch-badge">${{m.ready_to_publish ? '✅ Ready for MakerWorld' : '🔧 Pipeline In Progress'}}</span>
                        </div>
                    </div>
                    <div class="carousel-strip">
                        ${{thumbsHtml}}
                    </div>
                </div>
                <div class="card-content">
                    <div class="card-header-top">
                        <div>
                            <h2 class="batch-title">${{escapeHtml(m.title)}}</h2>
                            <div class="meta-tags">
                                <span class="tag">${{escapeHtml(m.category)}}</span>
                                <span class="tag">04_MakerWorld_Models/${{escapeHtml(m.folder_name)}}</span>
                            </div>
                        </div>
                        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
                            <a href="cosplaydad://open/04_MakerWorld_Models/${{encodeURIComponent(m.folder_name)}}"
                               class="btn"
                               style="text-decoration:none;background:rgba(0,200,83,0.14);border-color:#22c55e;color:#dcfce7;"
                               title="Opens this MakerWorld Model folder directly in Windows File Explorer">
                                📂 Open Model Folder
                            </a>
                            <a href="cosplaydad://open/04_MakerWorld_Models/${{encodeURIComponent(m.folder_name)}}/05_Final_STL_Under500k"
                               class="btn"
                               style="text-decoration:none;"
                               title="Opens 05_Final_STL_Under500k directly in Windows File Explorer">
                                📂 Open Final STL
                            </a>
                        </div>
                    </div>

                    <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(210px, 1fr));gap:8px;">
                        ${{stagesHtml}}
                    </div>

                    <div class="copy-panel" style="flex:1;">
                        <div class="panel-header">
                            <span>MakerWorld Listing Description (MODEL_LISTING.md)</span>
                            <button class="copy-action-btn mw-copy-btn" onclick="navigator.clipboard.writeText(document.getElementById('mw-desc-${{mIdx}}').value);this.textContent='✓ Copied!';setTimeout(()=>this.textContent='Copy MakerWorld Description',1600)">Copy MakerWorld Description</button>
                        </div>
                        <textarea class="copy-textarea" id="mw-desc-${{mIdx}}">${{escapeHtml(m.description)}}</textarea>
                    </div>
                </div>
            </article>`;
        }}

        function selectMwMedia(mIdx, rel, isVid, thumbEl) {{
            const stage = document.getElementById(`mw-stage-${{mIdx}}`);
            const oldMedia = document.getElementById(`mw-main-${{mIdx}}`);
            if (oldMedia) oldMedia.remove();
            const wrapper = document.createElement("div");
            wrapper.innerHTML = isVid
                ? `<video id="mw-main-${{mIdx}}" src="${{rel}}" controls playsinline autoplay style="width:100%;height:100%;object-fit:contain;"></video>`
                : `<img id="mw-main-${{mIdx}}" src="${{rel}}" style="width:100%;height:100%;object-fit:contain;">`;
            stage.prepend(wrapper.firstChild);
            thumbEl.parentElement.querySelectorAll(".thumb-wrap").forEach(el => el.classList.remove("active"));
            thumbEl.classList.add("active");
        }}

        function renderAll() {{
            const root = document.getElementById("batchesRoot");
            if (currentTab === "mw") {{
                root.innerHTML = MW_MODELS.map((m, idx) => buildMwModelCardHtml(m, idx)).join("");
                updateSummaryCounters();
                return;
            }}

            const visible = state
                .map((b, idx) => ({{ b, idx }}))
                .filter(item => {{
                    if (currentTab === "ready") return !item.b.archived;
                    if (currentTab === "archived") return item.b.archived;
                    return true;
                }});

            if (visible.length === 0) {{
                root.innerHTML = `<div class="empty-state" style="background:var(--bg-card);border:1px solid var(--border);border-radius:14px;">No batches in this view right now. Switch tabs above!</div>`;
            }} else {{
                root.innerHTML = visible.map(({{ b, idx }}) => `
                    <article class="batch-card ${{b.approval === 'Approved' ? 'is-approved' : ''}} ${{b.archived ? 'is-archived' : ''}}" id="batch-card-${{idx}}">
                        ${{buildCardInnerHtml(b, idx)}}
                    </article>
                `).join("");
            }}
            updateSummaryCounters();
        }}

        renderAll();
        pullStateFromCloud();
    </script>
</body>
</html>
"""
    DASHBOARD_PATH.write_text(dashboard_html, encoding="utf-8")
    print(f"Updated {TRACKER_PATH} and {DASHBOARD_PATH}")


def apply_review_decisions(json_source: Optional[str] = None) -> None:
    """
    Apply human review decisions (vetoed slides, new #1 Hero/slide order, edited captions,
    approval status, posted dates/platforms, and archived status) to the Batch folders on disk.
    """
    ensure_directories()
    data = None
    if json_source:
        raw = json_source.strip()
        if raw.lower().startswith("clean up:"):
            raw = raw.split(":", 1)[1].strip()
        if raw.startswith("{"):
            data = json.loads(raw)
        elif Path(raw).exists():
            data = json.loads(Path(raw).read_text(encoding="utf-8"))

    if data is None:
        # 1. Try pulling live review state from Firestore (saved from iPhone/web dashboard!)
        cloud_data = fetch_cloud_review_state()
        if cloud_data and cloud_data.get("batches"):
            data = cloud_data
            print("Loaded live review decisions from Firebase Cloud Sync (cosplaydad_sync/review_state)!")
        else:
            candidates = [
                REVIEW_JSON_PATH,
                Path.home() / "Downloads" / "review_decisions.json",
            ]
            found = next((p for p in candidates if p.exists()), None)
            if not found:
                raise FileNotFoundError(
                    "No cloud review state in Firestore and no review_decisions.json found locally."
                )
            data = json.loads(found.read_text(encoding="utf-8"))
            print(f"Loaded review decisions from {found}")

    batches_map = data.get("batches", {})
    for folder_name, b_rev in batches_map.items():
        batch_dir = READY_DIR / folder_name
        in_archive = False
        if not batch_dir.exists():
            batch_dir = ARCHIVE_DIR / folder_name
            in_archive = True
        if not batch_dir.exists():
            continue

        ig_dir = batch_dir / "Instagram_Carousel"
        post_copy_path = batch_dir / "POST_COPY.md"
        meta = parse_post_copy(post_copy_path)

        for field in (
            "approval",
            "ig_caption",
            "mw_text",
            "ig_posted_date",
            "mw_posted_date",
            "posted_platforms",
        ):
            if field in b_rev:
                meta[field] = b_rev[field]

        # 1. Move vetoed files to _Vetoed_Archive/<folder_name>/
        vetoed_list = b_rev.get("vetoed", [])
        if vetoed_list and ig_dir.exists():
            veto_batch_dir = VETOED_DIR / folder_name
            veto_batch_dir.mkdir(parents=True, exist_ok=True)
            for v_name in vetoed_list:
                v_path = ig_dir / v_name
                if v_path.exists():
                    shutil.move(str(v_path), str(veto_batch_dir / v_name))
                    poster = v_path.with_suffix(".poster.jpg")
                    if poster.exists():
                        shutil.move(str(poster), str(veto_batch_dir / poster.name))
                    print(f"[{folder_name}] Vetoed & removed: {v_name}")

        # 2. Reorder & renumber surviving files in Instagram_Carousel/
        keep_order = b_rev.get("keep_order", [])
        if ig_dir.exists():
            existing_files = {
                p.name: p
                for p in ig_dir.iterdir()
                if p.is_file()
                and p.suffix.lower() in (IMAGE_EXTS | VIDEO_EXTS)
                and not p.name.endswith(".poster.jpg")
            }
            ordered_paths = [
                existing_files[n] for n in keep_order if n in existing_files
            ]
            for name, p in sorted(existing_files.items()):
                if p not in ordered_paths:
                    ordered_paths.append(p)

            staged = []
            for idx, p in enumerate(ordered_paths, start=1):
                tmp_p = ig_dir / f"__tmp_{idx:02d}{p.suffix.lower()}"
                shutil.move(str(p), str(tmp_p))
                poster = p.with_suffix(".poster.jpg")
                tmp_poster = None
                if poster.exists():
                    tmp_poster = ig_dir / f"__tmp_{idx:02d}.poster.jpg"
                    shutil.move(str(poster), str(tmp_poster))
                staged.append((idx, tmp_p, tmp_poster))

            final_slides = []
            for idx, tmp_p, tmp_poster in staged:
                stem = "01_Hero" if idx == 1 else f"{idx:02d}_Slide"
                final_p = ig_dir / f"{stem}{tmp_p.suffix.lower()}"
                shutil.move(str(tmp_p), str(final_p))
                if tmp_poster and tmp_poster.exists():
                    shutil.move(str(tmp_poster), str(final_p.with_suffix(".poster.jpg")))
                final_slides.append(final_p)

            write_updated_post_copy(post_copy_path, meta, final_slides)

        # 3. Move between 02_Ready_To_Post and 03_Posted_Archive if archived flag changed
        want_archived = Boolean = bool(b_rev.get("archived", in_archive))
        if want_archived and not in_archive:
            dst = ARCHIVE_DIR / folder_name
            if dst.exists():
                shutil.rmtree(dst)
            shutil.move(str(batch_dir), str(dst))
            print(f"[{folder_name}] Moved to 03_Posted_Archive/ ({meta.get('posted_platforms')})")
        elif not want_archived and in_archive:
            dst = READY_DIR / folder_name
            if dst.exists():
                shutil.rmtree(dst)
            shutil.move(str(batch_dir), str(dst))
            print(f"[{folder_name}] Restored to 02_Ready_To_Post/")

    clear_cloud_review_state()
    build_tracker_and_dashboard()
    publish_dashboard_to_firebase(deploy=True)
    print("Applied human review & archive decisions, rebuilt dashboard, and deployed to Firebase!")


def publish_dashboard_to_firebase(deploy: bool = True) -> str:
    """Stage and deploy the dashboard + web-optimized media to https://myairotica.web.app/cosplaydad/."""
    ensure_directories()
    build_tracker_and_dashboard()
    ready_batches = collect_batches(READY_DIR, "Ready to Post")
    posted_batches = collect_batches(ARCHIVE_DIR, "Posted")
    mw_models = collect_mw_models()
    return stage_and_deploy_firebase(ready_batches, posted_batches, mw_models, deploy=deploy)


def mark_batch_posted(
    batch_id: str,
    platforms: str = "both",
    date_str: Optional[str] = None,
) -> None:
    """
    Move Batch_XX_* from 02_Ready_To_Post to 03_Posted_Archive, record posted date
    for Instagram Only ('ig'), MakerWorld Only ('mw'), or Both ('both'), and rebuild dashboard.
    """
    ensure_directories()
    num = batch_id.strip().zfill(2)
    matches = list(READY_DIR.glob(f"Batch_{num}_*")) + list(
        ARCHIVE_DIR.glob(f"Batch_{num}_*")
    )
    if not matches:
        raise FileNotFoundError(f"No Batch_{num}_* found in Ready or Archive")

    today = date_str or datetime.date.today().strftime("%Y-%m-%d")
    plat_norm = platforms.lower().strip()

    for src in matches:
        post_copy_path = src / "POST_COPY.md"
        ig_dir = src / "Instagram_Carousel"
        meta = parse_post_copy(post_copy_path)
        meta["approval"] = "Approved"

        if plat_norm in ("ig", "instagram"):
            meta["ig_posted_date"] = today
        elif plat_norm in ("mw", "makerworld"):
            meta["mw_posted_date"] = today
        else:
            meta["ig_posted_date"] = today
            meta["mw_posted_date"] = today

        if meta["ig_posted_date"] and meta["mw_posted_date"]:
            meta["posted_platforms"] = "Both (Instagram + MakerWorld)"
        elif meta["ig_posted_date"]:
            meta["posted_platforms"] = "Instagram Only"
        elif meta["mw_posted_date"]:
            meta["posted_platforms"] = "MakerWorld Only"

        ig_slides = sorted(
            [
                p
                for p in ig_dir.iterdir()
                if p.is_file()
                and p.suffix.lower() in (IMAGE_EXTS | VIDEO_EXTS)
                and not p.name.endswith(".poster.jpg")
            ]
            if ig_dir.exists()
            else []
        )
        write_updated_post_copy(post_copy_path, meta, ig_slides)

        if src.parent == READY_DIR:
            dst = ARCHIVE_DIR / src.name
            if dst.exists():
                shutil.rmtree(dst)
            shutil.move(str(src), str(dst))
            print(
                f"Moved {src.name} -> 03_Posted_Archive/ [{meta['posted_platforms']} on {today}]"
            )
        else:
            print(f"Updated archive record for {src.name}: [{meta['posted_platforms']} on {today}]")

    build_tracker_and_dashboard()


def convert_inbox_media() -> None:
    """
    Scan 01_Inbox_Drop (and sweep any recent IMG_* drops from !cosplaydad3d root only):
    - Convert any .HEIC files to .jpg and IMMEDIATELY delete the .HEIC file.
    - Extract 2x2 keyframe sheets for any video files (.mp4, .mov, .m4v) so Antigravity can inspect them.
    """
    ensure_directories()
    for parent_dir in [DRIVE_ROOT]:
        if parent_dir.exists():
            for p in sorted(parent_dir.iterdir()):
                if (
                    p.is_file()
                    and p.name.upper().startswith("IMG_")
                    and p.suffix.lower() in (HEIC_EXTS | IMAGE_EXTS | VIDEO_EXTS)
                ):
                    dst = INBOX_DIR / p.name
                    shutil.move(str(p), str(dst))
                    print(f"Swept {p.name} from {parent_dir} -> 01_Inbox_Drop/")

    deleted_heics = purge_any_heic_files(INBOX_DIR)
    auto_organize_all_mw_projects()

    # Inspect any .stl files in 01_Inbox_Drop and print their triangle counts immediately
    for stl_p in sorted(INBOX_DIR.glob("*.stl")):
        meta = inspect_stl_file(stl_p)
        print(
            f"[STL Inspector] {stl_p.name}: {meta['triangles']:,} triangles ({meta['size_mb']} MB) "
            f"-> Target: {meta['target_subfolder']}/"
        )

    videos = [
        p for p in sorted(INBOX_DIR.iterdir()) if p.is_file() and p.suffix.lower() in VIDEO_EXTS
    ]
    for v in videos:
        sheet = INBOX_DIR / f"_video_preview_{v.stem}.jpg"
        extract_video_Sheet_for_inspection(v, sheet)
        print(f"Created video inspection sheet for {v.name} -> {sheet.name}")
    if deleted_heics == 0 and not videos:
        print("Inbox checked: no .HEIC or new video previews needed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="@cosplaydad3d CMS CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("build-dashboard", help="Rebuild TRACKER.md and CosplayDad_Dashboard.html")
    sub.add_parser("publish-web", help="Stage and deploy dashboard + media to https://myairotica.web.app/cosplaydad/")
    sub.add_parser("convert-inbox", help="Convert .HEIC to .jpg (deleting .HEIC) and preview videos in 01_Inbox_Drop")

    rev_p = sub.add_parser("apply-review", help="Apply human review vetoes/reorders/edits/archives to disk")
    rev_p.add_argument("--source", default=None, help="Path to review_decisions.json or inline JSON string")

    vid_p = sub.add_parser("format-video", help="Format a video for Instagram (4x5 Carousel or 9x16 Reel)")
    vid_p.add_argument("--src", required=True, help="Source video path")
    vid_p.add_argument("--dst", required=True, help="Destination .mp4 path")
    vid_p.add_argument("--aspect", default="4x5", choices=["4x5", "9x16"], help="Target aspect ratio")

    post_p = sub.add_parser("mark-posted", help="Move a Batch from Ready to Posted Archive with platform & date")
    post_p.add_argument("--batch", required=True, help="Batch number, e.g. 01 or 08")
    post_p.add_argument(
        "--platforms",
        default="both",
        choices=["ig", "mw", "both", "instagram", "makerworld"],
        help="Which platform(s) were posted: ig, mw, or both",
    )
    post_p.add_argument("--date", default=None, help="Posted date YYYY-MM-DD (defaults to today)")

    args = parser.parse_args()
    if args.cmd == "build-dashboard":
        ensure_directories()
        build_tracker_and_dashboard()
    elif args.cmd == "publish-web":
        publish_dashboard_to_firebase(deploy=True)
    elif args.cmd == "convert-inbox":
        convert_inbox_media()
    elif args.cmd == "apply-review":
        apply_review_decisions(args.source)
    elif args.cmd == "format-video":
        format_video_for_instagram(Path(args.src), Path(args.dst), aspect=args.aspect)
    elif args.cmd == "mark-posted":
        mark_batch_posted(args.batch, platforms=args.platforms, date_str=args.date)


if __name__ == "__main__":
    main()

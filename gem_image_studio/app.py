# app.py - CosplayDad3D Glass Studio: Local Image Manager, JPG Converter & Tripo 3D Hub
import os
import sys
import time
import json
import uuid
import shutil
import threading
import subprocess
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, abort
from PIL import Image

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

import tripo_client

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_FOLDER = os.path.join(BASE_DIR, "filigree staff", "05_Elongated_LED_Tubes")
OUTPUT_STL_DIR = os.path.join(BASE_DIR, "output_stl")
STAGING_DIR = os.path.join(BASE_DIR, "Tripo_Web_Staging")
JOBS_FILE = os.path.join(BASE_DIR, "tripo_jobs.json")
DOWNLOADS_DIR = os.path.expanduser("~/Downloads")

os.makedirs(OUTPUT_STL_DIR, exist_ok=True)
os.makedirs(STAGING_DIR, exist_ok=True)

app = Flask(__name__)

# Supported image extensions
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".jfif", ".webp", ".heic", ".heif", ".bmp", ".tiff"}
CONVERTIBLE_EXTS = {".png", ".jfif", ".webp", ".heic", ".heif", ".bmp", ".tiff", ".jpeg"}

# Thread-safe jobs store
JOBS_LOCK = threading.Lock()
JOBS = []


def load_jobs():
    global JOBS
    if os.path.exists(JOBS_FILE):
        try:
            with open(JOBS_FILE, "r", encoding="utf-8") as f:
                JOBS = json.load(f)
        except Exception:
            JOBS = []


def save_jobs():
    with JOBS_LOCK:
        try:
            with open(JOBS_FILE, "w", encoding="utf-8") as f:
                json.dump(JOBS, f, indent=2)
        except Exception as e:
            print(f"Error saving jobs: {e}")


load_jobs()


def get_bookmarks():
    """Return curated project bookmarks for quick navigation."""
    candidates = [
        {
            "name": "Embercore Armor (All)",
            "subtitle": "Light-Passthrough Filigree Armor",
            "icon": "shield",
            "path": os.path.join(BASE_DIR, "Embercore Armor"),
        },
        {
            "name": "Embercore: Cuirass / Chest",
            "subtitle": "Skull & Corset Openwork 4-Views",
            "icon": "shield",
            "path": os.path.join(BASE_DIR, "Embercore Armor", "01_Cuirass_Chest_Armor"),
        },
        {
            "name": "Embercore: Pauldrons",
            "subtitle": "3-Tier, 4-Tier & Feathered Shoulders",
            "icon": "shield",
            "path": os.path.join(BASE_DIR, "Embercore Armor", "02_Pauldrons_Shoulders"),
        },
        {
            "name": "Embercore: Bracers",
            "subtitle": "Single-Sided Forearm 4-View & Variants",
            "icon": "shield",
            "path": os.path.join(BASE_DIR, "Embercore Armor", "03_Bracers_Forearms"),
        },
        {
            "name": "Embercore: Tassets & Shields",
            "subtitle": "Openwork Skull Tasset & Shield Plates",
            "icon": "shield",
            "path": os.path.join(BASE_DIR, "Embercore Armor", "04_Tassets_and_Shields"),
        },
        {
            "name": "05_Elongated_LED_Tubes",
            "subtitle": "20 Helix & Chevron Staff Tubes",
            "icon": "sparkles",
            "path": os.path.join(BASE_DIR, "filigree staff", "05_Elongated_LED_Tubes"),
        },
        {
            "name": "04_Hollow_LED_Openwork",
            "subtitle": "Hollow Sleeves, Heads & Finales",
            "icon": "sun",
            "path": os.path.join(BASE_DIR, "filigree staff", "04_Hollow_LED_Openwork"),
        },
        {
            "name": "01_Heads (Staff Toppers)",
            "subtitle": "5 Filigree Staff Heads",
            "icon": "crown",
            "path": os.path.join(BASE_DIR, "filigree staff", "01_Heads"),
        },
        {
            "name": "02_Shaft_Sections",
            "subtitle": "15 Modular Shaft Segments",
            "icon": "layers",
            "path": os.path.join(BASE_DIR, "filigree staff", "02_Shaft_Sections"),
        },
        {
            "name": "03_Finales (Butt Caps)",
            "subtitle": "5 Staff Base Finales",
            "icon": "anchor",
            "path": os.path.join(BASE_DIR, "filigree staff", "03_Finales"),
        },
        {
            "name": "Filigree Staff Root",
            "subtitle": "Master Staff Project Folder",
            "icon": "folder",
            "path": os.path.join(BASE_DIR, "filigree staff"),
        },
        {
            "name": "Cosplay Portfolio & Builds",
            "subtitle": "30 Workshop Photos & Concepts",
            "icon": "folder",
            "path": os.path.join(BASE_DIR, "Cosplay Portfolio & Builds"),
        },
        {
            "name": "Tripo Web Staging",
            "subtitle": "Staged Batches for Web Studio (3000 Cr)",
            "icon": "inbox",
            "path": STAGING_DIR,
        },
        {
            "name": "Output 3D STLs",
            "subtitle": "Generated Tripo STL & GLB Files",
            "icon": "box",
            "path": OUTPUT_STL_DIR,
        },
        {
            "name": "Downloads Folder",
            "subtitle": "Browser Downloads",
            "icon": "download",
            "path": DOWNLOADS_DIR,
        },
    ]
    return [c for c in candidates if os.path.exists(c["path"])]


def convert_single_file_to_jpg(src_path, archive_original=True):
    """
    Convert a non-jpg image file (.jfif, .png, .webp, .heic, etc.) to .jpg in the same directory.
    Returns (jpg_path, was_converted).
    """
    ext = os.path.splitext(src_path)[1].lower()
    if ext == ".jpg":
        return src_path, False
    if ext not in CONVERTIBLE_EXTS:
        return src_path, False

    folder = os.path.dirname(src_path)
    stem = os.path.splitext(os.path.basename(src_path))[0]
    dst_jpg = os.path.join(folder, f"{stem}.jpg")

    with Image.open(src_path) as im:
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            bg = Image.new("RGB", im.size, (0, 0, 0))
            rgba = im.convert("RGBA")
            bg.paste(rgba, mask=rgba.split()[3])
            rgb_im = bg
        else:
            rgb_im = im.convert("RGB")
        rgb_im.save(dst_jpg, "JPEG", quality=95)

    if archive_original and os.path.abspath(src_path) != os.path.abspath(dst_jpg):
        orig_dir = os.path.join(folder, "_originals_raw")
        os.makedirs(orig_dir, exist_ok=True)
        try:
            shutil.move(src_path, os.path.join(orig_dir, os.path.basename(src_path)))
        except Exception:
            pass

    return dst_jpg, True


@app.route("/")
def index():
    initial_folder = DEFAULT_FOLDER if os.path.exists(DEFAULT_FOLDER) else BASE_DIR
    return render_template("index.html", initial_folder=initial_folder)


@app.route("/api/bookmarks", methods=["GET"])
def api_bookmarks():
    return jsonify({"bookmarks": get_bookmarks(), "default_folder": DEFAULT_FOLDER})


@app.route("/api/browse", methods=["GET"])
def api_browse():
    folder = request.args.get("path", "").strip()
    auto_convert = request.args.get("auto_convert", "false").lower() == "true"

    if not folder:
        folder = DEFAULT_FOLDER if os.path.exists(DEFAULT_FOLDER) else BASE_DIR

    folder = os.path.abspath(folder)
    if not os.path.exists(folder) or not os.path.isdir(folder):
        return jsonify({"error": f"Directory not found: {folder}"}), 404

    converted_files = []
    # Only auto-convert in project folders (never auto-move in system Downloads unless explicitly asked)
    is_downloads = os.path.normcase(folder) == os.path.normcase(DOWNLOADS_DIR)
    if auto_convert and not is_downloads:
        for fname in os.listdir(folder):
            fpath = os.path.join(folder, fname)
            if os.path.isfile(fpath):
                ext = os.path.splitext(fname)[1].lower()
                if ext in CONVERTIBLE_EXTS:
                    try:
                        jpg_path, did_conv = convert_single_file_to_jpg(fpath, archive_original=True)
                        if did_conv:
                            converted_files.append(os.path.basename(jpg_path))
                    except Exception as e:
                        print(f"Auto-convert skipped {fname}: {e}")

    subdirs = []
    images = []
    models = []
    unconverted_count = 0

    try:
        entries = list(os.scandir(folder))
    except PermissionError:
        return jsonify({"error": f"Permission denied: {folder}"}), 403

    for entry in entries:
        if entry.name.startswith(".") or entry.name in ("__pycache__", "_originals_raw"):
            continue
        if entry.is_dir():
            # Count images inside subfolder (recursively) for badge
            img_count = 0
            try:
                for root_w, dirs_w, files_w in os.walk(entry.path):
                    dirs_w[:] = [d for d in dirs_w if not d.startswith(".") and d not in ("__pycache__", "_originals_raw", "heic")]
                    for fn in files_w:
                        if os.path.splitext(fn)[1].lower() in IMAGE_EXTS:
                            img_count += 1
            except Exception:
                pass
            subdirs.append({
                "name": entry.name,
                "path": entry.path,
                "image_count": img_count,
            })
        elif entry.is_file():
            ext = os.path.splitext(entry.name)[1].lower()
            stat = entry.stat()
            if ext in IMAGE_EXTS:
                if ext != ".jpg":
                    unconverted_count += 1
                width, height = 0, 0
                try:
                    with Image.open(entry.path) as im:
                        width, height = im.size
                except Exception:
                    pass
                images.append({
                    "name": entry.name,
                    "path": entry.path,
                    "ext": ext.lstrip(".").upper(),
                    "is_jpg": ext == ".jpg",
                    "size_bytes": stat.st_size,
                    "mtime": stat.st_mtime,
                    "width": width,
                    "height": height,
                })
            elif ext in (".stl", ".glb", ".obj", ".3mf"):
                models.append({
                    "name": entry.name,
                    "path": entry.path,
                    "ext": ext.lstrip(".").upper(),
                    "size_bytes": stat.st_size,
                    "mtime": stat.st_mtime,
                })

    # If this is a parent category folder with subfolders and 0 direct images, roll up child images
    if not images and subdirs and os.path.normcase(folder) != os.path.normcase(BASE_DIR):
        for root_w, dirs_w, files_w in os.walk(folder):
            dirs_w[:] = [d for d in dirs_w if not d.startswith(".") and d not in ("__pycache__", "_originals_raw", "heic")]
            for fn in files_w:
                ext = os.path.splitext(fn)[1].lower()
                if ext in IMAGE_EXTS:
                    fpath = os.path.join(root_w, fn)
                    try:
                        stat = os.stat(fpath)
                        width, height = 0, 0
                        with Image.open(fpath) as im:
                            width, height = im.size
                        images.append({
                            "name": fn,
                            "path": fpath,
                            "ext": ext.lstrip(".").upper(),
                            "is_jpg": ext == ".jpg",
                            "size_bytes": stat.st_size,
                            "mtime": stat.st_mtime,
                            "width": width,
                            "height": height,
                        })
                    except Exception:
                        pass

    subdirs.sort(key=lambda d: d["name"].lower())
    images.sort(key=lambda x: x["name"].lower())
    models.sort(key=lambda x: x["mtime"], reverse=True)

    parent_dir = os.path.dirname(folder) if os.path.dirname(folder) != folder else None

    return jsonify({
        "current_folder": folder,
        "folder_name": os.path.basename(folder) or folder,
        "parent_folder": parent_dir,
        "subdirs": subdirs,
        "images": images,
        "models": models,
        "unconverted_count": unconverted_count,
        "converted_now": converted_files,
    })


@app.route("/api/pick-folder", methods=["POST"])
def api_pick_folder():
    """Open native Windows folder picker dialog."""
    current = (request.json or {}).get("initial_dir", BASE_DIR)
    if not os.path.exists(current):
        current = BASE_DIR
    try:
        cmd = [
            sys.executable,
            "-c",
            (
                "import tkinter as tk; from tkinter import filedialog; "
                "root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True); "
                f"p = filedialog.askdirectory(initialdir={repr(current)}, title='Select Folder for CosplayDad3D Studio'); "
                "print(p)"
            ),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        picked = res.stdout.strip()
        if picked and os.path.isdir(picked):
            return jsonify({"path": os.path.abspath(picked)})
        return jsonify({"path": None})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/image")
def api_serve_image():
    path = request.args.get("path", "")
    if not path or not os.path.isfile(path):
        abort(404)
    ext = os.path.splitext(path)[1].lower()
    if ext in (".heic", ".heif"):
        # Serve on-the-fly JPEG preview for HEIC
        from io import BytesIO
        with Image.open(path) as im:
            buf = BytesIO()
            im.convert("RGB").save(buf, "JPEG", quality=90)
            buf.seek(0)
            return send_file(buf, mimetype="image/jpeg")
    return send_file(path)


@app.route("/api/convert-folder", methods=["POST"])
def api_convert_folder():
    """Convert all non-JPG images in the given folder (or specific list of files) to .JPG."""
    data = request.json or {}
    folder = data.get("folder", "")
    target_files = data.get("files", [])
    archive_originals = data.get("archive_originals", True)

    converted = []
    errors = []

    if target_files:
        file_list = target_files
    elif folder and os.path.isdir(folder):
        file_list = [os.path.join(folder, f) for f in os.listdir(folder)]
    else:
        return jsonify({"error": "Valid folder or files required"}), 400

    for fpath in file_list:
        if not os.path.isfile(fpath):
            continue
        ext = os.path.splitext(fpath)[1].lower()
        if ext in CONVERTIBLE_EXTS:
            try:
                jpg_path, did_conv = convert_single_file_to_jpg(fpath, archive_original=archive_originals)
                if did_conv:
                    converted.append({
                        "original": os.path.basename(fpath),
                        "jpg": os.path.basename(jpg_path),
                        "path": jpg_path,
                    })
            except Exception as e:
                errors.append({"file": os.path.basename(fpath), "error": str(e)})

    return jsonify({"converted": converted, "errors": errors, "count": len(converted)})


@app.route("/api/pull-downloads", methods=["POST"])
def api_pull_downloads():
    """
    Scan user's Downloads folder for recent Gemini / Grok / AI images,
    convert them to .jpg, and store them in the active destination folder.
    """
    data = request.json or {}
    dest_folder = data.get("dest_folder") or os.path.join(BASE_DIR, "gem-images to do")
    limit_count = int(data.get("limit", 10))
    only_new_minutes = float(data.get("minutes", 1440))  # default last 24h

    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder, exist_ok=True)

    if not os.path.exists(DOWNLOADS_DIR):
        return jsonify({"error": "Downloads folder not found"}), 404

    now = time.time()
    candidates = []
    for fname in os.listdir(DOWNLOADS_DIR):
        fpath = os.path.join(DOWNLOADS_DIR, fname)
        if not os.path.isfile(fpath):
            continue
        ext = os.path.splitext(fname)[1].lower()
        if ext not in IMAGE_EXTS:
            continue
        mtime = os.path.getmtime(fpath)
        if (now - mtime) <= (only_new_minutes * 60):
            candidates.append((mtime, fpath, fname))

    candidates.sort(key=lambda x: x[0], reverse=True)
    candidates = candidates[:limit_count]

    imported = []
    for _, src_path, fname in candidates:
        stem = os.path.splitext(fname)[0]
        dst_jpg = os.path.join(dest_folder, f"{stem}.jpg")
        if os.path.exists(dst_jpg):
            continue
        try:
            with Image.open(src_path) as im:
                rgb = im.convert("RGB")
                rgb.save(dst_jpg, "JPEG", quality=95)
            imported.append({
                "source": fname,
                "jpg": os.path.basename(dst_jpg),
                "path": dst_jpg,
            })
        except Exception as e:
            print(f"Error pulling {fname}: {e}")

    return jsonify({"imported": imported, "count": len(imported), "dest_folder": dest_folder})


@app.route("/api/upload-drop", methods=["POST"])
def api_upload_drop():
    """Handle drag-and-drop image files from browser/desktop, auto-converting to .jpg."""
    dest_folder = request.form.get("folder", BASE_DIR)
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder, exist_ok=True)

    saved = []
    for f in request.files.getlist("files"):
        if not f.filename:
            continue
        stem = os.path.splitext(os.path.basename(f.filename))[0]
        dst_jpg = os.path.join(dest_folder, f"{stem}.jpg")
        counter = 1
        while os.path.exists(dst_jpg):
            dst_jpg = os.path.join(dest_folder, f"{stem}_{counter}.jpg")
            counter += 1

        im = Image.open(f.stream)
        rgb = im.convert("RGB")
        rgb.save(dst_jpg, "JPEG", quality=95)
        saved.append({"name": os.path.basename(dst_jpg), "path": dst_jpg})

    return jsonify({"saved": saved, "count": len(saved)})


@app.route("/api/rename", methods=["POST"])
def api_rename():
    data = request.json or {}
    old_path = data.get("path", "")
    new_name = data.get("new_name", "").strip()
    if not old_path or not os.path.isfile(old_path) or not new_name:
        return jsonify({"error": "Invalid path or new name"}), 400

    if not new_name.lower().endswith(".jpg"):
        new_name += ".jpg"

    new_path = os.path.join(os.path.dirname(old_path), new_name)
    if os.path.exists(new_path) and os.path.abspath(old_path) != os.path.abspath(new_path):
        return jsonify({"error": f"File '{new_name}' already exists"}), 409

    os.rename(old_path, new_path)
    return jsonify({"old_path": old_path, "new_path": new_path, "new_name": new_name})


@app.route("/api/reveal", methods=["POST"])
def api_reveal():
    """Highlight file or open folder in Windows Explorer."""
    path = (request.json or {}).get("path", "")
    if not path or not os.path.exists(path):
        return jsonify({"error": "Path does not exist"}), 404
    path = os.path.normpath(path)
    if os.path.isfile(path):
        subprocess.Popen(["explorer", f"/select,{path}"])
    else:
        subprocess.Popen(["explorer", path])
    return jsonify({"ok": True})


@app.route("/api/tripo/balance", methods=["GET"])
def api_tripo_balance():
    try:
        bal = tripo_client.get_balance()
        return jsonify({"ok": True, "balance": bal.get("balance", 0.0), "frozen": bal.get("frozen", 0.0)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


def _run_tripo_pipeline(job_id):
    """Background worker thread that runs the full Tripo 3D + STL conversion pipeline."""
    job = None
    with JOBS_LOCK:
        for j in JOBS:
            if j["id"] == job_id:
                job = j
                break
    if not job:
        return

    def update_job(**kwargs):
        with JOBS_LOCK:
            job.update(kwargs)
            job["updated_at"] = datetime.now().isoformat(timespec="seconds")
        save_jobs()

    try:
        update_job(status="uploading", status_label="Uploading to Tripo...", progress=5)

        mode = job["mode"]
        model_ver = job.get("model", "v3.1-20260211")
        geometry_quality = job.get("geometry_quality", "detailed")
        texture = job.get("texture", False)
        flatten_bottom = job.get("flatten_bottom", False)
        export_format = job.get("export_format", "STL")

        if mode == "single":
            img_path = job["images"]["front"]
            # Ensure JPG before sending
            if not img_path.lower().endswith(".jpg"):
                img_path, _ = convert_single_file_to_jpg(img_path, archive_original=False)
            gen_task_id = tripo_client.create_image_to_model_task(
                image_path=img_path,
                model=model_ver,
                geometry_quality=geometry_quality,
                texture=texture,
                pbr=texture,
            )
        else:
            views = {}
            for slot, p in job["images"].items():
                if p and os.path.exists(p):
                    if not p.lower().endswith(".jpg"):
                        p, _ = convert_single_file_to_jpg(p, archive_original=False)
                    views[slot] = p
            gen_task_id = tripo_client.create_multiview_to_model_task(
                views_dict=views,
                model=model_ver,
                geometry_quality=geometry_quality,
                texture=texture,
                pbr=texture,
            )

        update_job(
            gen_task_id=gen_task_id,
            status="generating_3d",
            status_label="Generating 3D Mesh...",
            progress=15,
        )

        # Poll 3D generation task
        start_time = time.time()
        gen_output = None
        while time.time() - start_time < 600:
            t_data = tripo_client.get_task_status(gen_task_id)
            t_status = t_data.get("status")
            t_prog = int(t_data.get("progress", 0))
            mapped_prog = 15 + int(t_prog * 0.50)  # 15% -> 65%
            update_job(progress=mapped_prog, status_label=f"Generating 3D Mesh ({t_prog}%)...")

            if t_status == "success":
                gen_output = t_data.get("output", {})
                break
            elif t_status in ("failed", "cancelled", "banned", "expired"):
                err_msg = t_data.get("error_message") or f"Tripo 3D task {t_status}"
                raise RuntimeError(err_msg)
            time.sleep(4)

        if not gen_output:
            raise TimeoutError("Timed out waiting for 3D generation task.")

        # Download GLB preview if present
        glb_url = gen_output.get("model_url") or gen_output.get("pbr_model") or gen_output.get("base_model")
        safe_stem = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in job["title"]).strip("_")
        timestamp_tag = datetime.now().strftime("%H%M%S")

        glb_local = None
        if glb_url:
            glb_local = os.path.join(OUTPUT_STL_DIR, f"{safe_stem}_{timestamp_tag}.glb")
            try:
                tripo_client.download_file(glb_url, glb_local)
            except Exception as e:
                print(f"GLB download warning: {e}")

        # Step 2: Convert to STL (or 3MF/OBJ)
        update_job(status="converting_stl", status_label=f"Converting to .{export_format}...", progress=70)
        conv_task_id = tripo_client.create_convert_to_stl_task(
            source_task_id=gen_task_id,
            export_format=export_format,
            flatten_bottom=flatten_bottom,
        )
        update_job(conv_task_id=conv_task_id)

        start_conv = time.time()
        conv_output = None
        while time.time() - start_conv < 300:
            c_data = tripo_client.get_task_status(conv_task_id)
            c_status = c_data.get("status")
            c_prog = int(c_data.get("progress", 0))
            mapped_prog = 70 + int(c_prog * 0.25)  # 70% -> 95%
            update_job(progress=mapped_prog, status_label=f"Converting to .{export_format} ({c_prog}%)...")

            if c_status == "success":
                conv_output = c_data.get("output", {})
                break
            elif c_status in ("failed", "cancelled"):
                err_msg = c_data.get("error_message") or f"STL conversion failed ({c_status})"
                raise RuntimeError(err_msg)
            time.sleep(3)

        if not conv_output:
            raise TimeoutError("Timed out waiting for STL conversion.")

        stl_url = conv_output.get("model_url") or conv_output.get("model")
        if not stl_url:
            raise RuntimeError(f"No model_url found in conversion output: {conv_output}")

        ext_lower = export_format.lower()
        stl_filename = f"{safe_stem}_{timestamp_tag}.{ext_lower}"
        stl_local = os.path.join(OUTPUT_STL_DIR, stl_filename)

        update_job(status="downloading", status_label=f"Downloading .{export_format}...", progress=96)
        tripo_client.download_file(stl_url, stl_local)

        # Also copy into the source image folder's stl/ subdirectory for organization
        source_folder = job.get("source_folder")
        project_stl_copy = None
        if source_folder and os.path.isdir(source_folder):
            proj_stl_dir = os.path.join(source_folder, "stl_models")
            os.makedirs(proj_stl_dir, exist_ok=True)
            project_stl_copy = os.path.join(proj_stl_dir, stl_filename)
            shutil.copyfile(stl_local, project_stl_copy)

        update_job(
            status="success",
            status_label=f"Ready (.{export_format})",
            progress=100,
            stl_path=stl_local,
            project_stl_path=project_stl_copy,
            glb_path=glb_local,
            stl_size=os.path.getsize(stl_local),
        )

    except Exception as e:
        update_job(
            status="failed",
            status_label="Failed",
            error=str(e),
        )


@app.route("/api/tripo/generate", methods=["POST"])
def api_tripo_generate():
    data = request.json or {}
    mode = data.get("mode", "single")  # 'single' or 'multiview'
    model_ver = data.get("model", "v3.1-20260211")
    geometry_quality = data.get("geometry_quality", "detailed")
    texture = bool(data.get("texture", False))
    flatten_bottom = bool(data.get("flatten_bottom", False))
    export_format = data.get("export_format", "STL")
    source_folder = data.get("source_folder", "")

    created_jobs = []

    if mode == "single":
        image_paths = data.get("image_paths", [])
        if not image_paths:
            return jsonify({"error": "Select at least one image to send to Tripo."}), 400

        for img_path in image_paths:
            if not os.path.isfile(img_path):
                continue
            title = os.path.splitext(os.path.basename(img_path))[0]
            job_id = str(uuid.uuid4())[:8]
            job = {
                "id": job_id,
                "title": title,
                "mode": "single",
                "model": model_ver,
                "geometry_quality": geometry_quality,
                "texture": texture,
                "flatten_bottom": flatten_bottom,
                "export_format": export_format,
                "source_folder": source_folder or os.path.dirname(img_path),
                "images": {"front": img_path},
                "status": "queued",
                "status_label": "Queued...",
                "progress": 0,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "updated_at": datetime.now().isoformat(timespec="seconds"),
                "stl_path": None,
                "glb_path": None,
                "error": None,
            }
            with JOBS_LOCK:
                JOBS.insert(0, job)
            save_jobs()
            created_jobs.append(job)
            t = threading.Thread(target=_run_tripo_pipeline, args=(job_id,), daemon=True)
            t.start()

    elif mode == "multiview":
        views = data.get("views", {})
        front = views.get("front")
        if not front or not os.path.isfile(front):
            return jsonify({"error": "Front view image is required for 4-View mode."}), 400
        valid_views = {k: v for k, v in views.items() if v and os.path.isfile(v)}
        if len(valid_views) < 2:
            return jsonify({"error": "Provide at least 2 views (including Front) for Multi-View mode."}), 400

        title = data.get("title") or os.path.splitext(os.path.basename(front))[0].replace("_front", "") + "_4view"
        job_id = str(uuid.uuid4())[:8]
        job = {
            "id": job_id,
            "title": title,
            "mode": "multiview",
            "model": model_ver,
            "geometry_quality": geometry_quality,
            "texture": texture,
            "flatten_bottom": flatten_bottom,
            "export_format": export_format,
            "source_folder": source_folder or os.path.dirname(front),
            "images": valid_views,
            "status": "queued",
            "status_label": "Queued 4-View...",
            "progress": 0,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "stl_path": None,
            "glb_path": None,
            "error": None,
        }
        with JOBS_LOCK:
            JOBS.insert(0, job)
        save_jobs()
        created_jobs.append(job)
        t = threading.Thread(target=_run_tripo_pipeline, args=(job_id,), daemon=True)
        t.start()

    return jsonify({"jobs": created_jobs, "count": len(created_jobs)})


@app.route("/api/tripo/jobs", methods=["GET"])
def api_tripo_jobs():
    with JOBS_LOCK:
        return jsonify({"jobs": JOBS})


@app.route("/api/tripo/jobs/<job_id>", methods=["DELETE"])
def api_delete_job(job_id):
    global JOBS
    with JOBS_LOCK:
        JOBS = [j for j in JOBS if j["id"] != job_id]
    save_jobs()
    return jsonify({"ok": True})


@app.route("/api/download")
def api_download_file():
    path = request.args.get("path", "")
    if not path or not os.path.isfile(path):
        abort(404)
    return send_file(path, as_attachment=True)


@app.route("/api/tripo/stage-web", methods=["POST"])
def api_tripo_stage_web():
    """
    Stage selected 1-image or 4-view set into Tripo_Web_Staging/CURRENT_ACTIVE_BATCH
    (and an archived subfolder), copy to Windows Clipboard, open Explorer + Tripo Web Studio
    so the user can spend their 3,000 monthly Web Studio subscription credits effortlessly.
    """
    import webbrowser

    data = request.json or {}
    mode = data.get("mode", "single")
    source_folder = data.get("source_folder", "")
    export_format = data.get("export_format", "STL")
    open_studio = bool(data.get("open_studio", True))

    active_batch_dir = os.path.join(STAGING_DIR, "00_CURRENT_ACTIVE_BATCH")
    os.makedirs(active_batch_dir, exist_ok=True)
    # Clear old files from active batch dir so ONLY the current staged files appear in the popup window
    for old_f in os.listdir(active_batch_dir):
        old_p = os.path.join(active_batch_dir, old_f)
        if os.path.isfile(old_p):
            try:
                os.remove(old_p)
            except Exception:
                pass

    staged_files = []
    created_jobs = []

    if mode == "single":
        image_paths = [p for p in data.get("image_paths", []) if p and os.path.isfile(p)]
        if not image_paths:
            return jsonify({"error": "Select at least one image in the gallery first."}), 400

        for idx, img_path in enumerate(image_paths, start=1):
            jpg_path, _ = convert_single_file_to_jpg(img_path, archive_original=False)
            base_stem = os.path.splitext(os.path.basename(jpg_path))[0]
            safe_stem = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in base_stem).strip("_")

            # Archive folder per item
            item_dir = os.path.join(STAGING_DIR, safe_stem)
            os.makedirs(item_dir, exist_ok=True)

            staged_name = f"{idx:02d}_{safe_stem}.jpg" if len(image_paths) > 1 else f"{safe_stem}.jpg"
            dst_active = os.path.join(active_batch_dir, staged_name)
            dst_archive = os.path.join(item_dir, f"{safe_stem}.jpg")

            shutil.copyfile(jpg_path, dst_active)
            shutil.copyfile(jpg_path, dst_archive)
            staged_files.append(dst_active)

            job_id = str(uuid.uuid4())[:8]
            job = {
                "id": job_id,
                "title": base_stem,
                "mode": "single",
                "model": "Tripo Web Studio (3000 Cr Sub)",
                "export_format": export_format,
                "source_folder": source_folder or os.path.dirname(img_path),
                "images": {"front": dst_archive},
                "staged_dir": active_batch_dir,
                "status": "staged_web",
                "status_label": "Staged for Web",
                "progress": 50,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "updated_at": datetime.now().isoformat(timespec="seconds"),
                "stl_path": None,
                "error": None,
            }
            with JOBS_LOCK:
                JOBS.insert(0, job)
            created_jobs.append(job)

        save_jobs()

    elif mode == "multiview":
        views = data.get("views", {})
        front = views.get("front")
        if not front or not os.path.isfile(front):
            return jsonify({"error": "Front view image is required for 4-View mode."}), 400

        raw_title = data.get("title") or os.path.splitext(os.path.basename(front))[0].replace("_front", "") + "_4view"
        safe_title = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in raw_title).strip("_")
        item_dir = os.path.join(STAGING_DIR, safe_title)
        os.makedirs(item_dir, exist_ok=True)

        slot_order = [("front", "01_FRONT"), ("left", "02_LEFT"), ("back", "03_BACK"), ("right", "04_RIGHT")]
        valid_views = {}
        for slot_key, prefix in slot_order:
            p = views.get(slot_key)
            if p and os.path.isfile(p):
                jpg_path, _ = convert_single_file_to_jpg(p, archive_original=False)
                fname = f"{prefix}_{safe_title}.jpg"
                dst_active = os.path.join(active_batch_dir, fname)
                dst_archive = os.path.join(item_dir, fname)
                shutil.copyfile(jpg_path, dst_active)
                shutil.copyfile(jpg_path, dst_archive)
                staged_files.append(dst_active)
                valid_views[slot_key] = dst_archive

        job_id = str(uuid.uuid4())[:8]
        job = {
            "id": job_id,
            "title": raw_title,
            "mode": "multiview",
            "model": "Tripo Web Studio (4-View Sub)",
            "export_format": export_format,
            "source_folder": source_folder or os.path.dirname(front),
            "images": valid_views,
            "staged_dir": active_batch_dir,
            "status": "staged_web",
            "status_label": f"Staged 4-View ({len(valid_views)}/4)",
            "progress": 50,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "stl_path": None,
            "error": None,
        }
        with JOBS_LOCK:
            JOBS.insert(0, job)
        save_jobs()
        created_jobs.append(job)

    # Copy staged file(s) to Windows clipboard so user can also press Ctrl+V in Tripo Web Studio
    if staged_files:
        try:
            ps_paths = ",".join([f"'{p}'" for p in staged_files])
            subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", f"Set-Clipboard -Path {ps_paths}"],
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except Exception:
            pass

        # Pop open the active staging folder with the first file highlighted
        try:
            subprocess.Popen(["explorer.exe", f"/select,{os.path.normpath(staged_files[0])}"])
        except Exception:
            pass

    if open_studio:
        try:
            webbrowser.open("https://studio.tripo3d.ai")
        except Exception:
            pass

    return jsonify({
        "ok": True,
        "staged_dir": active_batch_dir,
        "staged_files": [os.path.basename(f) for f in staged_files],
        "jobs": created_jobs,
    })


@app.route("/api/tripo/pull-stl/<job_id>", methods=["POST"])
def api_tripo_pull_stl(job_id):
    """
    Grab the most recently downloaded .stl / .glb / .3mf / .obj from ~/Downloads,
    rename it cleanly after the staged job title, and save it to output_stl/ and the source folder.
    """
    target_job = None
    with JOBS_LOCK:
        for j in JOBS:
            if j["id"] == job_id:
                target_job = j
                break

    if not target_job:
        return jsonify({"error": "Job not found."}), 404

    if not os.path.exists(DOWNLOADS_DIR):
        return jsonify({"error": "Downloads directory not found."}), 404

    model_exts = {".stl", ".glb", ".3mf", ".obj"}
    candidates = []
    for entry in os.scandir(DOWNLOADS_DIR):
        if entry.is_file():
            ext = os.path.splitext(entry.name)[1].lower()
            if ext in model_exts:
                candidates.append((entry.stat().st_mtime, entry.path, ext))

    if not candidates:
        return jsonify({"error": "No .STL, .GLB, .3MF, or .OBJ files found in your Downloads folder yet."}), 404

    candidates.sort(key=lambda x: x[0], reverse=True)
    newest_mtime, newest_path, ext = candidates[0]

    safe_stem = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in target_job["title"]).strip("_")
    timestamp_tag = datetime.now().strftime("%H%M%S")
    dst_filename = f"{safe_stem}_{timestamp_tag}{ext}"
    dst_stl = os.path.join(OUTPUT_STL_DIR, dst_filename)

    shutil.copyfile(newest_path, dst_stl)

    source_folder = target_job.get("source_folder")
    project_stl_copy = None
    if source_folder and os.path.isdir(source_folder):
        proj_stl_dir = os.path.join(source_folder, "stl_models")
        os.makedirs(proj_stl_dir, exist_ok=True)
        project_stl_copy = os.path.join(proj_stl_dir, dst_filename)
        shutil.copyfile(dst_stl, project_stl_copy)

    with JOBS_LOCK:
        target_job["status"] = "success"
        target_job["status_label"] = f"Imported ({ext.upper()})"
        target_job["progress"] = 100
        target_job["stl_path"] = dst_stl
        target_job["project_stl_path"] = project_stl_copy
        target_job["export_format"] = ext.lstrip(".").upper()
        target_job["updated_at"] = datetime.now().isoformat(timespec="seconds")
    save_jobs()

    return jsonify({
        "ok": True,
        "imported_from": os.path.basename(newest_path),
        "saved_to": dst_stl,
        "job": target_job,
    })


if __name__ == "__main__":
    import webbrowser
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("=" * 68)
    print("  CosplayDad3D Glass Studio - Image & Tripo 3D Hub")
    print("  Local URL: http://127.0.0.1:5050")
    print("=" * 68)
    if "--no-browser" not in sys.argv:
        threading.Timer(1.2, lambda: webbrowser.open("http://127.0.0.1:5050")).start()
    app.run(host="127.0.0.1", port=5050, debug=False, threaded=True)

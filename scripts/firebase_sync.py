#!/usr/bin/env python3
"""
Firebase Hosting Publisher & Firestore Cloud Sync for @cosplaydad3d
===================================================================
- Publishes CosplayDad_Dashboard.html + web-optimized media to:
    https://myairotica.web.app/cosplaydad/
  (hosted inside c:\\P\\DP\\dist\\cosplaydad\\ with zero links from DuoScribe PWA).
- Pulls and resets live review decisions from Firestore REST endpoint:
    https://firestore.googleapis.com/v1/projects/myairotica/databases/(default)/documents/cosplaydad_sync/review_state
  so any clicks made on the user's iPhone are automatically applied when the user
  tells Antigravity "clean up"!
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Optional

from PIL import Image, ImageOps
from path_config import find_dp_project_root, find_drive_root

DRIVE_ROOT = find_drive_root()
DP_PROJECT_ROOT = find_dp_project_root()
DP_DIST_COSPLAY = DP_PROJECT_ROOT / "dist" / "cosplaydad"

FIRESTORE_DOC_URL = (
    "https://firestore.googleapis.com/v1/projects/myairotica/"
    "databases/(default)/documents/cosplaydad_sync/review_state"
)
LIVE_DASHBOARD_URL = "https://myairotica.web.app/cosplaydad/"


def fetch_cloud_review_state() -> Optional[Dict]:
    """Fetch the latest review state saved from iPhone/browser via Firestore REST API."""
    try:
        req = urllib.request.Request(FIRESTORE_DOC_URL, method="GET")
        with urllib.request.urlopen(req, timeout=8) as resp:
            doc = json.loads(resp.read().decode("utf-8"))
            fields = doc.get("fields", {})
            payload_str = fields.get("payload_json", {}).get("stringValue", "")
            if payload_str:
                return json.loads(payload_str)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        print(f"Firestore fetch HTTP warning: {e}")
    except Exception as e:
        print(f"Firestore fetch warning: {e}")
    return None


def clear_cloud_review_state() -> None:
    """Clear/reset the cloud review_state doc after disk cleanup has been applied."""
    try:
        req = urllib.request.Request(FIRESTORE_DOC_URL, method="DELETE")
        with urllib.request.urlopen(req, timeout=8):
            print("Cleared processed cloud review_state in Firestore.")
    except Exception:
        pass


def copy_media_for_web(rel_posix_path: str) -> None:
    """
    Copy a media file referenced by the dashboard (relative to G:\\My Drive\\!cosplaydad3d)
    into c:\\P\\DP\\dist\\cosplaydad\\<rel_posix_path>.
    Images are optimized to crisp 1080px max width JPEGs (~180KB) for fast mobile loading
    while remaining sharp enough to Save to Photos on iPhone for Instagram.
    """
    if not rel_posix_path:
        return
    src = DRIVE_ROOT / Path(rel_posix_path)
    if not src.exists():
        return

    dst = DP_DIST_COSPLAY / Path(rel_posix_path)
    dst.parent.mkdir(parents=True, exist_ok=True)

    # Skip re-encoding if destination already exists and is newer/same size check
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return

    ext = src.suffix.lower()
    if ext in {".jpg", ".jpeg", ".png", ".webp"}:
        with Image.open(src) as im:
            im_rgb = ImageOps.exif_transpose(im).convert("RGB")
            w, h = im_rgb.size
            if w > 1080:
                new_h = int(round(h * (1080.0 / w)))
                im_rgb = im_rgb.resize((1080, new_h), Image.Resampling.LANCZOS)
            im_rgb.save(dst, "JPEG", quality=86, optimize=True)
    else:
        shutil.copy2(src, dst)


def stage_and_deploy_firebase(
    ready_batches: list,
    posted_batches: list,
    mw_models: list,
    deploy: bool = True,
) -> str:
    """
    Stage CosplayDad_Dashboard.html as c:\\P\\DP\\dist\\cosplaydad\\index.html,
    sync all referenced media, and deploy to Firebase Hosting (`myairotica`).
    """
    DP_DIST_COSPLAY.mkdir(parents=True, exist_ok=True)

    # Copy dashboard HTML to dist/cosplaydad/index.html
    dashboard_src = DRIVE_ROOT / "CosplayDad_Dashboard.html"
    if not dashboard_src.exists():
        raise FileNotFoundError(f"Missing {dashboard_src}")

    shutil.copy2(dashboard_src, DP_DIST_COSPLAY / "index.html")

    # Collect all media paths referenced across batches and MW models
    media_rels = set()
    for b in ready_batches + posted_batches:
        for s in b.get("slides", []):
            if s.get("rel"):
                media_rels.add(s["rel"])
            if s.get("poster_rel"):
                media_rels.add(s["poster_rel"])

    for m in mw_models:
        for med in m.get("media", []):
            if med.get("rel"):
                media_rels.add(med["rel"])

    for rel in sorted(media_rels):
        copy_media_for_web(rel)

    print(f"Staged {len(media_rels)} web media files into {DP_DIST_COSPLAY}")

    if deploy:
        print("Deploying to Firebase Hosting + Firestore rules (project: myairotica)...")
        res = subprocess.run(
            "firebase deploy --only hosting,firestore:rules",
            cwd=str(DP_PROJECT_ROOT),
            shell=True,
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            print("Firebase deploy stderr:", res.stderr)
            raise RuntimeError(f"firebase deploy failed with exit code {res.returncode}")
        print(f"[OK] Deployed live to: {LIVE_DASHBOARD_URL}")

    return LIVE_DASHBOARD_URL

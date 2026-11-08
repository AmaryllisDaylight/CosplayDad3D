#!/usr/bin/env python3
"""
Portable Path Resolver for @cosplaydad3d (Desktop & Laptop Compatible)
======================================================================
Automatically finds:
- `DRIVE_ROOT` (`!cosplaydad3d` on Google Drive across any drive letter C:..Z: or ~/Google Drive)
- `WORKSPACE_ROOT` (the folder containing this repo's `scripts/` directory)
- `DP_PROJECT_ROOT` (`DP` / `Duoprompt` repo for Firebase Hosting deployment)
"""

from __future__ import annotations

import os
import string
import subprocess
import time
from pathlib import Path


def find_workspace_root() -> Path:
    """Return the root of the CosplayDad3D codebase (parent of `scripts/`)."""
    return Path(__file__).resolve().parent.parent


def _scan_drive_candidates() -> Path | None:
    # Check common drive letters (G: first for speed, then C:..Z:)
    drive_letters = ["G"] + [c for c in string.ascii_uppercase if c != "G"]
    for letter in drive_letters:
        for sub in ("My Drive\\!cosplaydad3d", "!cosplaydad3d", "Google Drive\\!cosplaydad3d"):
            cand = Path(f"{letter}:\\{sub}")
            try:
                if cand.exists():
                    return cand
            except OSError:
                continue

    # Check under %USERPROFILE%
    home = Path.home()
    for rel in (
        "Google Drive/My Drive/!cosplaydad3d",
        "Google Drive/!cosplaydad3d",
        "My Drive/!cosplaydad3d",
    ):
        cand = home / rel
        if cand.exists():
            return cand
    return None


def find_drive_root() -> Path:
    """
    Auto-detect the `!cosplaydad3d` Google Drive folder across any Windows drive letter
    (G:\\My Drive\\!cosplaydad3d, H:\\My Drive\\!cosplaydad3d, etc.) or user profile path,
    or via the COSPLAYDAD_DRIVE_ROOT environment variable. Automatically launches
    Google Drive for Desktop if it isn't running yet.
    """
    env_override = os.environ.get("COSPLAYDAD_DRIVE_ROOT")
    if env_override:
        p = Path(env_override)
        if p.exists():
            return p

    # If running directly inside `!cosplaydad3d/00_System_Scripts_And_Repo/scripts`
    ws_root = find_workspace_root()
    if ws_root.parent.name.lower() == "!cosplaydad3d":
        return ws_root.parent

    found = _scan_drive_candidates()
    if found is not None:
        return found

    # Try auto-starting Google Drive for Desktop if installed on Windows
    gdfs_dir = Path(r"C:\Program Files\Google\Drive File Stream")
    if gdfs_dir.exists():
        exes = sorted(gdfs_dir.glob("*/GoogleDriveFS.exe"), reverse=True)
        if exes:
            try:
                subprocess.Popen(
                    [str(exes[0])],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                for _ in range(10):
                    time.sleep(1)
                    found = _scan_drive_candidates()
                    if found is not None:
                        return found
            except Exception:
                pass

    # Fallback default
    return Path(r"G:\My Drive\!cosplaydad3d")


def find_dp_project_root() -> Path:
    """Auto-detect the `DP` / `Duoprompt` Firebase project folder on Desktop or Laptop."""
    env_override = os.environ.get("COSPLAYDAD_DP_ROOT")
    if env_override:
        p = Path(env_override)
        if p.exists():
            return p

    ws_root = find_workspace_root()
    candidates = [
        Path(r"c:\P\DP"),
        Path(r"c:\P\Duoprompt"),
        ws_root.parent / "DP",
        ws_root.parent / "Duoprompt",
        Path.home() / "P" / "DP",
        Path.home() / "DP",
        Path.home() / "Duoprompt",
    ]
    for c in candidates:
        try:
            if c.exists() and (c / "firebase.json").exists():
                return c
        except OSError:
            continue

    return Path(r"c:\P\DP")

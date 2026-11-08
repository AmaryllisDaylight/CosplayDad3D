#!/usr/bin/env python3
"""
Custom Windows URL Protocol Handler (`cosplaydad://open/<relative_path>`)
=========================================================================
Allows clicking "📂 Open Folder in Explorer" directly from https://myairotica.web.app/cosplaydad/
(or local CosplayDad_Dashboard.html) on the user's PC to pop open the exact local folder
in Windows File Explorer so the user can drag-and-drop photos straight into Instagram or MakerWorld!

Run `python c:\P\CosplayDad3D\scripts\open_folder_protocol.py --register` once to register the
`cosplaydad://` protocol in HKEY_CURRENT_USER\Software\Classes\cosplaydad.
"""

from __future__ import annotations

import os
import sys
import urllib.parse
import winreg
from pathlib import Path
from path_config import find_drive_root

DRIVE_ROOT = find_drive_root()


def register_protocol() -> None:
    script_path = Path(__file__).resolve()
    pythonw = Path(sys.executable).parent / "pythonw.exe"
    if not pythonw.exists():
        pythonw = Path(sys.executable)

    cmd_str = f'"{pythonw}" "{script_path}" "%1"'

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\cosplaydad") as k:
        winreg.SetValue(k, "", winreg.REG_SZ, "URL:CosplayDad3D Folder Opener")
        winreg.SetValueEx(k, "URL Protocol", 0, winreg.REG_SZ, "")

    with winreg.CreateKey(
        winreg.HKEY_CURRENT_USER, r"Software\Classes\cosplaydad\shell\open\command"
    ) as ck:
        winreg.SetValue(ck, "", winreg.REG_SZ, cmd_str)

    print(f"[OK] Registered cosplaydad:// URL protocol -> {cmd_str}")


def handle_url(raw_url: str) -> None:
    parsed = urllib.parse.unquote(raw_url).strip()
    rel = ""
    for prefix in ("cosplaydad://open/", "cosplaydad://", "cosplaydad:"):
        if parsed.lower().startswith(prefix):
            rel = parsed[len(prefix) :].strip("/\\")
            break

    target = (DRIVE_ROOT / Path(rel)).resolve()
    root_res = DRIVE_ROOT.resolve()
    if root_res in target.parents or target == root_res:
        if target.exists():
            os.startfile(str(target))
        elif target.parent.exists():
            os.startfile(str(target.parent))
        else:
            os.startfile(str(root_res))


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        if sys.argv[1] == "--register":
            register_protocol()
        else:
            handle_url(sys.argv[1])
    else:
        register_protocol()

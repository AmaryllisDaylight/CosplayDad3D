# @cosplaydad3d Laptop Handoff & Complete System Guide

> **For the Laptop Antigravity Agent**: Read this file and `.antigravityrules` first! This repo (`CosplayDad3D`) and the synced Google Drive directory (`!cosplaydad3d`) contain the complete, zero-API automated content & 3D model pipeline for **@cosplaydad3d** (Kevin McKinney).

---

## 1. Quick Laptop Setup (60 Seconds)

1. **Make sure Google Drive for Desktop is signed in** so `!cosplaydad3d` is mounted (the scripts in `scripts/path_config.py` automatically find `!cosplaydad3d` across any drive letter `C:`–`Z:` or user folder).
2. **Clone this repo** (or open `!cosplaydad3d\00_System_Scripts_And_Repo` directly in Antigravity):
   ```powershell
   git clone https://github.com/AmaryllisDaylight/CosplayDad3D.git c:\P\CosplayDad3D
   ```
3. **Install the two Python packages & register the `📂 Open IG Folder` protocol handler** on the laptop:
   ```powershell
   pip install pillow pillow-heif
   python c:\P\CosplayDad3D\scripts\open_folder_protocol.py --register
   ```
4. *(Optional — only needed if deploying to Firebase Hosting from the laptop)*:
   Clone `https://github.com/AmaryllisDaylight/Duoprompt.git` to `c:\P\DP` and make sure `firebase-tools` is logged in (`firebase login`).

---

## 2. Architecture & Where Everything Lives

### A. Google Drive (`!cosplaydad3d/`) — Auto-Detected via `scripts/path_config.py`
- **`00_System_Scripts_And_Repo/`** — Full mirror of this GitHub repository (`scripts/`, `.antigravityrules`, `WORKFLOW.md`, `LAPTOP_HANDOFF.md`) so the laptop always has the code even without Git.
- **`01_Inbox_Drop/`** — Drop zone for raw iPhone photos (`.HEIC` / `.jpg`), videos (`.MOV` / `.mp4`), AI paint concepts, 4-pose turnaround images, and raw Tripo `.stl` / sculpted `.blend` / `.3mf` files.
- **`02_Ready_To_Post/`** — Active social batches (`Batch_01_...` through `Batch_14_...`). Each batch has:
  - `Instagram_Carousel/` — `1440×1800` (4:5) `.jpg` slides and `864×1080` (4:5) web-ready H.264 `.mp4` videos (`01_Hero.jpg`, `02_Slide.jpg`, etc.).
  - `MakerWorld/` — Full-resolution photos and `9:16` Reels (`720×1280` H.264 `.mp4`).
  - `POST_COPY.md` — Title, Category, Designer Credit, Review Status, Posted Dates/Platforms, short Instagram caption, and MakerWorld Make/Build note.
- **`03_Posted_Archive/`** — Archived batches after they have been marked Posted (`IG Only`, `MW Only`, or `Both`).
- **`04_MakerWorld_Models/`** — 7-Stage Product Library for original 3D printable designs (`MW_01` through `MW_09`):
  - `01_4Pose_Turnarounds/` — 1024×1024 RGB JPEG orthographic Front, Back, Left, and Right views for Tripo AI.
  - `02_Paint_And_Finish_Concepts/` — AI paint-job concepts, lighting videos, and Tripo screen previews.
  - `03_Tripo_Raw_90MB/` — Raw ~90MB high-density `.stl` / `.glb` (`>500,000` triangles — never upload to MakerWorld).
  - `04_Blender_Working/` — High-poly sculpted `.blend` and auto-decimated `_B_Decimated_280k.blend`.
  - `05_Final_STL_Under500k/` — ✅ **UPLOAD THIS STL**: Decimated `280,000`-triangle (`13.35 MB`) `EmberCore_*_v1.stl`.
  - `06_Bambu_3MF_Profile/` — ✅ **UPLOAD THIS 3MF**: Sliced Bambu Studio `EmberCore_*_Profile.3mf`.
  - `07_Real_Print_Photos/` — ✅ **UPLOAD THESE PICS**: Physical print Cover Image + headless Blender studio clay render (`02_*_MatCap_Clay_Render.jpg`).
  - `MODEL_LISTING.md` — Ready-to-copy MakerWorld Title, Tags, Upload Checklist & Description.
- **`05_Concept_Vault_And_Lookbooks/`** — Organized vault for AI concepts and 4-pose turnaround sheets (`01_Unsorted_Concept_Drop/`, `02_EmberCore_Paint_And_Glow_Concepts/`, `03_Weapon_And_Prop_Concepts/`, `04_4Pose_Character_Sheets/`).
- **`99_Raw_Originals_Backup/`** — Numbered descriptive `.jpg` and `.mp4`/`.MOV` backups (`01_...` through `80_...`), plus `_Vetoed_Archive/`. **Zero `.HEIC` retention policy**: `.HEIC` files are converted to `.jpg` and deleted immediately.
- **`CosplayDad_Dashboard.html` & `TRACKER.md`** — Interactive human-review dashboard and markdown status table.

### B. Live Web Dashboard & Cloud Sync (`https://myairotica.web.app/cosplaydad/`)
- Hosted on Firebase project **`myairotica`** (staged via `c:\P\DP\dist\cosplaydad\`, with zero links from the DuoScribe PWA).
- Any clicks made on iPhone or browser (`✕` Veto, `★ #1` Hero promotion, `◀`/`▶` reorder, caption edits, or `Posted Today & Archive`) automatically sync in real time to **Cloud Firestore** (`projects/myairotica/databases/(default)/documents/cosplaydad_sync/review_state`).
- Clicking **`📂 Open IG Folder`** on any batch card (or **`📂 Open Model Folder`** on any MakerWorld card) invokes `cosplaydad://open/...` via `scripts/open_folder_protocol.py` to pop open that exact folder in Windows File Explorer so the user can drag-and-drop photos straight into Instagram or MakerWorld.
- Clicking **`⬇️ Download Slides`** downloads all active (non-vetoed) slides in order (`Batch_14_01_Hero.jpg`, etc.).

---

## 3. Core CLI Commands & Shortcuts

Whenever the user says:
- **`"do it"`** or **`"process inbox"`**:
  1. Run `python scripts/cms_manager.py convert-inbox` (converts `.HEIC` -> `.jpg` & deletes `.HEIC`, extracts 2x2 keyframe sheets for videos, inspects `.stl` triangle counts, and auto-routes/decimates any MakerWorld CAD files).
  2. Visually inspect any new photos/video sheets in `01_Inbox_Drop/` using `read_file`.
  3. Back up originals to `99_Raw_Originals_Backup/`, format 4:5 Instagram slides (`format_for_instagram`) and compact web-ready H.264 `.mp4` videos (`ffmpeg`), update/create `Batch_XX_...` folders or `MW_XX_...` folders, and run:
     ```powershell
     python scripts/cms_manager.py publish-web
     ```
- **`"clean up"`** or **`"apply review"`**:
  Run:
  ```powershell
  python scripts/cms_manager.py apply-review
  ```
  This pulls the latest review clicks directly from Firestore (`myairotica`), moves vetoed slides to `_Vetoed_Archive/`, renumbers surviving slides, moves archived batches to `03_Posted_Archive/`, rebuilds `TRACKER.md` & `CosplayDad_Dashboard.html`, and redeploys to Firebase!
- **`"create the 4 files for front, back, left and right views"`** (when the user uploads a concept armor image):
  1. Center/pad the uploaded front image onto a `1024×1024` pure `#FFFFFF` canvas (`_front.jpg`).
  2. Use the `image-generator` subagent to generate the matching orthographic `1024×1024` `_back.jpg` (concave hollow interior) and `_left.jpg` (90-degree left profile matching the true curvature/depth of the armor piece—e.g. shallow bend for hip/tasset plates vs. deeper dome for shoulder pauldrons), vertically aligned pixel-for-pixel with `_front.jpg`.
  3. Horizontally mirror `_left.jpg` (`ImageOps.mirror`) to create `_right.jpg` for 100% bilateral symmetry in Tripo AI.
  4. Save all 4 files to `05_Concept_Vault_And_Lookbooks/04_4Pose_Character_Sheets/` and the target `MW_XX_.../01_4Pose_Turnarounds/` folder.

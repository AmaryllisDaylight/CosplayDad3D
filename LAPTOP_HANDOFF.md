# @cosplaydad3d Unified System Guide (CMS + MakerWorld 3D Pipeline + Glass Studio)

> **Single Project & Single Dropbox**: `c:\P\CosplayDad3D` (merged with `Gem-image-jpg`) and the synced Google Drive directory (`!cosplaydad3d`) contain the complete, unified 2D-to-3D concept studio, Blender auto-decimation pipeline, MakerWorld product library (`MW_01`–`MW_29+`), and Instagram/MakerWorld dashboard for **@cosplaydad3d** (Kevin McKinney).
>
> **Single Dropbox Rule**: There is only **ONE** Inbox Drop folder across the entire system: **`G:\My Drive\!cosplaydad3d\01_Inbox_Drop\`** (auto-detected on any drive letter via `scripts/path_config.py`).

---

## 1. Quick Laptop Setup (60 Seconds)

1. **Make sure Google Drive for Desktop is signed in** so `!cosplaydad3d` is mounted (the scripts in `scripts/path_config.py` automatically find `!cosplaydad3d` across any drive letter `C:`–`Z:` or user folder, and auto-start `GoogleDriveFS.exe` if needed).
2. **Clone this repo** (or open `!cosplaydad3d\00_System_Scripts_And_Repo` directly in Antigravity):
   ```powershell
   git clone https://github.com/AmaryllisDaylight/CosplayDad3D.git c:\P\CosplayDad3D
   ```
3. **Install Python packages & register the `📂 Open IG Folder` protocol handler**:
   ```powershell
   pip install pillow pillow-heif flask requests python-dotenv
   python c:\P\CosplayDad3D\scripts\open_folder_protocol.py --register
   ```

---

## 2. Architecture & Where Everything Lives

### A. Google Drive (`!cosplaydad3d/`) — Auto-Detected via `scripts/path_config.py`
- **`00_System_Scripts_And_Repo/`** — Full mirror of this GitHub repository (`scripts/`, `.antigravityrules`, `WORKFLOW.md`, `LAPTOP_HANDOFF.md`, `AGENTS.md`).
- **`01_Inbox_Drop/`** — **THE SINGLE UNIFIED DROPBOX** for raw iPhone photos (`.HEIC` / `.jpg` / `.jfif`), videos (`.MOV` / `.mp4`), AI paint concepts, 4-pose turnaround images, and raw Tripo `.stl` / sculpted `.blend` / `.3mf` files. Glass Studio (`📥 Pull .STL`) also saves pulled `.stl` files directly here!
- **`02_Ready_To_Post/`** — Active social batches (`Batch_01_...` through `Batch_15_...`). Each batch has:
  - `Instagram_Carousel/` — `1440×1800` (4:5) `.jpg` slides and `1080×1350` (4:5) web-ready H.264 `.mp4` videos (`01_Hero.jpg`, `02_Slide.jpg`, etc.).
  - `MakerWorld/` — Full-resolution photos and `9:16` Reels (`1080×1920` H.264 `.mp4`).
  - `POST_COPY.md` — Title, Category, Designer Credit, Review Status, Posted Dates/Platforms, short Instagram caption, and MakerWorld Make/Build note.
- **`03_Posted_Archive/`** — Archived batches after they have been marked Posted (`IG Only`, `MW Only`, or `Both`).
- **`04_MakerWorld_Models/`** — 7-Stage Product Library for original 3D printable designs (`MW_01` through `MW_29+`):
  - `01_4Pose_Turnarounds/` — 1024×1024 RGB JPEG orthographic Front, Back, Left, and Right views for Tripo AI.
  - `02_Paint_And_Finish_Concepts/` — 2D clay concepts, AI paint-job concepts, lighting videos, and Tripo screen previews.
  - `03_Tripo_Raw_90MB/` — Raw ~90MB high-density `.stl` / `.glb` (`>500,000` triangles — never upload to MakerWorld).
  - `04_Blender_Working/` — High-poly sculpted `.blend` and auto-decimated `_B_Decimated_280k.blend`.
  - `05_Final_STL_Under500k/` — ✅ **UPLOAD THIS STL**: Decimated `280,000`-triangle (`13.35 MB`) `*_v1.stl`.
  - `06_Bambu_3MF_Profile/` — ✅ **UPLOAD THIS 3MF**: Sliced Bambu Studio `*_Profile.3mf`.
  - `07_Real_Print_Photos/` — ✅ **UPLOAD THESE PICS**: Physical print Cover Image + headless Blender studio clay render (`02_*_MatCap_Clay_Render.jpg`).
  - `MODEL_LISTING.md` — Ready-to-copy MakerWorld Title, Tags, Upload Checklist & Description.
- **`05_Concept_Vault_And_Lookbooks/`** — Organized vault for AI concepts, 4-pose turnaround sheets, and the full `04_Gem_Image_Studio_And_Turnarounds/` backup.
- **`99_Raw_Originals_Backup/`** — Numbered descriptive `.jpg` and `.mp4`/`.MOV` backups (`01_...` through `86_...`), plus `_Vetoed_Archive/`. **Zero `.HEIC`/`.JFIF` retention policy**: `.HEIC` and `.JFIF` files are converted to `.jpg` and deleted immediately.
- **`CosplayDad_Dashboard.html` & `TRACKER.md`** — Interactive human-review dashboard and markdown status table.

### B. CosplayDad3D Glass Studio (`c:\P\CosplayDad3D\gem_image_studio\` & `Launch_Glass_Studio.bat`)
- Launch via `c:\P\CosplayDad3D\Launch_Glass_Studio.bat` (`http://127.0.0.1:5050`).
- Houses the 2D concept libraries (`Embercore Armor/`, `filigree staff/`, `Fantasy_Weapons_and_Bracer/`, `Holiday_Ornaments/`, `Trending_Hero_Props/`).
- Stages 1-image or 4-view sets for **Tripo Web Studio** (`https://studio.tripo3d.ai`, using the 3,000 monthly Web Studio subscription credits) and copies `.stl` files pulled via **`📥 Pull .STL`** directly into **`!cosplaydad3d\01_Inbox_Drop\`** so `"process inbox"` picks them up automatically!

### C. Strict Visual Rules When Generating New 2D Concepts for Tripo 3D
1. **Matte Grey Clay on Pure White Background ONLY (`#FFFFFF`)**:
   - Every generated Tripo input image MUST be an **untextured matte neutral grey 3D clay/resin print model** isolated on a **100% solid pure white studio background (`#FFFFFF`)**.
2. **True Openwork Filigree (Light-Passthrough)**:
   - Openwork armor and staff sleeves must be **hollow perforated cages/sleeves with complete through-holes** (where the white background is clearly visible through the cutouts) so internal LEDs shine through.
3. **Elongated Staff Tube Geometry (`filigree staff/05_Elongated_LED_Tubes`)**:
   - Tall vertical cylinders (`3.5:1` to `4:1` height-to-diameter ratio) with smooth solid cylindrical connection collars (`8–10mm` tall) at the top and bottom.
4. **Wearable Armor Interior Geometry**:
   - Single-sided wearable shells (bracers, cuirasses, pauldrons, tassets) must have a **smooth anatomical concave interior shell** on the `_back.jpg` view.

### D. Live Web Dashboard & Cloud Sync (`https://myairotica.web.app/cosplaydad/`)
- Hosted on Firebase project **`myairotica`** (staged via `c:\P\DP\dist\cosplaydad\`, with zero links from the DuoScribe PWA).
- Any clicks made on iPhone or browser (`✕` Veto, `★ #1` Hero promotion, `◀`/`▶` reorder, caption edits, or `Posted Today & Archive`) automatically sync in real time to **Cloud Firestore** (`projects/myairotica/databases/(default)/documents/cosplaydad_sync/review_state`).
- Clicking **`📂 Open IG Folder`** on any batch card (or **`📂 Open Model Folder`** / **`📂 Open Final STL`** on any MakerWorld card) invokes `cosplaydad://open/...` via `scripts/open_folder_protocol.py` to pop open that exact folder in Windows File Explorer.

---

## 3. Core CLI Commands & Shortcuts

Whenever the user says:
- **`"do it"`** or **`"process inbox"`**:
  1. Run `python scripts/cms_manager.py convert-inbox` (converts `.HEIC`/`.JFIF` -> `.jpg` & deletes originals, extracts 2x2 keyframe sheets for videos, inspects `.stl` triangle counts, and auto-routes/decimates any MakerWorld CAD files in headless Blender 5.2).
  2. Visually inspect any new photos/video sheets or clay renders using `read_file`.
  3. Back up originals to `99_Raw_Originals_Backup/`, format 4:5 Instagram slides (`format_for_instagram`) and compact web-ready H.264 `.mp4` videos (`ffmpeg`), update/create `Batch_XX_...` folders or `MW_XX_...` folders (`write_updated_post_copy` / `MODEL_LISTING.md`), and run:
     ```powershell
     python scripts/cms_manager.py publish-web
     ```
- **`"clean up"`** or **`"apply review"`**:
  Run:
  ```powershell
  python scripts/cms_manager.py apply-review
  ```
- **`"create the 4 files for front, back, left and right views"`**:
  Center/pad the front image onto a `1024×1024` pure `#FFFFFF` canvas (`_front.jpg`), generate matching orthographic `_back.jpg` (concave interior) and `_left.jpg` (true profile curvature) aligned pixel-for-pixel, mirror `_left.jpg` to `_right.jpg`, and save to `01_4Pose_Turnarounds/`.

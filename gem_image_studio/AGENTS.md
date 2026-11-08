# Antigravity Project Instructions — CosplayDad3D Glass Studio, Embercore Armor & Filigree Staff

When opening this repository on any machine (desktop or laptop), Antigravity automatically loads this `AGENTS.md` file to maintain full context across sessions.

---

## 1. Project Overview & Workflow

This workspace powers **CosplayDad3D's** 3D-printable cosplay armor and prop pipeline:
1. **Generate / Curate Concept Images**: Antigravity generates orthographic concept renders (or the user drops images from Gemini/Grok into the project).
2. **Auto-Convert & Organize**: All images are converted to high-quality `.jpg` (`95%` quality) and organized by collection.
3. **CosplayDad3D Glass Studio (`http://127.0.0.1:5050`)**: Local Flask web app (`app.py`) with a glassmorphism UI to browse folders, inspect/zoom images in a lightbox, and send **1-Image** or **4-View (`Front`, `Back`, `Left`, `Right`)** sets to **Tripo 3D** to produce `.STL` files.

### Launching the App
- Run `.\start.bat` (PowerShell) or `start.bat` (CMD / Explorer).
- On a new laptop, `start.bat` automatically creates `.venv` and installs `requirements.txt` on first run, then opens `http://127.0.0.1:5050`.

---

## 2. Directory Structure

- **`Embercore Armor/`** — All filigree armor sets designed with **openwork cutouts that allow internal LED light to pass through**:
  - `01_Cuirass_Chest_Armor/`
    - `01_Openwork_Skull_Cuirass/` — Openwork filigree skull chestplate (`front`, `back`, `left`)
    - `02_Concave_Shell_Skull_Cuirass_4View/` — 4-view Gothic skull cuirass with smooth anatomical concave interior shell
    - `03_Openwork_Corset_Cuirass_4View/` — 4-view openwork filigree torso armor
  - `02_Pauldrons_Shoulders/`
    - `01_3Tier_Embercore_Pauldron_4View/` — 3-tier openwork pauldron 4-view set
    - `02_4Tier_Embercore_Pauldron_4View/` — 4-tier openwork pauldron 4-view sets
    - `03_Feathered_Scale_Pauldrons/` — Feathered scale & scrollwork shoulder armor sets
  - `03_Bracers_Forearms/`
    - `01_Single_Sided_Embercore_Bracer_4View/` — Single-sided open-C forearm bracer 4-view set
    - `02_Bracer_Variants_and_Renders/` — Mesh-backed and metallic bracer variants
  - `04_Tassets_and_Shields/` — Openwork skull tassets and shield emblems
- **`filigree staff/`** — Modular 3D-printable filigree staff sections:
  - `00_Inspiration_References/` — 20 original `.jpg` reference concepts
  - `01_Heads/` (5 staff toppers), `02_Shaft_Sections/` (15 solid-core shaft sections), `03_Finales/` (5 butt caps)
  - `04_Hollow_LED_Openwork/` — Hollow openwork lantern heads, sleeves, and vented finales
  - `05_Elongated_LED_Tubes/` — **Primary active staff tube collection**: 20 elongated (`tall_tube_01` to `tall_tube_20`) hollow openwork filigree tubes, including 10 helical/spiral twist designs (`tall_tube_11` to `tall_tube_20`)
- **`Cosplay Portfolio & Builds/`** — 30 workshop photos of printed builds + character/prop concepts
- **`Tripo_Web_Staging/`** — Staging folder (`00_CURRENT_ACTIVE_BATCH`) for dragging/pasting into Tripo Web Studio
- **`output_stl/`** — Destination folder for generated `.STL` and `.GLB` 3D print meshes

---

## 3. Strict Visual Rules for Generating New Images

Whenever the user asks you to generate new **Filigree Staff** or **Embercore Armor** images for Tripo 3D:
1. **Matte Grey Clay on Pure White Background ONLY**:
   - Every generated image MUST be an **untextured matte neutral grey 3D clay/resin print model** isolated on a **100% solid pure white studio background (`#FFFFFF`)**.
   - Never use dark backgrounds, glowing colored LED effects, metallic paints, or dramatic shadows.
2. **True Openwork Filigree (Light-Passthrough)**:
   - Designs must be **hollow perforated cages/sleeves with complete through-holes** (where the white background is clearly visible through the cutouts and out the opposite wall) so physical LED strips placed inside the 3D print will shine through.
3. **Elongated Staff Tube Geometry (`05_Elongated_LED_Tubes` style)**:
   - Tall, slender vertical cylinders (`3.5:1` to `4:1` height-to-diameter ratio).
   - **Smooth solid cylindrical collar rings** at the very top and bottom (`8–10mm` tall) so modular sections can mate via internal dowel/PVC/acrylic light-pipe sleeves.
   - Thick structural primary ribs (`4–5mm` wall thickness) framing recessed secondary scrollwork, with `45°+` self-supporting teardrop/lancet/chevron/helix cutouts for support-free vertical FDM printing.
4. **Wearable Armor Interior Geometry**:
   - Single-sided wearable shells (bracers, cuirasses, pauldrons) must have a **smooth anatomical concave interior shell** (smooth inside to rest comfortably against chest/forearm padding, never a solid block or double-sided front-cloned-to-back).

---

## 4. Tripo 3D Integration (Web Studio Staging vs. Direct API)

### Why Two Modes Exist
- The user has a **3,000 credits/month subscription on Tripo Web Studio** (`https://studio.tripo3d.ai`).
- Tripo keeps **Web Studio subscription credits** completely separate from **Developer API credits** (`https://platform.tripo3d.ai/billing`).
- Therefore:
  1. **Web Studio Staging (`POST /api/tripo/stage-web`)** is the primary zero-extra-cost workflow: it copies selected 1-image or 4-view files (`01_FRONT_...`, `02_LEFT_...`, `03_BACK_...`, `04_RIGHT_...`) into `Tripo_Web_Staging/00_CURRENT_ACTIVE_BATCH`, copies them to the Windows Clipboard (`Ctrl+V`), opens Explorer + `studio.tripo3d.ai`, and lets the user click **`📥 Pull .STL`** (`POST /api/tripo/pull-stl/<job_id>`) to automatically import downloaded `.stl` files from `~/Downloads` into `output_stl/`.
  2. **Direct API (`POST /api/tripo/generate` via `tripo_client.py`)** uses `https://openapi.tripo3d.ai/v3` (`/v3/account/balance`, `/v3/files`, `/v3/generation/image-to-model`, `/v3/generation/multiview-to-model`, `/v3/models/convert`, `/v3/tasks/{task_id}`). Requires `TRIPO_API_KEY` in `.env` (or `~/.env`).

---

## 5. Google Drive Backup & Cloud IDs

The user's Google Drive is accessible via the `gdrive` skill:
- **Master Drive Folder (`!cosplaydad3d`)**: `1Wd5aeKXJZeu-oWH0hxysKtpqj2poSDYl`
- **Glass Studio & Filigree Staff Drive Folder (`06_Glass_Studio_and_Filigree_Staff`)**: `131wHVgIro7BwQEcfsOJpKGyEjF3nHlvM`
- **Full Portable Laptop Zip Bundle (includes `.env`)**: `1LGfWUgQRXRx0xYsu-CR7JeTVsw8Z0F_a` (`CosplayDad3D_Glass_Studio_Laptop_Bundle.zip`)
- **Ready for Tripo Single-Sided Bracer Folder**: `1iI0wVW0dbLRxDIVwVg0EPKACJfK0FgNH`

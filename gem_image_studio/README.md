# CosplayDad3D Glass Studio — Embercore Armor & Filigree Staff Hub

A local glassmorphism web application (`http://127.0.0.1:5050`) for browsing cosplay 3D print concept folders, inspecting & zooming high-resolution `.jpg` orthographics, auto-converting incoming images (`.jfif`, `.png`, `.webp`, `.heic`) to `.jpg`, and staging or sending **1-Image** or **4-View (`Front`, `Back`, `Left`, `Right`)** sets to **Tripo 3D** to produce `.STL` files.

---

## Quick Start (Desktop or Laptop)

1. Clone this repository (or download from Google Drive `!cosplaydad3d`).
2. Run [`start.bat`](./start.bat) from PowerShell (`.\start.bat`), Command Prompt (`start.bat`), or by double-clicking it:
   - **First-Time Laptop Run:** If `.venv` does not exist yet, `start.bat` automatically creates the Python virtual environment and installs [`requirements.txt`](./requirements.txt).
   - Starts the local server and opens **http://127.0.0.1:5050** in your browser.

---

## Project Folder Structure

- **[`Embercore Armor/`](./Embercore%20Armor)** — Light-passthrough openwork filigree armor sets:
  - `01_Cuirass_Chest_Armor/` — Openwork Skull Cuirass, Concave Shell Skull Cuirass (4-View), and Openwork Corset Cuirass (4-View)
  - `02_Pauldrons_Shoulders/` — 3-Tier & 4-Tier Embercore Pauldron 4-Views and Feathered Scale Pauldrons
  - `03_Bracers_Forearms/` — Single-Sided Embercore Forearm Bracer (4-View) & Variants
  - `04_Tassets_and_Shields/` — Openwork Skull Tassets & Shield Plates
- **[`filigree staff/`](./filigree%20staff)** — Modular LED-illuminated filigree staff sections:
  - `00_Inspiration_References/` — 20 reference `.jpg` images
  - `01_Heads/`, `02_Shaft_Sections/`, `03_Finales/`
  - `04_Hollow_LED_Openwork/` — Vented sleeves, lantern heads, and slotted finales
  - `05_Elongated_LED_Tubes/` — 20 elongated & helix-twist hollow LED staff tubes
- **[`Cosplay Portfolio & Builds/`](./Cosplay%20Portfolio%20&%20Builds)** — 30 workshop build photos & prop concepts
- **`Tripo_Web_Staging/`** — Auto-managed staging directory for Tripo Web Studio (`00_CURRENT_ACTIVE_BATCH`)
- **`output_stl/`** — Destination folder for downloaded `.STL` / `.GLB` 3D print files (sync this folder with Google Drive for large `.stl` meshes)

---

## Tripo 3D Workflows

### Option A: Tripo Web Studio Staging (Uses Your 3,000 Monthly Web Credits)
1. Select 1 image (or assign `Front`, `Back`, `Left`, `Right` in **4-View Mode**).
2. Click **"Stage & Open Tripo Web (3000 Cr Sub)"**.
3. The app copies the image(s) to your Windows Clipboard (`Ctrl+V`), stages numbered `.jpg` files in `Tripo_Web_Staging/00_CURRENT_ACTIVE_BATCH`, opens that folder in Explorer, and launches [studio.tripo3d.ai](https://studio.tripo3d.ai).
4. Once you download the `.stl` from Tripo Web Studio, click **`📥 Pull .STL`** on the job card in the right sidebar to automatically rename and move it from `Downloads` into `output_stl/`.

### Option B: Direct Tripo v3 API
1. Copy `.env.example` to `.env` and add your `TRIPO_API_KEY=tsk_...`.
2. Click **"Direct API → Generate .STL"** to run image upload, 3D generation, and `.STL` conversion automatically in the background.

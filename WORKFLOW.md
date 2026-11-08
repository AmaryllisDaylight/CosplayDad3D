# @cosplaydad3d Content Management System — Workflow Guide

Everything runs locally between `c:\P\CosplayDad3d` and `G:\My Drive\!cosplaydad3d` with **zero external AI APIs** and **zero `.HEIC` files kept**.

---

## Complete Folder Architecture in `G:\My Drive\!cosplaydad3d`

```text
G:\My Drive\!cosplaydad3d\
├── 01_Inbox_Drop\                     # Drop ANY photos, videos, concepts, .stl, .blend, or .3mf here
├── 02_Ready_To_Post\                  # 📸 Active Social Queue (Batch_01..Batch_09)
├── 03_Posted_Archive\                 # 📦 Archived Social Posts (with IG/MW date stamps)
│
├── 04_MakerWorld_Models\              # 🟢 Original 3D Printable Designs (7-Stage Pipeline)
│   └── MW_01_Elven_Filigree_Pauldron\
│       ├── 01_4Pose_Turnarounds\          # 4-view images fed into Tripo AI
│       ├── 02_Paint_And_Finish_Concepts\  # 🎨 AI paint-job styling, colorways & concept videos
│       ├── 03_Tripo_Raw_90MB\             # Raw ~90MB .stl from Tripo (>500k tris — DO NOT UPLOAD)
│       ├── 04_Blender_Working\            # Sculpted_HighPoly.blend + Decimated_500k.blend
│       ├── 05_Final_STL_Under500k\        # ✅ UPLOAD THIS STL (<500k tris, ~15-24 MB)
│       ├── 06_Bambu_3MF_Profile\          # ✅ UPLOAD THIS 3MF (Bambu Studio sliced profile)
│       ├── 07_Real_Print_Photos\          # ✅ UPLOAD THESE PICS (Physical print proof)
│       └── MODEL_LISTING.md               # MakerWorld Title, Print Settings & Description
│
├── 05_Concept_Vault_And_Lookbooks\    # 🎨 Bulk Vault for ~100+ AI Paint & Prop Concepts
│   ├── 01_Unsorted_Concept_Drop\
│   ├── 02_Armor_Paint_And_Finish_Ideas\
│   ├── 03_Weapon_And_Prop_Concepts\
│   └── 04_4Pose_Character_Sheets\
│
└── 99_Raw_Originals_Backup\           # Master .jpg & video backup (zero .HEICs)
```

---

## Automatic `.STL` Triangle-Count Routing (`mw_pipeline.py`)

When you drop `.stl`, `.blend`, or `.3mf` files and tell Antigravity **`"do it"`**:
- `inspect_stl_file()` reads the binary `.stl` header in 1 millisecond:
  - **`> 500,000` triangles (~90 MB Tripo raw export)** → automatically routed to `03_Tripo_Raw_90MB/`.
  - **`<= 500,000` triangles (~15–24 MB Blender decimated export)** → automatically routed to `05_Final_STL_Under500k/`.
- `.blend` files go to `04_Blender_Working/`, and `.3mf` files go to `06_Bambu_3MF_Profile/`.

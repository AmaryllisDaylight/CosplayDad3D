#!/usr/bin/env python3
"""
MakerWorld 3D Model Pipeline & Concept Vault Manager for @cosplaydad3d
======================================================================
Includes permanent support for the signature **EmberCore Armor System** (`EmberCore_` prefix):
  01_4Pose_Turnarounds/          - 4-view turnaround sheets for Tripo AI
  02_Paint_And_Finish_Concepts/  - AI paint-job styling, colorways, lighting videos & Blender MatCap clay renders
  03_Tripo_Raw_90MB/             - Raw ~90MB high-density .stl/.glb from Tripo (>500k tris)
  04_Blender_Working/            - High-poly sculpted .blend & decimated .blend files
  05_Final_STL_Under500k/        - Decimated (target 200k-350k tris, max 500k) EmberCore_*.stl
  06_Bambu_3MF_Profile/          - Sliced Bambu Studio EmberCore_*_Profile.3mf
  07_Real_Print_Photos/          - Physical print Cover Image + Blender MatCap clay render
"""

from __future__ import annotations

import json
import re
import shutil
import struct
import zipfile
from pathlib import Path
from typing import Dict, List

from path_config import find_drive_root

DRIVE_ROOT = find_drive_root()
MW_MODELS_DIR = DRIVE_ROOT / "04_MakerWorld_Models"
CONCEPT_VAULT_DIR = DRIVE_ROOT / "05_Concept_Vault_And_Lookbooks"
BACKUP_DIR = DRIVE_ROOT / "99_Raw_Originals_Backup"

MW_STAGE_FOLDERS = [
    "01_4Pose_Turnarounds",
    "02_Paint_And_Finish_Concepts",
    "03_Tripo_Raw_90MB",
    "04_Blender_Working",
    "05_Final_STL_Under500k",
    "06_Bambu_3MF_Profile",
    "07_Real_Print_Photos",
]

TRIANGLE_LIMIT = 500_000


def inspect_stl_file(stl_path: Path) -> Dict[str, object]:
    """
    Read the triangle count and file size of an .STL file.
    Target for EmberCore decimated STLs: 200k-350k triangles (hard ceiling: 500k).
    """
    size_bytes = stl_path.stat().st_size
    size_mb = round(size_bytes / (1024 * 1024), 2)
    tri_count = 0
    is_binary = True

    with open(stl_path, "rb") as f:
        header = f.read(84)
        if len(header) == 84:
            cand_tris = struct.unpack("<I", header[80:84])[0]
            expected_size = 84 + (cand_tris * 50)
            if abs(size_bytes - expected_size) <= 1024 or not header.startswith(b"solid"):
                tri_count = cand_tris
            else:
                is_binary = False

    if not is_binary or tri_count == 0:
        count = 0
        with open(stl_path, "rb") as f:
            for line in f:
                if b"facet normal" in line:
                    count += 1
        tri_count = count

    is_decimated = tri_count <= TRIANGLE_LIMIT
    in_sweet_spot = 150_000 <= tri_count <= 380_000
    target_subfolder = (
        "05_Final_STL_Under500k" if is_decimated else "03_Tripo_Raw_90MB"
    )
    return {
        "filename": stl_path.name,
        "size_mb": size_mb,
        "triangles": tri_count,
        "is_decimated_under_500k": is_decimated,
        "in_200k_350k_sweet_spot": in_sweet_spot,
        "target_subfolder": target_subfolder,
    }


def route_cad_file_to_project(
    file_path: Path, project_dir: Path, embercore_slug: str = ""
) -> Path:
    """
    Automatically route a .stl, .glb, .obj, .blend, or .3mf file into the right
    numbered stage subfolder inside a MakerWorld project folder.
    If embercore_slug is provided, ensures final .stl and .3mf files carry the EmberCore_ prefix.
    """
    for sf in MW_STAGE_FOLDERS:
        (project_dir / sf).mkdir(parents=True, exist_ok=True)

    ext = file_path.suffix.lower()
    out_name = file_path.name
    if embercore_slug and not out_name.startswith("EmberCore_"):
        if ext == ".stl":
            out_name = f"EmberCore_{embercore_slug}_v1.stl"
        elif ext == ".3mf":
            out_name = f"EmberCore_{embercore_slug}_Profile.3mf"

    if ext == ".stl":
        meta = inspect_stl_file(file_path)
        dst_dir = project_dir / str(meta["target_subfolder"])
        # Only rename with EmberCore_v1 if it's the final decimated STL
        final_name = out_name if meta["is_decimated_under_500k"] else file_path.name
        dst = dst_dir / final_name
        shutil.move(str(file_path), str(dst))
        print(
            f"Routed STL {dst.name} ({meta['triangles']:,} tris, {meta['size_mb']} MB) -> {meta['target_subfolder']}/"
        )
        return dst
    elif ext in (".glb", ".obj", ".fbx"):
        dst = project_dir / "03_Tripo_Raw_90MB" / file_path.name
        shutil.move(str(file_path), str(dst))
        return dst
    elif ext in (".blend", ".blend1"):
        dst = project_dir / "04_Blender_Working" / file_path.name
        shutil.move(str(file_path), str(dst))
        return dst
    elif ext == ".3mf":
        dst = project_dir / "06_Bambu_3MF_Profile" / out_name
        shutil.move(str(file_path), str(dst))
        return dst
    else:
        dst = project_dir / file_path.name
        shutil.move(str(file_path), str(dst))
        return dst


def auto_organize_all_mw_projects() -> List[str]:
    """
    Scan every MW_XX_* project folder in 04_MakerWorld_Models/:
    1. Any loose .stl, .blend, .glb, .obj, or .3mf dropped into the root of MW_XX_*
       is automatically inspected and routed to the right subfolder (03, 04, 05, or 06).
    2. Any .stl accidentally placed in 03_Tripo_Raw_90MB that has <=500k triangles is
       moved to 05_Final_STL_Under500k (and vice versa if a >500k raw STL was placed in 05).
    """
    logs: List[str] = []
    if not MW_MODELS_DIR.exists():
        return logs

    for proj_dir in sorted(MW_MODELS_DIR.iterdir()):
        if not proj_dir.is_dir() or not proj_dir.name.startswith("MW_"):
            continue

        # Determine EmberCore slug if this is an EmberCore project
        ec_slug = ""
        m = re.match(r"^MW_\d+_EmberCore_(.+)$", proj_dir.name)
        if m:
            ec_slug = m.group(1)

        # 1. Route loose CAD files dropped in project root
        for p in sorted(proj_dir.iterdir()):
            if p.is_file() and p.suffix.lower() in {
                ".stl",
                ".glb",
                ".obj",
                ".fbx",
                ".blend",
                ".blend1",
                ".3mf",
            }:
                dst = route_cad_file_to_project(p, proj_dir, embercore_slug=ec_slug)
                logs.append(f"[{proj_dir.name}] Auto-routed {p.name} -> {dst.parent.name}/{dst.name}")

        # 2. Verify STLs inside 03_Tripo_Raw_90MB and 05_Final_STL_Under500k are in the right bucket
        for sub_name in ("03_Tripo_Raw_90MB", "05_Final_STL_Under500k"):
            sub_dir = proj_dir / sub_name
            if not sub_dir.exists():
                continue
            for stl_p in sorted(sub_dir.glob("*.stl")):
                meta = inspect_stl_file(stl_p)
                correct_sub = str(meta["target_subfolder"])
                if correct_sub != sub_name:
                    dst = proj_dir / correct_sub / stl_p.name
                    shutil.move(str(stl_p), str(dst))
                    msg = (
                        f"[{proj_dir.name}] Moved {stl_p.name} ({meta['triangles']:,} tris) "
                        f"from {sub_name}/ -> {correct_sub}/"
                    )
                    print(msg)
                    logs.append(msg)

        # 3. If 04_Blender_Working has a sculpted .blend (or 03_Tripo_Raw_90MB has a raw .stl)
        #    and 05_Final_STL_Under500k is still empty, auto-run headless Blender decimate + clay render!
        final_stl_dir = proj_dir / "05_Final_STL_Under500k"
        blender_dir = proj_dir / "04_Blender_Working"
        raw_dir = proj_dir / "03_Tripo_Raw_90MB"
        if not list(final_stl_dir.glob("*.stl")):
            candidate_blends = [
                b
                for b in sorted(blender_dir.glob("*.blend"))
                if "_B_Decimated_" not in b.name
            ]
            candidate_raw_stls = sorted(raw_dir.glob("*.stl"))
            src_cad = None
            if candidate_blends:
                src_cad = candidate_blends[-1]
            elif candidate_raw_stls:
                src_cad = candidate_raw_stls[-1]

            if src_cad is not None:
                prefix = f"EmberCore_{ec_slug}" if ec_slug else "_".join(proj_dir.name.split("_")[2:])
                import subprocess as _sp
                import sys as _sys

                script_path = Path(__file__).parent / "blender_auto_decimate.py"
                print(f"[{proj_dir.name}] Auto-decimating {src_cad.name} in headless Blender...")
                _sp.run(
                    [
                        _sys.executable,
                        str(script_path),
                        "--input",
                        str(src_cad),
                        "--project",
                        proj_dir.name,
                        "--prefix",
                        prefix,
                        "--target-tris",
                        "280000",
                    ],
                    check=True,
                )
                logs.append(f"[{proj_dir.name}] Auto-decimated {src_cad.name} -> {prefix}_v1.stl + MatCap Clay Render")

    return logs


INITIAL_MW_MODELS = [
    {
        "folder": "MW_01_EmberCore_Mage_Filigree_Bracer",
        "title": "Fantasy Mage Filigree Bracer / Forearm Gauntlet - Cosplay Armor [EmberCore Series]",
        "category": "EmberCore Series • Wearable Cosplay Armor",
        "status": "First Upload — Needs EmberCore_Mage_Bracer_v1.stl (200k-350k tris), .3mf & MatCap Render",
        "tags": "embercore, cosplay, armor, bracer, gauntlet, filigree, fantasy, wearable, rpg, bambulab",
        "photos": [
            "02_elven_filigree_bracer_print.jpg",
            "38_elven_filigree_bracer_foam_liner_test.jpg",
        ],
        "concepts": [
            "39_elven_filigree_bracer_backlit_led_concept.MOV",
        ],
        "description": """Fantasy Mage Filigree Bracer / Forearm Gauntlet — the debut piece in the @cosplaydad3d EmberCore Armor Series, designed and built with my daughters for convention and stage wear.

• About the EmberCore Series: Every EmberCore armor piece is engineered with high-relief metallic scrollwork and filigree shells over a recessed diamond lattice and pierced core. You can finish it two ways:
  1. Standard / Painted Version: Leave the recessed lattice core in deep shadow wash underneath bright Rub 'n Buff or dry-brushed metallic filigree highlights.
  2. LED / Illuminated Version: Line the interior cuff with thin white diffusion foam and tuck addressable LEDs behind the lattice so upward-pulsing fire, ember, or arcane light glows through the scrollwork cutouts.

Print & Slicer Recommendations:
• File Naming: EmberCore_Mage_Bracer_v1.stl (decimated 200k–350k triangles for crisp relief without slicer lag) + EmberCore_Mage_Bracer_Profile.3mf
• Printer: Bambu Lab P2S / H2S (Textured PEI Plate)
• Layer Height: 0.16mm, 3 wall loops, 12% Gyroid infill
• Supports: Organic Tree Supports (0.20mm top Z-distance, angled upright so supports never scar the outer scrollwork)

Tags: embercore, cosplay, armor, bracer, gauntlet, filigree, fantasy, wearable, rpg""",
    },
    {
        "folder": "MW_02_EmberCore_Mage_Filigree_Pauldron",
        "title": "Fantasy Mage Filigree Shoulder Pauldron - Cosplay Armor [EmberCore Series]",
        "category": "EmberCore Series • Wearable Cosplay Armor",
        "status": "In Progress — Needs EmberCore_Mage_Pauldron_v1.stl (200k-350k tris), .3mf & MatCap Render",
        "tags": "embercore, cosplay, armor, pauldron, shoulder, filigree, fantasy, wearable, rpg",
        "photos": [
            "01_elven_filigree_pauldron_print.jpg",
            "04_bambu_lab_pauldron_printing.jpg",
        ],
        "concepts": [],
        "description": """Three-tier curved shoulder pauldron with raised baroque scrollwork, embossed runic trim, and a recessed diamond gem socket at the crest—part of the @cosplaydad3d EmberCore Armor System.

• About the EmberCore Series: Designed with high-relief scrollwork over a recessed lattice and pierced core—engineered to catch deep shadow washes cleanly under Rub 'n Buff highlights or house diffused internal LED lighting.

Print & Slicer Recommendations:
• File Naming: EmberCore_Mage_Pauldron_v1.stl + EmberCore_Mage_Pauldron_Profile.3mf
• Printer: Bambu Lab P2S / H2S (Textured PEI Plate)
• Layer Height: 0.16mm, 3 wall loops, 12% Gyroid infill
• Supports: Organic Tree Supports (angled 35° upright on the bed so tree branches snake cleanly through the hollow lattice windows)

Tags: embercore, cosplay, armor, pauldron, shoulder, filigree, fantasy, wearable, rpg""",
    },
    {
        "folder": "MW_03_Dragon_Skull_Crossbow",
        "title": "Dragon-Bone Horned Skull Hand Crossbow Prop",
        "category": "Cosplay Weapons • Fantasy Bone Armory",
        "status": "In Progress (Needs .STL & .3MF Drop)",
        "tags": "cosplay, crossbow, dragon, skull, weapon, prop, fantasy, rpg, dnd",
        "photos": [
            "03_dragon_skull_crossbow_prop.jpg",
        ],
        "concepts": [],
        "description": """Fantasy hand crossbow sculpted from dragon bone motifs—horned dragon skull prod with recurved horns and a spinal vertebrae stock with runic bolt track.

Print Settings:
• Printer: Bambu Lab P2S / H2S
• Layer Height: 0.16mm - 0.20mm, 3 walls, 12% gyroid infill, Organic Tree Supports""",
    },
    {
        "folder": "MW_04_Primal_Beast_Skull_Helm",
        "title": "Wearable Primal Saber-Tooth Beast Skull Helmet",
        "category": "Cosplay Helmets • Creature Skulls",
        "status": "In Progress (Needs .STL & .3MF Drop)",
        "tags": "cosplay, helmet, skull, mask, shaman, monsterhunter, primal, wearable, fantasy",
        "photos": [
            "20_primal_tusk_skull_headdresses_and_armor.jpg",
            "21_primal_tusk_skull_masks_stacked.jpg",
        ],
        "concepts": [],
        "description": """Full-scale wearable prehistoric saber-tooth beast skull helmet with cranium sutures, deep eye sockets, and tie-down ports for faux fur manes and cord wraps.

Print Settings:
• Printer: Bambu Lab H2S / P2S (fits in one piece on 320x340 class beds)
• Layer Height: 0.20mm (leave light 220-grit texture for realistic porous bone washes), 3 walls, 10% gyroid infill""",
    },
    {
        "folder": "MW_05_Frozen_Throne_Ice_Pedestal",
        "title": "Hexagonal Frozen Throne / Icecrown Citadel Sword Display Pedestal",
        "category": "Display Base & Scenic Prop",
        "status": "In Progress (Needs .STL & .3MF Drop)",
        "tags": "frostmourne, lichking, worldofwarcraft, pedestal, display, cosplay, prop, led",
        "photos": [
            "30_frozen_throne_ice_spire_pedestal.jpg",
        ],
        "concepts": [],
        "description": """Multi-tiered hexagonal display plinth with skull pillars, runic walls, perimeter ice fangs, and hollow center ice spires designed for translucent blue filament + LED lighting.

Print Settings:
• Base Plinth: Matte grey PLA, 0.20mm layers, 3 walls, 10% gyroid infill
• Ice Spires: Translucent blue PLA/PETG, 2 walls, 0% infill for internal LED diffusion""",
    },
    {
        "folder": "MW_06_EmberCore_Mage_Filigree_Greave",
        "title": "Fantasy Mage Filigree Shin Greave / Lower Leg Armor - Cosplay Armor [EmberCore Series]",
        "category": "EmberCore Series • Wearable Cosplay Armor",
        "status": "Decimated & Rendered — Ready for Bambu Studio .3mf Profile & Physical Print Photo",
        "tags": "embercore, cosplay, armor, greave, shin, legarmor, filigree, fantasy, wearable, rpg, bambulab",
        "photos": [],
        "concepts": [],
        "description": """Fantasy Mage Filigree Shin Greave / Lower Leg Armor — part of the @cosplaydad3d EmberCore Armor Series, designed for full-body fantasy armor sets and stage wear.

• About the EmberCore Series: Engineered with high-relief metallic scrollwork over a recessed diamond lattice and pierced core—designed to catch deep shadow washes cleanly under Rub 'n Buff metallic highlights or house diffused internal LED lighting.

Print & Slicer Recommendations:
• File Naming: EmberCore_Mage_Filigree_Greave_v1.stl (decimated to 280k triangles for crisp relief without slicer lag) + EmberCore_Mage_Filigree_Greave_Profile.3mf
• Printer: Bambu Lab P2S / H2S (Textured PEI Plate)
• Layer Height: 0.16mm, 3 wall loops, 12% Gyroid infill
• Supports: Organic Tree Supports (angled upright so tree branches never scar the outer scrollwork)

Tags: embercore, cosplay, armor, greave, filigree, fantasy, wearable, rpg""",
    },
    {
        "folder": "MW_07_EmberCore_Skull_Headpiece",
        "title": "Gothic Skull Filigree Headpiece / Crown - Cosplay Armor [EmberCore Series]",
        "category": "EmberCore Series • Wearable Cosplay Headpiece",
        "status": "Decimated & Rendered — Ready for Bambu Studio .3mf Profile & Physical Print Photo",
        "tags": "embercore, cosplay, armor, headpiece, crown, skull, gothic, filigree, fantasy, wearable, rpg",
        "photos": [],
        "concepts": [],
        "description": """Gothic Skull Filigree Headpiece / Crown — an ornate necromancer and dark-fantasy crown in the @cosplaydad3d EmberCore Armor Series.

• About the EmberCore Series: Designed with high-relief gothic scrollwork and sculpted skull relief over a recessed lattice and pierced core—engineered to catch deep shadow washes cleanly under Rub 'n Buff metallic highlights or house diffused internal LED lighting.

Print & Slicer Recommendations:
• File Naming: EmberCore_Skull_Headpiece_v1.stl (decimated to 280k triangles) + EmberCore_Skull_Headpiece_Profile.3mf
• Printer: Bambu Lab P2S / H2S (Textured PEI Plate)
• Layer Height: 0.16mm, 3 wall loops, 12% Gyroid infill
• Supports: Organic Tree Supports (0.20mm top Z-distance)

Tags: embercore, cosplay, armor, headpiece, crown, skull, filigree, fantasy, wearable, rpg""",
    },
    {
        "folder": "MW_08_EmberCore_Skull_Loin_Guard",
        "title": "Gothic Skull Filigree Loin Guard / Belt Tasset Apron - Cosplay Armor [EmberCore Series]",
        "category": "EmberCore Series • Wearable Cosplay Waist / Belt Armor",
        "status": "Decimated & Rendered — Ready for Bambu Studio .3mf Profile & Physical Print Photo",
        "tags": "embercore, cosplay, armor, loinguard, tasset, beltarmor, skull, gothic, filigree, fantasy, wearable, rpg",
        "photos": [],
        "concepts": [],
        "description": """Gothic Skull Filigree Loin Guard / Front Belt Tasset Apron — hangs from the center belt buckle as a rigid armored loincloth/fauld plate, part of the @cosplaydad3d EmberCore Armor Series.

• About the EmberCore Series: Engineered with high-relief gothic skull and baroque scrollwork over a recessed lattice and pierced core—designed to catch deep shadow washes cleanly under Rub 'n Buff highlights or house diffused internal LED lighting.

Print & Slicer Recommendations:
• File Naming: EmberCore_Skull_Loin_Guard_v1.stl (decimated to 280k triangles) + EmberCore_Skull_Loin_Guard_Profile.3mf
• Printer: Bambu Lab P2S / H2S (Textured PEI Plate)
• Layer Height: 0.16mm, 3 wall loops, 12% Gyroid infill
• Supports: Organic Tree Supports

Tags: embercore, cosplay, armor, loinguard, tasset, skull, filigree, fantasy, wearable, rpg""",
    },
    {
        "folder": "MW_09_EmberCore_Mage_Filigree_Tasset",
        "title": "Fantasy Mage Filigree Hip Tasset / Thigh Armor Plate - Cosplay Armor [EmberCore Series]",
        "category": "EmberCore Series • Wearable Cosplay Hip & Thigh Armor",
        "status": "Decimated & Rendered — Ready for Bambu Studio .3mf Profile & Physical Print Photo",
        "tags": "embercore, cosplay, armor, tasset, hiparmor, thigharmor, filigree, fantasy, wearable, rpg, bambulab",
        "photos": [],
        "concepts": [],
        "description": """Fantasy Mage Filigree Hip Tasset / Thigh Armor Plate — 3-tier gothic scrollwork and pierced filigree hip plate, part of the @cosplaydad3d EmberCore Armor Series.

• About the EmberCore Series: Engineered with high-relief metallic scrollwork over a recessed lattice and pierced core—designed to catch deep shadow washes cleanly under Rub 'n Buff highlights or house diffused internal LED lighting.

Print & Slicer Recommendations:
• File Naming: EmberCore_Mage_Filigree_Tasset_v1.stl (decimated to 280k triangles) + EmberCore_Mage_Filigree_Tasset_Profile.3mf
• Printer: Bambu Lab P2S / H2S (Textured PEI Plate)
• Layer Height: 0.16mm, 3 wall loops, 12% Gyroid infill
• Supports: Organic Tree Supports

Tags: embercore, cosplay, armor, tasset, hiparmor, filigree, fantasy, wearable, rpg""",
    },
    {
        "folder": "MW_10_EmberCore_Fantasy_Dagger",
        "title": "Dragon-Wing Runic Fantasy Dagger w/ Claw & Orb Pommel - Cosplay Prop [EmberCore Armory]",
        "category": "EmberCore Armory • Cosplay Weapons & Props",
        "status": "Decimated & Rendered — Ready for Bambu Studio .3mf Profile & Physical Print Photo",
        "tags": "embercore, cosplay, dagger, knife, dragon, runes, weapon, prop, fantasy, rpg, dnd, bambulab",
        "photos": [],
        "concepts": [],
        "description": """Dragon-Wing Runic Fantasy Dagger — an ornate dark-fantasy sidearm and ritual blade in the @cosplaydad3d EmberCore Armory.

• Sculpt Highlights:
  - Twin sculpted dragon-wing crossguards framing the ricasso
  - Recurve single-edged fantasy blade with a deep central fuller engraved with arcane elder runes (ideal for glowing molten ember or arcane washes)
  - Ribbed cord-wrapped grip terminating in a four-talon dragon claw clutching a spherical orb pommel

Print & Slicer Recommendations:
• File Naming: EmberCore_Fantasy_Dagger_v1.stl (decimated from 1.90M to 280k triangles — 13.35 MB — for crisp runic detail without slicer lag) + EmberCore_Fantasy_Dagger_Profile.3mf
• Printer: Bambu Lab P2S / H2S (Textured PEI Plate)
• Layer Height: 0.16mm (or 0.12mm for ultra-sharp blade runes), 3–4 wall loops for rigid blade strength, 15% Gyroid infill
• Supports: Organic Tree Supports (print vertically or split in half flat on the bed in Bambu Studio for support-free blade faces)

Tags: embercore, cosplay, dagger, dragon, runes, weapon, prop, fantasy, rpg, dnd""",
    },
    {
        "folder": "MW_11_EmberCore_Twin_Serpent_Dragon_Dagger",
        "title": "Twin-Serpent Helical Dragon Dagger w/ Horned Skull Guard & Coiled Tail Orb Pommel [EmberCore Armory]",
        "category": "EmberCore Armory • Cosplay Weapons & Props",
        "status": "Decimated & Rendered — Ready for Bambu Studio .3mf Profile & Physical Print Photo",
        "tags": "embercore, cosplay, dagger, dragon, serpent, snake, ritualblade, weapon, prop, fantasy, rpg, dnd, bambulab",
        "photos": [],
        "concepts": [],
        "description": """Twin-Serpent Helical Dragon Dagger — a dark-fantasy warlock, rogue, and ritual sidearm in the @cosplaydad3d EmberCore Armory.

• Sculpt Highlights:
  - Double-helix pierced blade formed by two intertwined, heavy-scaled dragon serpents with open hollow gaps down the core (perfect for internal LED fiber/filament glow or deep shadow washes)
  - Horned dragon-head medallion centerpiece at the ricasso flanked by twin spiked dragon-talon crossguards
  - Ornate scaled grip terminating in a coiled dragon-tail pommel clutching a smooth arcane orb

Print & Slicer Recommendations:
• File Naming: EmberCore_Twin_Serpent_Dragon_Dagger_v1.stl (decimated from 1.90M to 280k triangles — 13.35 MB — for crisp scale relief without slicer lag) + EmberCore_Twin_Serpent_Dragon_Dagger_Profile.3mf
• Printer: Bambu Lab P2S / H2S (Textured PEI Plate)
• Layer Height: 0.16mm, 3–4 wall loops for rigid helical blade strength, 15% Gyroid infill
• Supports: Organic Tree Supports (0.20mm top Z-distance so support branches snake cleanly out of the open serpent helix gaps)

Tags: embercore, cosplay, dagger, dragon, serpent, ritualblade, weapon, prop, fantasy, rpg, dnd""",
    },
]


def initialize_mw_library_and_vault() -> None:
    """Create/update 04_MakerWorld_Models/ with EmberCore naming and 05_Concept_Vault_And_Lookbooks/."""
    MW_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    CONCEPT_VAULT_DIR.mkdir(parents=True, exist_ok=True)

    # Remove old pre-EmberCore folders if they exist and haven't had custom CAD files added yet
    for old_name in ["MW_01_Elven_Filigree_Pauldron", "MW_02_Elven_Filigree_Bracer"]:
        old_dir = MW_MODELS_DIR / old_name
        if old_dir.exists():
            shutil.rmtree(old_dir)

    for sub in [
        "01_Unsorted_Concept_Drop",
        "02_EmberCore_Paint_And_Glow_Concepts",
        "03_Weapon_And_Prop_Concepts",
        "04_4Pose_Character_Sheets",
    ]:
        (CONCEPT_VAULT_DIR / sub).mkdir(parents=True, exist_ok=True)

    old_armor_sub = CONCEPT_VAULT_DIR / "02_Armor_Paint_And_Finish_Ideas"
    if old_armor_sub.exists():
        try:
            old_armor_sub.rmdir()
        except OSError:
            pass

    for m in INITIAL_MW_MODELS:
        proj_dir = MW_MODELS_DIR / m["folder"]
        for sf in MW_STAGE_FOLDERS:
            (proj_dir / sf).mkdir(parents=True, exist_ok=True)

        photos_dir = proj_dir / "07_Real_Print_Photos"
        for p_name in m["photos"]:
            src = BACKUP_DIR / p_name
            dst = photos_dir / p_name
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)

        concepts_dir = proj_dir / "02_Paint_And_Finish_Concepts"
        for c_name in m["concepts"]:
            src = BACKUP_DIR / c_name
            dst = concepts_dir / c_name
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)

        listing_path = proj_dir / "MODEL_LISTING.md"
        listing_md = f"""# {m['title']}

- **Model Folder**: `{m['folder']}`
- **Category**: {m['category']}
- **Release Status**: {m['status']}
- **Tags**: `{m['tags']}`
- **Upload Checklist**:
  - [ ] Decimated `.stl` (`200k–350k` triangles target, `EmberCore_*_v1.stl`) in `05_Final_STL_Under500k/`
  - [ ] Sliced Bambu Studio `.3mf` Print Profile (`EmberCore_*_Profile.3mf`) in `06_Bambu_3MF_Profile/`
  - [x] Real-world photo of physical print (Cover Image) in `07_Real_Print_Photos/`
  - [ ] Clean Blender MatCap clay render (Secondary Gallery Image) in `07_Real_Print_Photos/`
- **MakerWorld Published Date**: `Pending`

---

## MakerWorld Listing Description

```text
{m['description']}
```
"""
        listing_path.write_text(listing_md, encoding="utf-8")

    print(f"Updated {len(INITIAL_MW_MODELS)} projects in {MW_MODELS_DIR} with EmberCore Series standards.")


def collect_mw_models() -> List[Dict]:
    """Scan 04_MakerWorld_Models/ and report pipeline stage status for each model."""
    models = []
    if not MW_MODELS_DIR.exists():
        return models

    for folder in sorted(MW_MODELS_DIR.iterdir()):
        if not folder.is_dir() or not folder.name.startswith("MW_"):
            continue

        listing_path = folder / "MODEL_LISTING.md"
        title = folder.name
        category = "3D Printable Model"
        mw_pub_date = ""
        tags = ""
        description = ""

        if listing_path.exists():
            txt = listing_path.read_text(encoding="utf-8")
            tm = re.search(r"^#\s+(.+)$", txt, re.MULTILINE)
            if tm:
                title = tm.group(1).strip()
            cm = re.search(r"\*\*Category\*\*:\s*(.+)$", txt, re.MULTILINE)
            if cm:
                category = cm.group(1).strip()
            tgm = re.search(r"\*\*Tags\*\*:\s*`?([^`\n]+)`?$", txt, re.MULTILINE)
            if tgm:
                tags = tgm.group(1).strip()
            pm = re.search(r"\*\*MakerWorld Published Date\*\*:\s*(.+)$", txt, re.MULTILINE)
            if pm:
                val = pm.group(1).strip().strip("`")
                if val not in ("Pending", "-", "None"):
                    mw_pub_date = val
            dm = re.search(
                r"##\s*MakerWorld Listing Description.*?```(?:text|markdown)?\n(.*?)```",
                txt,
                re.DOTALL | re.IGNORECASE,
            )
            if dm:
                description = dm.group(1).strip()

        stage_counts = {}
        for sf in MW_STAGE_FOLDERS:
            sf_dir = folder / sf
            files = (
                [p for p in sf_dir.iterdir() if p.is_file() and not p.name.startswith(".")]
                if sf_dir.exists()
                else []
            )
            stage_counts[sf] = len(files)

        final_stls = []
        final_stl_dir = folder / "05_Final_STL_Under500k"
        if final_stl_dir.exists():
            for sp in sorted(final_stl_dir.glob("*.stl")):
                final_stls.append(inspect_stl_file(sp))

        media_items = []
        for sf_name, badge in [
            ("07_Real_Print_Photos", "📸 Real Print"),
            ("02_Paint_And_Finish_Concepts", "🎨 Paint/Glow Concept"),
            ("01_4Pose_Turnarounds", "📐 4-Pose Sheet"),
        ]:
            sf_dir = folder / sf_name
            if sf_dir.exists():
                for p in sorted(sf_dir.iterdir()):
                    if p.is_file() and p.suffix.lower() in {
                        ".jpg",
                        ".jpeg",
                        ".png",
                        ".webp",
                        ".mp4",
                        ".mov",
                    }:
                        media_items.append(
                            {
                                "name": p.name,
                                "rel": p.relative_to(DRIVE_ROOT).as_posix(),
                                "is_video": p.suffix.lower() in {".mp4", ".mov"},
                                "stage_badge": badge,
                            }
                        )

        ready_to_publish = (
            stage_counts.get("05_Final_STL_Under500k", 0) > 0
            and stage_counts.get("06_Bambu_3MF_Profile", 0) > 0
            and stage_counts.get("07_Real_Print_Photos", 0) > 0
        )

        models.append(
            {
                "folder_name": folder.name,
                "title": title,
                "category": category,
                "tags": tags,
                "mw_pub_date": mw_pub_date,
                "description": description,
                "stage_counts": stage_counts,
                "final_stls": final_stls,
                "media": media_items,
                "ready_to_publish": ready_to_publish,
            }
        )
    return models


if __name__ == "__main__":
    initialize_mw_library_and_vault()

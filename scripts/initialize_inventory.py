#!/usr/bin/env python3
"""
Initialize/refresh the 7 Batches for @cosplaydad3d with:
- Short, real-human captions (no AI essays!)
- Smart initial #1 Hero selections
- Zero .HEIC files (only .jpg originals in 99_Raw_Originals_Backup/)
- Interactive Human-Review CosplayDad_Dashboard.html with ✕ Veto & ★ Hero controls
"""

from __future__ import annotations

import shutil
from pathlib import Path
from cms_manager import (
    DRIVE_ROOT,
    WORKSPACE_ROOT,
    READY_DIR,
    BACKUP_DIR,
    ensure_directories,
    purge_any_heic_files,
    format_for_instagram,
    build_tracker_and_dashboard,
)


BATCH_DEFINITIONS = [
    {
        "folder": "Batch_01_Lich_King_Helm_And_Torso_Armor",
        "title": "Lich King (Arthas) — Helm of Domination & Upper Torso Armor",
        "category": "World of Warcraft • Upper Armor",
        "makerworld_mode": "Make Review",
        "designer_credit": "@sarwtin",
        "slides": [
            ("12_lich_king_helm_of_domination.jpg", "pad", "helm_of_domination"),
            ("17_lich_king_spiked_pauldron_shoulder.jpg", "crop", "spiked_shoulder_pauldron"),
            ("07_ornate_chest_plate_emblem.jpg", "pad", "chest_plate_frontal"),
            ("10_lich_king_dragon_scale_cuffs_pair.jpg", "crop", "dragon_scale_gauntlet_cuffs"),
            ("11_lich_king_skull_belt_buckle.jpg", "crop", "skull_belt_buckle_fauld"),
            ("08_ornate_chest_plate_angle_view.jpg", "crop", "chest_plate_ergonomic_angle"),
        ],
        "ig_caption": """Lich King upper armor coming together. Printed on the Bambu P2S & H2S and finished with graphite powder + Rub 'n Buff over gloss black.

Model by @sarwtin

#lichking #arthas #cosplayarmor #bambulab #3dprinting #cosplaydad3d""",
        "mw_text": """Printed on Bambu Lab P2S & H2S in PLA+/PETG (0.16mm layers, organic tree supports). Sanded with filler primer, painted gloss black, and buffed with graphite powder + Silver Leaf Rub 'n Buff. Incredible sculpt by @sarwtin—fits great.""",
    },
    {
        "folder": "Batch_02_Lich_King_Leg_Armor_And_Weathering",
        "title": "Lich King — Skull Greaves, Articulated Sabatons & Leg Plates",
        "category": "World of Warcraft • Lower Armor",
        "makerworld_mode": "Make Review",
        "designer_credit": "@sarwtin",
        "slides": [
            ("13_lich_king_skull_greaves_shinguards_pair.jpg", "pad", "skull_greaves_shinguards_pair"),
            ("14_lich_king_sabatons_boot_armor.jpg", "crop", "sabatons_boot_armor_assembled"),
            ("09_lich_king_skull_knee_armor.jpg", "crop", "skull_knee_poleyn"),
            ("18_lich_king_thigh_armor_shells_pair.jpg", "crop", "thigh_cuisse_shells_pair"),
            ("05_lich_king_segmented_spine_armor.jpg", "pad", "segmented_spine_plate"),
            ("16_lich_king_skull_medallion_closeup.jpg", "crop", "skull_medallion_macro_turntable"),
            ("19_lich_king_thigh_armor_shells_closeup.jpg", "crop", "thigh_cuisse_weathering_closeup"),
            ("15_lich_king_sabatons_disassembled_view.jpg", "crop", "sabatons_disassembled_strapping"),
            ("06_lich_king_segmented_armor_plates_pair.jpg", "pad", "segmented_armor_plates_pair"),
        ],
        "ig_caption": """Lower leg armor, shinguards, and articulated boot sabatons for the Arthas build. Strapped internally so they actually flex when walking a con floor.

Model by @sarwtin

#lichkingcosplay #worldofwarcraft #3dprintedarmor #bambulab #cosplaydad3d""",
        "mw_text": """Lower armor printed on Bambu Lab P2S/H2S (PETG for the articulated boot sabatons so they flex without cracking, Elegoo Saturn 4 Ultra resin for the small skull medallions). Finished with graphite powder, Rub 'n Buff, and dark acrylic wash.""",
    },
    {
        "folder": "Batch_03_Frostmourne_And_Frozen_Throne_Pedestal",
        "title": "1:1 Frostmourne Runeblade & Frozen Throne Ice Pedestal",
        "category": "World of Warcraft • Weapon & Display",
        "makerworld_mode": "Build Note",
        "designer_credit": "@sarwtin / @cosplaydad3d",
        "slides": [
            ("30_frozen_throne_ice_spire_pedestal.jpg", "pad", "frozen_throne_ice_spire_pedestal"),
            ("22_frostmourne_runeblade_prop_full_view.jpg", "pad", "frostmourne_full_length_bench"),
            ("25_frostmourne_hilt_and_guard_closeup.jpg", "crop", "frostmourne_ram_skull_hilt_macro"),
            ("24_frostmourne_sword_angled_workshop_view.jpg", "pad", "frostmourne_angled_workshop_blade"),
            ("23_frostmourne_standing_with_lich_king_armor.jpg", "pad", "frostmourne_standing_with_armor"),
        ],
        "ig_caption": """Frozen Throne ice pedestal with translucent blue spires + full 1:1 Frostmourne in grey filler primer. Ready for paint next.

#frostmourne #lichking #worldofwarcraft #cosplayprops #bambulab #cosplaydad3d""",
        "mw_text": """1:1 Frostmourne printed vertically on Bambu Lab H2S over a steel core rod, seam-filled with Bondo and filler primer. Frozen Throne pedestal printed in matte grey PLA with translucent blue filament for the center ice crystals.""",
    },
    {
        "folder": "Batch_04_Elven_Filigree_Armory_Daughter_Build",
        "title": "Elven Filigree Pauldron & Bracer — Daughter's Cosplay Build",
        "category": "Fantasy Armory • Tree Supports",
        "makerworld_mode": "Print & Support Profile",
        "designer_credit": "@cosplaydad3d",
        "slides": [
            ("01_elven_filigree_pauldron_print.jpg", "pad", "elven_filigree_pauldron_primed"),
            ("02_elven_filigree_bracer_print.jpg", "pad", "elven_filigree_bracer_primed"),
            ("04_bambu_lab_pauldron_printing.jpg", "crop", "bambu_lab_tree_supports_in_progress"),
        ],
        "ig_caption": """Elven filigree shoulder and bracer print for my daughter's cosplay. Those organic tree supports on the Bambu plate popped right off in one piece.

#elvencosplay #cosplayarmor #bambulab #3dprinting #cosplaydad3d""",
        "mw_text": """Openwork filigree pauldron and bracer printed at a 35° angle on the Bambu Lab textured PEI plate (0.16mm layers, organic tree supports, 0.20mm top Z-distance). Primed in filler grey, ready for chrome paint and a resin center gem.""",
    },
    {
        "folder": "Batch_05_Mountain_Shaper_Cel_Shaded_Greatsword",
        "title": "Cel-Shaded 'Mountain Shaper' Greatsword vs. Frostmourne",
        "category": "Stylized Fantasy Weapons",
        "makerworld_mode": "Build & Paint Note",
        "designer_credit": "@cosplaydad3d / @ogi3d",
        "slides": [
            ("28_frostmourne_and_mountain_shaper_props.jpg", "pad", "frostmourne_vs_mountain_shaper_scale"),
            ("26_mountain_shaper_stylized_greatsword_view1.jpg", "pad", "mountain_shaper_greatsword_view1"),
            ("27_mountain_shaper_stylized_greatsword_view2.jpg", "pad", "mountain_shaper_greatsword_view2"),
        ],
        "ig_caption": """Cel-shaded Mountain Shaper greatsword next to Frostmourne for scale. Lots of Tamiya tape and airbrush masking to get that neon pixel glow without LEDs.

#genshinimpact #cosplayweapons #3dprintedprops #airbrush #bambulab #cosplaydad3d""",
        "mw_text": """Printed on Bambu Lab P2S/H2S over an internal dowel core. Primed matte white and masked step-by-step for the neon green/yellow airbrush gradient, with metallic bronze trim on the frame.""",
    },
    {
        "folder": "Batch_06_Arlecchino_Crimson_Moon_Scythe",
        "title": "Genshin Impact — Arlecchino's 'Crimson Moon's Semblance' Scythe",
        "category": "Genshin Impact • Wall Display",
        "makerworld_mode": "Make & Paint Note",
        "designer_credit": "@ogi3d / @cosplaydad3d",
        "slides": [
            ("29_arlecchino_scythe_crimson_moon_wall_display.jpg", "pad", "arlecchino_crimson_moon_scythe_display"),
        ],
        "ig_caption": """Arlecchino's Crimson Moon scythe finished and mounted up on the wall above the wig station.

#arlecchino #genshinimpactcosplay #cosplayprops #bambulab #3dprinting #cosplaydad3d""",
        "mw_text": """Printed with 2 walls and 8% gyroid infill on the upper crescent blades to keep the polearm tip lightweight. Wet-sanded to 600 grit and airbrushed with a jet-black to crimson red ombre fade.""",
    },
    {
        "folder": "Batch_07_Primal_Beast_Skulls_And_Dragon_Crossbow",
        "title": "Primal Saber-Tooth Skull Helmets & Dragon-Bone Hand Crossbow",
        "category": "Creature Bone & Fur Armory",
        "makerworld_mode": "Build & Weathering Note",
        "designer_credit": "@cosplaydad3d",
        "slides": [
            ("20_primal_tusk_skull_headdresses_and_armor.jpg", "pad", "primal_tusk_skull_headdresses_trio"),
            ("21_primal_tusk_skull_masks_stacked.jpg", "crop", "primal_tusk_skull_masks_stacked"),
            ("03_dragon_skull_crossbow_prop.jpg", "pad", "dragon_skull_hand_crossbow_primed"),
        ],
        "ig_caption": """Trio of weathered saber-tooth skull helmets with faux fur manes, plus a dragon-bone hand crossbow fresh in primer.

#cosplayhelmet #3dprintedprops #monsterhunter #bambulab #cosplaydad3d""",
        "mw_text": """Full-scale wearable beast skulls printed in one piece on the Bambu Lab H2S (0.20mm layers). Left light 220-grit texture for a porous bone look, weathered with burnt umber washes, and lashed with faux fur and red cord.""",
    },
]


def build_post_copy_markdown(batch: dict, formatted_slides: list) -> str:
    slide_lines = []
    for idx, (orig_name, mode_used, out_name) in enumerate(formatted_slides, start=1):
        role = "HERO SLIDE (#1)" if idx == 1 else f"Carousel Slide #{idx}"
        slide_lines.append(
            f"- **`{out_name}`** ({role}) — Source: `{orig_name}` | Framing: `4:5 ({mode_used.upper()})`"
        )

    return f"""# {batch['title']}

- **Batch Folder**: `{batch['folder']}`
- **Category**: {batch['category']}
- **Designer Credit**: {batch['designer_credit']}
- **MakerWorld Type**: {batch['makerworld_mode']}
- **Review Status**: Needs Review
- **Total Slides**: `{len(formatted_slides)}`

## Slide Manifest (`Instagram_Carousel/`)
{chr(10).join(slide_lines)}

---

## 1. Instagram Caption & Hashtags

```text
{batch['ig_caption']}
```

---

## 2. MakerWorld Text ({batch['makerworld_mode']})

```markdown
{batch['mw_text']}
```
"""


def run_refresh() -> None:
    ensure_directories()
    purge_any_heic_files(BACKUP_DIR)

    for batch in BATCH_DEFINITIONS:
        batch_dir = READY_DIR / batch["folder"]
        ig_dir = batch_dir / "Instagram_Carousel"
        mw_dir = batch_dir / "MakerWorld"
        if ig_dir.exists():
            shutil.rmtree(ig_dir)
        if mw_dir.exists():
            shutil.rmtree(mw_dir)
        ig_dir.mkdir(parents=True, exist_ok=True)
        mw_dir.mkdir(parents=True, exist_ok=True)

        formatted_slides = []
        for idx, (src_filename, mode, slug) in enumerate(batch["slides"], start=1):
            src_path = BACKUP_DIR / src_filename
            if not src_path.exists():
                raise FileNotFoundError(f"Missing source JPG in backup: {src_path}")

            ig_name = "01_Hero.jpg" if idx == 1 else f"{idx:02d}_Slide.jpg"
            ig_dst = ig_dir / ig_name
            actual_mode = format_for_instagram(src_path, ig_dst, mode=mode)
            formatted_slides.append((src_filename, actual_mode, ig_name))

            mw_prefix = "01_Cover" if idx == 1 else f"{idx:02d}_Detail"
            mw_dst = mw_dir / f"{mw_prefix}_{slug}.jpg"
            shutil.copy2(src_path, mw_dst)

        post_copy_md = build_post_copy_markdown(batch, formatted_slides)
        (batch_dir / "POST_COPY.md").write_text(post_copy_md, encoding="utf-8")
        print(f"Refreshed {batch['folder']} ({len(formatted_slides)} slides)")

    build_tracker_and_dashboard()
    print("All batches and interactive review dashboard updated!")


if __name__ == "__main__":
    run_refresh()

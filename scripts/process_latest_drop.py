#!/usr/bin/env python3
"""Build new batches 10-13, update Batch 04 & 06, populate MakerWorld real print photos, and deploy to Firebase."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, r"c:\P\CosplayDad3D\scripts")
from cms_manager import (
    BACKUP_DIR,
    READY_DIR,
    format_for_instagram,
    parse_post_copy,
    publish_dashboard_to_firebase,
    write_updated_post_copy,
)
from mw_pipeline import MW_MODELS_DIR


def build_batch(folder_name: str, slides: list[tuple[str, str]], meta_dict: dict) -> None:
    b_dir = READY_DIR / folder_name
    ig_dir = b_dir / "Instagram_Carousel"
    mw_dir = b_dir / "MakerWorld"
    if ig_dir.exists():
        shutil.rmtree(ig_dir)
    if mw_dir.exists():
        shutil.rmtree(mw_dir)
    ig_dir.mkdir(parents=True, exist_ok=True)
    mw_dir.mkdir(parents=True, exist_ok=True)

    final_slides = []
    for idx, (fname, mode) in enumerate(slides, start=1):
        sp = BACKUP_DIR / fname
        ig_name = "01_Hero.jpg" if idx == 1 else f"{idx:02d}_Slide.jpg"
        ig_dst = ig_dir / ig_name
        format_for_instagram(sp, ig_dst, mode=mode)
        shutil.copy2(sp, mw_dir / f"{idx:02d}_{fname}")
        final_slides.append(ig_dst)

    write_updated_post_copy(b_dir / "POST_COPY.md", meta_dict, final_slides)
    print(f"Built {folder_name} ({len(final_slides)} slides)")


def main() -> None:
    # 1. Update Batch_06_Arlecchino_Crimson_Moon_Scythe with the 2 con photos + wall display
    build_batch(
        "Batch_06_Arlecchino_Crimson_Moon_Scythe",
        [
            ("68_arlecchino_cosplay_with_crimson_moon_scythe_stained_glass.jpg", "crop"),
            ("69_arlecchino_and_varesa_burger_cosplay_at_con.jpg", "crop"),
            ("29_arlecchino_scythe_crimson_moon_wall_display.jpg", "pad"),
        ],
        {
            "title": "Genshin Impact — Arlecchino's 'Crimson Moon's Semblance' Scythe at the Con",
            "category": "Genshin Impact • Full Cosplay & Prop Build",
            "designer_credit": "@ogi3d / @cosplaydad3d",
            "makerworld_mode": "Make & Paint Note",
            "approval": "Needs Review",
            "ig_caption": """Arlecchino and her Crimson Moon scythe out on the con floor (plus hanging above the wig station at home).

#arlecchino #genshinimpactcosplay #cosplayprops #bambulab #3dprinting #cosplaydad3d""",
            "mw_text": """Printed with 2 walls and 8% gyroid infill on the upper crescent blades to keep the polearm tip lightweight for carrying all day at a convention. Wet-sanded to 600 grit and airbrushed with a jet-black to crimson red ombre fade.""",
        },
    )

    # 2. Create Batch_10_EmberCore_4Tier_Pauldron_Print_Showcase (15 photos of the 4-tier pauldron print + tree supports)
    build_batch(
        "Batch_10_EmberCore_4Tier_Pauldron_Print_Showcase",
        [
            ("49_embercore_4tier_pauldron_clean_front_hero.jpg", "crop"),
            ("43_embercore_4tier_pauldron_on_bambu_plate_high_angle.jpg", "crop"),
            ("44_embercore_4tier_pauldron_tree_supports_side_1.jpg", "crop"),
            ("54_embercore_4tier_pauldrons_pair_with_supports_1.jpg", "crop"),
            ("50_embercore_4tier_pauldron_clean_three_quarter.jpg", "crop"),
            ("47_embercore_4tier_pauldron_clean_side_profile_1.jpg", "crop"),
            ("52_embercore_4tier_pauldron_clean_side_profile_4.jpg", "crop"),
            ("42_embercore_4tier_pauldron_on_bambu_plate_front.jpg", "crop"),
            ("53_embercore_4tier_pauldron_second_print_on_plate.jpg", "crop"),
            ("40_embercore_pauldron_bambu_printing_closeup.jpg", "crop"),
            ("45_embercore_4tier_pauldron_tree_supports_side_2.jpg", "crop"),
            ("46_embercore_4tier_pauldron_with_supports_table.jpg", "crop"),
            ("48_embercore_4tier_pauldron_clean_side_profile_2.jpg", "crop"),
            ("51_embercore_4tier_pauldron_clean_side_profile_3.jpg", "crop"),
            ("55_embercore_4tier_pauldrons_pair_with_supports_2.jpg", "crop"),
        ],
        {
            "title": "EmberCore 4-Tier Gothic Filigree Pauldrons — Organic Tree Supports to Clean Print",
            "category": "EmberCore Armor Series • Shoulder Pauldrons",
            "designer_credit": "@cosplaydad3d",
            "makerworld_mode": "EmberCore Series Upload",
            "approval": "Needs Review",
            "ig_caption": """Matching pair of 4-tier EmberCore shoulder pauldrons fresh off the Bambu H2S. The organic tree supports snake right through the hollow filigree tiers and pop off clean.

#EmberCore #EmberCoreArmor #cosplaydad3d #3dprintedarmor #bambulab #cosplaywip #makerdad""",
            "mw_text": """Fantasy Mage 4-Tier Filigree Shoulder Pauldron - Cosplay Armor [EmberCore Series]

• About the EmberCore Series: Engineered with high-relief gothic scrollwork over a recessed diamond lattice and pierced core—designed to catch deep shadow washes cleanly under Rub 'n Buff highlights or house diffused internal LED lighting.
• Print Settings: Bambu Lab H2S / P2S (Textured PEI Plate), 0.16mm layers, 3 walls, 12% gyroid infill, Organic Tree Supports (0.20mm top Z-distance).
• Tags: embercore, cosplay, armor, pauldron, shoulder, filigree, fantasy, wearable, rpg""",
        },
    )

    # 3. Create Batch_11_EmberCore_3Tier_Hip_Tasset_Print_Showcase (7 photos of the 3-tier hip tasset print)
    build_batch(
        "Batch_11_EmberCore_3Tier_Hip_Tasset_Print_Showcase",
        [
            ("62_embercore_3tier_hip_tasset_clean_front_with_armory.jpg", "crop"),
            ("58_embercore_3tier_hip_tasset_finished_on_pei_plate.jpg", "crop"),
            ("61_embercore_3tier_hip_tasset_clean_side_view.jpg", "crop"),
            ("56_embercore_3tier_hip_tasset_printing_top_view.jpg", "crop"),
            ("57_embercore_3tier_hip_tasset_printing_tree_trunks.jpg", "crop"),
            ("60_embercore_3tier_hip_tasset_hollow_back_tree_supports.jpg", "crop"),
            ("59_embercore_3tier_hip_tasset_held_in_hand.jpg", "crop"),
        ],
        {
            "title": "EmberCore 3-Tier Filigree Hip Tasset Plate — From 4-Pose Concept to Physical Print",
            "category": "EmberCore Armor Series • Hip & Thigh Armor",
            "designer_credit": "@cosplaydad3d",
            "makerworld_mode": "EmberCore Series Upload",
            "approval": "Needs Review",
            "ig_caption": """3-tier EmberCore hip tasset plate off the build plate to pair with the pauldrons and bracers. Printed upright so just four main tree trunks support the entire curved shell from behind.

#EmberCore #EmberCoreArmor #cosplaydad3d #3dprintedarmor #bambulab #cosplaywip #makerdad""",
            "mw_text": """Fantasy Mage Filigree Hip Tasset / Thigh Armor Plate - Cosplay Armor [EmberCore Series]

• About the EmberCore Series: Engineered with high-relief metallic scrollwork over a recessed lattice and pierced core—designed to catch deep shadow washes cleanly under Rub 'n Buff highlights or house diffused internal LED lighting.
• Print Settings: Bambu Lab H2S / P2S (Textured PEI Plate), 0.16mm layers, 3 walls, 12% gyroid infill, Organic Tree Supports placed on the concave interior so the outer filigree stays completely unscarred.
• Tags: embercore, cosplay, armor, tasset, hiparmor, filigree, fantasy, wearable, rpg""",
        },
    )

    # 4. Create Batch_12_Con_Floor_Memories_And_Throwbacks (6 con & throwback photos)
    build_batch(
        "Batch_12_Con_Floor_Memories_And_Throwbacks",
        [
            ("70_colossalcon_east_dad_and_daughter_columbina_selfie.jpg", "pad"),
            ("73_anime_con_group_cosplay_pose_3.jpg", "crop"),
            ("71_anime_con_group_cosplay_pose_1.jpg", "crop"),
            ("72_anime_con_group_cosplay_pose_2.jpg", "crop"),
            ("74_anime_con_group_cosplay_pose_4.jpg", "crop"),
            ("75_throwback_daughters_halloween_costumes.jpg", "crop"),
        ],
        {
            "title": "Colossalcon East Memories & Where the Costume Building Started",
            "category": "Convention Memories • Family Cosplay",
            "designer_credit": "@cosplaydad3d",
            "makerworld_mode": "Community Post",
            "approval": "Needs Review",
            "ig_caption": """From store-bought Halloween costumes years ago to building full Genshin and anime cosplays together for Colossalcon East. Best hobby in the world.

#colossalconeast #cosplaydad3d #familycosplay #genshincosplay #columbina #makerdad""",
            "mw_text": """Convention memories from Colossalcon East with my daughters and their cosplay crew.""",
        },
    )

    # 5. Create Batch_13_Doughboy_Pool_Winterizing_Cap_Functional_Print (5 functional print photos)
    build_batch(
        "Batch_13_Doughboy_Pool_Winterizing_Cap_Functional_Print",
        [
            ("67_doughboy_pool_return_winterizing_cap_test_fit.jpg", "crop"),
            ("65_pool_winterizing_plug_cap_next_to_embercore_tassets.jpg", "crop"),
            ("64_pool_winterizing_plug_cap_on_pei_plate_2.jpg", "pad"),
            ("66_pool_winterizing_plug_cap_closeup_table.jpg", "crop"),
            ("63_pool_winterizing_plug_cap_on_pei_plate_1.jpg", "crop"),
        ],
        {
            "title": "When the Armor Printer Pauses for Dad Duty — Doughboy Pool Return Plug Cap",
            "category": "Functional 3D Print • Household Fix",
            "designer_credit": "@cosplaydad3d",
            "makerworld_mode": "Functional Print",
            "approval": "Needs Review",
            "ig_caption": """Took a 20-minute break between 18-hour EmberCore armor prints to model and print a replacement Doughboy pool winterizing cap. Gotta love having a 3D printer in the shop.

#functionalprint #3dprinting #bambulab #makerdad #cosplaydad3d""",
            "mw_text": """Quick functional replacement cap/plug for a Doughboy pool wall return fitting, printed on the Bambu Lab PEI plate in weather-resistant filament with a finger-grip turn tab.""",
        },
    )

    # 6. Copy the best physical print photos into 04_MakerWorld_Models/07_Real_Print_Photos/
    shutil.copy2(
        BACKUP_DIR / "41_embercore_mage_bracer_print_table_view.jpg",
        MW_MODELS_DIR
        / "MW_01_EmberCore_Mage_Filigree_Bracer"
        / "07_Real_Print_Photos"
        / "03_embercore_mage_bracer_print_table_view.jpg",
    )
    for fn in [
        "49_embercore_4tier_pauldron_clean_front_hero.jpg",
        "43_embercore_4tier_pauldron_on_bambu_plate_high_angle.jpg",
        "44_embercore_4tier_pauldron_tree_supports_side_1.jpg",
        "54_embercore_4tier_pauldrons_pair_with_supports_1.jpg",
        "50_embercore_4tier_pauldron_clean_three_quarter.jpg",
    ]:
        shutil.copy2(
            BACKUP_DIR / fn,
            MW_MODELS_DIR / "MW_02_EmberCore_Mage_Filigree_Pauldron" / "07_Real_Print_Photos" / fn,
        )

    for fn in [
        "58_embercore_3tier_hip_tasset_finished_on_pei_plate.jpg",
        "61_embercore_3tier_hip_tasset_clean_side_view.jpg",
        "62_embercore_3tier_hip_tasset_clean_front_with_armory.jpg",
        "57_embercore_3tier_hip_tasset_printing_tree_trunks.jpg",
        "60_embercore_3tier_hip_tasset_hollow_back_tree_supports.jpg",
    ]:
        shutil.copy2(
            BACKUP_DIR / fn,
            MW_MODELS_DIR / "MW_09_EmberCore_Mage_Filigree_Tasset" / "07_Real_Print_Photos" / fn,
        )

    # Also add 41_embercore_mage_bracer_print_table_view.jpg to Batch_04_EmberCore_Mage_Filigree_Armory
    b4_dir = READY_DIR / "Batch_04_EmberCore_Mage_Filigree_Armory"
    b4_ig = b4_dir / "Instagram_Carousel"
    b4_mw = b4_dir / "MakerWorld"
    format_for_instagram(
        BACKUP_DIR / "41_embercore_mage_bracer_print_table_view.jpg",
        b4_ig / "04_Slide.jpg",
        mode="crop",
    )
    shutil.copy2(
        BACKUP_DIR / "41_embercore_mage_bracer_print_table_view.jpg",
        b4_mw / "04_Detail_embercore_mage_bracer_table.jpg",
    )
    b4_meta = parse_post_copy(b4_dir / "POST_COPY.md")
    b4_slides = sorted([p for p in b4_ig.iterdir() if p.is_file() and p.suffix.lower() == ".jpg"])
    write_updated_post_copy(b4_dir / "POST_COPY.md", b4_meta, b4_slides)
    print("Added new bracer photo to Batch_04_EmberCore_Mage_Filigree_Armory")

    publish_dashboard_to_firebase(deploy=True)


if __name__ == "__main__":
    main()

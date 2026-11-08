import os
import shutil
import json
import subprocess

temp_dir = r"c:\P\Gem-image-jpg\gdrive_cosplay_temp"
jpg_dir = os.path.join(temp_dir, "jpg")
renamed_jpg_dir = os.path.join(temp_dir, "renamed_jpg")
os.makedirs(renamed_jpg_dir, exist_ok=True)

# Mapping of original HEIC/JPG to clear descriptive filenames
name_mapping = {
    "IMG_3589": "01_elven_filigree_pauldron_print.jpg",
    "IMG_3590": "02_elven_filigree_bracer_print.jpg",
    "IMG_3591": "03_dragon_skull_crossbow_prop.jpg",
    "IMG_3594": "04_bambu_lab_pauldron_printing.jpg",
    "IMG_3595": "05_lich_king_segmented_spine_armor.jpg",
    "IMG_3596": "06_lich_king_segmented_armor_plates_pair.jpg",
    "IMG_3597": "07_ornate_chest_plate_emblem.jpg",
    "IMG_3598": "08_ornate_chest_plate_angle_view.jpg",
    "IMG_3599": "09_lich_king_skull_knee_armor.jpg",
    "IMG_3600": "10_lich_king_dragon_scale_cuffs_pair.jpg",
    "IMG_3601": "11_lich_king_skull_belt_buckle.jpg",
    "IMG_3602": "12_lich_king_helm_of_domination.jpg",
    "IMG_3603": "13_lich_king_skull_greaves_shinguards_pair.jpg",
    "IMG_3604": "14_lich_king_sabatons_boot_armor.jpg",
    "IMG_3605": "15_lich_king_sabatons_disassembled_view.jpg",
    "IMG_3606": "16_lich_king_skull_medallion_closeup.jpg",
    "IMG_3607": "17_lich_king_spiked_pauldron_shoulder.jpg",
    "IMG_3608": "18_lich_king_thigh_armor_shells_pair.jpg",
    "IMG_3609": "19_lich_king_thigh_armor_shells_closeup.jpg",
    "IMG_3610": "20_primal_tusk_skull_headdresses_and_armor.jpg",
    "IMG_3611": "21_primal_tusk_skull_masks_stacked.jpg",
    "IMG_3612": "22_frostmourne_runeblade_prop_full_view.jpg",
    "IMG_3613": "23_frostmourne_standing_with_lich_king_armor.jpg",
    "IMG_3614": "24_frostmourne_sword_angled_workshop_view.jpg",
    "IMG_3615": "25_frostmourne_hilt_and_guard_closeup.jpg",
    "IMG_3616": "26_mountain_shaper_stylized_greatsword_view1.jpg",
    "IMG_3617": "27_mountain_shaper_stylized_greatsword_view2.jpg",
    "IMG_3618": "28_frostmourne_and_mountain_shaper_props.jpg",
    "IMG_3620": "29_arlecchino_scythe_crimson_moon_wall_display.jpg",
    "IMG_3621": "30_frozen_throne_ice_spire_pedestal.jpg"
}

# Copy and rename local JPEGs
for orig_base, new_name in name_mapping.items():
    src = os.path.join(jpg_dir, orig_base + ".jpg")
    dst = os.path.join(renamed_jpg_dir, new_name)
    shutil.copyfile(src, dst)
    print(f"Renamed: {orig_base}.jpg -> {new_name}")

print(f"Total renamed JPGs: {len(os.listdir(renamed_jpg_dir))}")

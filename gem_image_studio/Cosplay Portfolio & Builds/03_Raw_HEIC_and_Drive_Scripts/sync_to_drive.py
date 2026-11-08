import os
import subprocess
import json
import time

root_folder_id = "1Wd5aeKXJZeu-oWH0hxysKtpqj2poSDYl"
heic_folder_id = "1LnwkgAkMNO1MJAG8qM9oYKb2rFPX4YBM"
forai_folder_id = "16tYDMR3WKNXwOMTfcmL0wj808lfn99w2"

temp_dir = r"c:\P\Gem-image-jpg\gdrive_cosplay_temp"
renamed_jpg_dir = os.path.join(temp_dir, "renamed_jpg")
forai_dir = os.path.join(temp_dir, "forAI")

# Step 1: Upload all 30 renamed JPGs to !cosplaydad3d
jpg_files = sorted([f for f in os.listdir(renamed_jpg_dir) if f.endswith(".jpg")])
print(f"Uploading {len(jpg_files)} renamed JPGs to Drive root folder (!cosplaydad3d)...")

for idx, f in enumerate(jpg_files, 1):
    local_path = os.path.join(renamed_jpg_dir, f)
    cmd = f'gdrive mutate upload "{local_path}" --parent {root_folder_id}'
    print(f"[{idx}/{len(jpg_files)}] Uploading {f}...")
    res = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    if res.returncode != 0:
        print(f"  Error uploading {f}: {res.stderr}")
    else:
        print(f"  {res.stdout.strip()}")

# Step 2: Upload forAI descriptions
print("\nUploading description files to forAI folder...")
for f in ["cosplay_builds_descriptions.md", "README.md"]:
    local_path = os.path.join(forai_dir, f)
    cmd = f'gdrive mutate upload "{local_path}" --parent {forai_folder_id}'
    res = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    print(f"Uploaded {f}: {res.stdout.strip()}")

# Step 3: Move original HEIC files into the HEIC folder
print("\nMoving original HEIC files into HEIC folder in Drive...")
list_cmd = f"gdrive readonly ls {root_folder_id} --max 100 --json"
res = subprocess.run(list_cmd, capture_output=True, text=True, shell=True)
current_files = json.loads(res.stdout)
heics = [item for item in current_files if item.get("mimeType") == "image/heic"]
print(f"Found {len(heics)} HEIC files in root to move.")

for idx, item in enumerate(heics, 1):
    file_id = item["id"]
    name = item["name"]
    print(f"[{idx}/{len(heics)}] Moving {name} (ID: {file_id}) to HEIC folder...")
    mv_cmd = f"gdrive mutate mv {file_id} {heic_folder_id}"
    mv_res = subprocess.run(mv_cmd, capture_output=True, text=True, shell=True)
    if mv_res.returncode != 0:
        print(f"  Error moving {name}: {mv_res.stderr}")
    else:
        print(f"  {mv_res.stdout.strip()}")

print("\nAll Drive operations completed successfully!")

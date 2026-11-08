import subprocess
import json
import os
import shutil
from PIL import Image, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()

temp_dir = r"c:\P\Gem-image-jpg\gdrive_cosplay_temp"
heic_dir = os.path.join(temp_dir, "heic")
jpg_dir = os.path.join(temp_dir, "jpg")
os.makedirs(heic_dir, exist_ok=True)
os.makedirs(jpg_dir, exist_ok=True)

folder_id = "1Wd5aeKXJZeu-oWH0hxysKtpqj2poSDYl"
heic_folder_id = "1LnwkgAkMNO1MJAG8qM9oYKb2rFPX4YBM"
forai_folder_id = "16tYDMR3WKNXwOMTfcmL0wj808lfn99w2"

# 1. List files
cmd = f"gdrive readonly ls {folder_id} --max 100 --json"
res = subprocess.run(cmd, capture_output=True, text=True, shell=True)
files = json.loads(res.stdout)
heic_files = [f for f in files if f.get("mimeType") == "image/heic"]
print(f"Total HEIC files to download: {len(heic_files)}")

# 2. Download
for idx, f in enumerate(heic_files, 1):
    file_id = f["id"]
    name = f["name"]
    local_path = os.path.join(heic_dir, name)
    if not os.path.exists(local_path):
        print(f"[{idx}/{len(heic_files)}] Downloading {name}...")
        dl_cmd = f'gdrive readonly download {file_id} --out "{local_path}"'
        subprocess.run(dl_cmd, check=True, shell=True)
    else:
        print(f"[{idx}/{len(heic_files)}] {name} already exists.")

print("All downloads complete. Starting conversion...")

# 3. Convert to JPG
for name in sorted(os.listdir(heic_dir)):
    if name.lower().endswith(".heic"):
        src = os.path.join(heic_dir, name)
        dst_name = os.path.splitext(name)[0] + ".jpg"
        dst = os.path.join(jpg_dir, dst_name)
        if not os.path.exists(dst):
            try:
                im = Image.open(src)
                im = ImageOps.exif_transpose(im)
                im = im.convert("RGB")
                im.save(dst, "JPEG", quality=95)
                print(f"Converted {name} -> {dst_name} ({im.size})")
            except Exception as e:
                print(f"Error converting {name}: {e}")

print("All conversions complete!")

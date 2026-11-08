# tripo_client.py - Verified Tripo 3D v3 API Client for 3D Printing & Cosplay Workflows
import os
import time
import json
import requests
from dotenv import load_dotenv

BASE_URL = "https://openapi.tripo3d.ai/v3"
ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")


def get_api_key():
    load_dotenv(ENV_PATH, override=True)
    key = os.getenv("TRIPO_API_KEY", "").strip()
    if not key:
        raise ValueError("TRIPO_API_KEY not found in .env")
    return key


def _headers(is_json=True):
    h = {"Authorization": f"Bearer {get_api_key()}"}
    if is_json:
        h["Content-Type"] = "application/json"
    return h


def get_balance():
    """Query Tripo v3 credit balance and frozen credits."""
    r = requests.get(f"{BASE_URL}/account/balance", headers=_headers(is_json=False), timeout=15)
    data = r.json()
    if r.status_code == 200 and data.get("code") == 0:
        return data.get("data", {"balance": 0.0, "frozen": 0.0})
    raise RuntimeError(data.get("message") or f"HTTP {r.status_code}: {r.text}")


def upload_file(file_path):
    """Upload a local image/model file via POST /v3/files and return file_token."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f)}
        r = requests.post(
            f"{BASE_URL}/files",
            headers=_headers(is_json=False),
            files=files,
            timeout=60,
        )
    data = r.json()
    if r.status_code == 200 and data.get("code") == 0:
        return data["data"]["file_token"]
    raise RuntimeError(data.get("message") or f"Upload failed ({r.status_code}): {r.text}")


def create_image_to_model_task(
    image_path,
    model="v3.1-20260211",
    geometry_quality="detailed",
    texture=False,
    pbr=False,
    face_limit=None,
    enable_image_autofix=False,
):
    """Create a single-image 3D generation task via POST /v3/generation/image-to-model."""
    file_token = upload_file(image_path)
    payload = {
        "input": file_token,
        "model": model,
        "texture": bool(texture),
        "pbr": bool(pbr),
    }
    if model.startswith("v3"):
        payload["geometry_quality"] = geometry_quality
    if enable_image_autofix:
        payload["enable_image_autofix"] = True
    if face_limit:
        payload["face_limit"] = int(face_limit)

    r = requests.post(
        f"{BASE_URL}/generation/image-to-model",
        headers=_headers(is_json=True),
        json=payload,
        timeout=30,
    )
    data = r.json()
    if r.status_code == 200 and data.get("code") == 0:
        return data["data"]["task_id"]
    raise RuntimeError(data.get("message") or f"Image-to-model failed ({r.status_code}): {r.text}")


def create_multiview_to_model_task(
    views_dict,
    model="v3.1-20260211",
    geometry_quality="detailed",
    texture=False,
    pbr=False,
    face_limit=None,
):
    """
    Create a multiview 3D generation task via POST /v3/generation/multiview-to-model.
    views_dict: {'front': path, 'left': path, 'back': path, 'right': path}
    Front is required, plus at least one other view.
    """
    if not views_dict.get("front"):
        raise ValueError("Front view image is required for Multiview-to-Model.")

    inputs = []
    for slot in ["front", "left", "back", "right"]:
        path = views_dict.get(slot)
        if path and os.path.exists(path):
            token = upload_file(path)
            inputs.append({slot: token})

    if len(inputs) < 2:
        raise ValueError("At least 2 views (including Front) are required for Multiview-to-Model.")

    payload = {
        "inputs": inputs,
        "model": model,
        "texture": bool(texture),
        "pbr": bool(pbr),
    }
    if model.startswith("v3"):
        payload["geometry_quality"] = geometry_quality
    if face_limit:
        payload["face_limit"] = int(face_limit)

    r = requests.post(
        f"{BASE_URL}/generation/multiview-to-model",
        headers=_headers(is_json=True),
        json=payload,
        timeout=30,
    )
    data = r.json()
    if r.status_code == 200 and data.get("code") == 0:
        return data["data"]["task_id"]
    raise RuntimeError(data.get("message") or f"Multiview-to-model failed ({r.status_code}): {r.text}")


def create_convert_to_stl_task(
    source_task_id,
    export_format="STL",
    flatten_bottom=False,
    face_limit=None,
):
    """Create a format conversion task via POST /v3/models/convert."""
    payload = {
        "input": source_task_id,
        "format": export_format.upper(),
        "flatten_bottom": bool(flatten_bottom),
    }
    if face_limit:
        payload["face_limit"] = int(face_limit)

    r = requests.post(
        f"{BASE_URL}/models/convert",
        headers=_headers(is_json=True),
        json=payload,
        timeout=30,
    )
    data = r.json()
    if r.status_code == 200 and data.get("code") == 0:
        return data["data"]["task_id"]
    raise RuntimeError(data.get("message") or f"Convert model failed ({r.status_code}): {r.text}")


def get_task_status(task_id):
    """Query status of a task via GET /v3/tasks/{task_id}."""
    r = requests.get(f"{BASE_URL}/tasks/{task_id}", headers=_headers(is_json=False), timeout=20)
    data = r.json()
    if r.status_code == 200 and data.get("code") == 0:
        return data["data"]
    raise RuntimeError(data.get("message") or f"Task query failed ({r.status_code}): {r.text}")


def download_file(url, output_path):
    """Download a remote model file to local disk."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
    return output_path

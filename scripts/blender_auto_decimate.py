#!/usr/bin/env python3
r"""
Headless Blender Auto-Decimator, STL Exporter & Clay Render Generator
=====================================================================
Can be invoked two ways:
1. From regular Python / PowerShell:
     python c:\P\CosplayDad3D\scripts\blender_auto_decimate.py --input <path_to.blend_or_.stl> [--project MW_01_...] [--target-tris 280000]
   This automatically finds Blender 5.2 / 4.0 and launches it in headless background mode (`-b`).

2. Inside Blender (`blender.exe -b <file.blend> --python blender_auto_decimate.py -- ...`):
   - Counts current triangles across all mesh objects.
   - Renders a studio MatCap / Clay preview image into `07_Real_Print_Photos/`.
   - Applies a Decimate modifier to hit `target_tris` (default: 280,000 triangles, right inside
     the 200k-350k EmberCore sweet spot).
   - Saves `<Prefix>_Decimated_280k.blend` in `04_Blender_Working/`.
   - Exports `<Prefix>_v1.stl` into `05_Final_STL_Under500k/`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

BLENDER_CANDIDATES = [
    r"C:\Program Files\Blender Foundation\Blender 5.3\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 3.0\blender.exe",
]


def find_blender_exe() -> str:
    # 1. Check PATH
    which_b = shutil.which("blender")
    if which_b and os.path.exists(which_b):
        return which_b

    # 2. Dynamic scan in Program Files\Blender Foundation
    bf_dir = Path(r"C:\Program Files\Blender Foundation")
    if bf_dir.exists():
        found = sorted(bf_dir.glob("*/blender.exe"), reverse=True)
        if found:
            return str(found[0])

    # 3. Dynamic scan in LocalAppData\Programs\Blender Foundation
    local_bf = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Blender Foundation"
    if local_bf.exists():
        found = sorted(local_bf.glob("*/blender.exe"), reverse=True)
        if found:
            return str(found[0])

    # 4. Check explicit candidates
    for c in BLENDER_CANDIDATES:
        if os.path.exists(c):
            return c
    raise FileNotFoundError(
        "Could not find blender.exe. Please install Blender (e.g. `winget install BlenderFoundation.Blender` "
        "or from https://www.blender.org/download/)."
    )


# ============================================================================
# PART A: Code that runs INSIDE Blender's internal `bpy` Python environment
# ============================================================================
def run_inside_blender() -> None:
    import bpy
    import mathutils

    argv = sys.argv
    if "--" in argv:
        args = argv[argv.index("--") + 1 :]
    else:
        args = []

    input_path = Path(args[0])
    out_blend_path = Path(args[1])
    out_stl_path = Path(args[2])
    out_render_path = Path(args[3])
    target_tris = int(args[4]) if len(args) > 4 else 280_000

    # If input was an .stl or .glb rather than a .blend, clear default cube and import it
    ext = input_path.suffix.lower()
    if ext == ".stl":
        bpy.ops.wm.read_factory_settings(use_empty=True)
        if hasattr(bpy.ops.wm, "stl_import"):
            bpy.ops.wm.stl_import(filepath=str(input_path))
        else:
            bpy.ops.import_mesh.stl(filepath=str(input_path))
    elif ext in (".glb", ".gltf"):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(input_path))
    elif ext == ".obj":
        bpy.ops.wm.read_factory_settings(use_empty=True)
        if hasattr(bpy.ops.wm, "obj_import"):
            bpy.ops.wm.obj_import(filepath=str(input_path))
        else:
            bpy.ops.import_scene.obj(filepath=str(input_path))

    # Exit Sculpt/Edit mode if the user saved the .blend file while still in Sculpt Mode!
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except Exception:
            pass

    mesh_objs = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not mesh_objs:
        raise RuntimeError(f"No MESH objects found in {input_path}")

    # Count total initial triangles across all mesh objects
    depsgraph = bpy.context.evaluated_depsgraph_get()
    total_initial_tris = 0
    for obj in mesh_objs:
        eval_obj = obj.evaluated_get(depsgraph)
        mesh = eval_obj.to_mesh()
        mesh.calc_loop_triangles()
        total_initial_tris += len(mesh.loop_triangles)
        eval_obj.to_mesh_clear()

    print(f"[Blender Auto-Prep] Initial triangle count: {total_initial_tris:,}")

    # 1. Render a clean Clay / Studio preview BEFORE or AFTER decimation
    try:
        render_clay_preview(bpy, mathutils, mesh_objs, out_render_path)
        print(f"[Blender Auto-Prep] Saved Clay Render -> {out_render_path}")
    except Exception as e:
        print(f"[Blender Auto-Prep] Clay render warning (non-fatal): {e}")

    # 2. Apply Decimation if total_initial_tris > target_tris
    if total_initial_tris > target_tris:
        ratio = max(0.01, min(1.0, float(target_tris) / float(total_initial_tris)))
        print(
            f"[Blender Auto-Prep] Decimating from {total_initial_tris:,} -> ~{target_tris:,} tris (ratio={ratio:.5f})..."
        )
        for obj in mesh_objs:
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            mod = obj.modifiers.new(name="AutoDecimate_EmberCore", type="DECIMATE")
            mod.decimate_type = "COLLAPSE"
            mod.ratio = ratio
            mod.use_collapse_triangulate = True
            bpy.ops.object.modifier_apply(modifier=mod.name)
    else:
        print(
            f"[Blender Auto-Prep] Mesh already has {total_initial_tris:,} tris (<= {target_tris:,}); skipping decimate."
        )

    # Recount final triangles
    depsgraph = bpy.context.evaluated_depsgraph_get()
    final_tris = 0
    for obj in mesh_objs:
        eval_obj = obj.evaluated_get(depsgraph)
        mesh = eval_obj.to_mesh()
        mesh.calc_loop_triangles()
        final_tris += len(mesh.loop_triangles)
        eval_obj.to_mesh_clear()

    print(f"[Blender Auto-Prep] Final triangle count: {final_tris:,}")

    # 3. Save the decimated .blend file
    out_blend_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out_blend_path), copy=True)
    print(f"[Blender Auto-Prep] Saved Decimated .blend -> {out_blend_path}")

    # 4. Export final binary .STL
    out_stl_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in mesh_objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objs[0]

    if hasattr(bpy.ops.wm, "stl_export"):
        bpy.ops.wm.stl_export(
            filepath=str(out_stl_path),
            export_selected_objects=True,
            ascii_format=False,
        )
    else:
        bpy.ops.export_mesh.stl(
            filepath=str(out_stl_path),
            use_selection=True,
            ascii=False,
        )
    print(f"[Blender Auto-Prep] Exported Final STL ({final_tris:,} tris) -> {out_stl_path}")


def render_clay_preview(bpy, mathutils, mesh_objs, out_render_path: Path) -> None:
    """Set up a 3-point studio lighting rig, clay material override, and camera to render a crisp studio clay shot."""
    out_render_path.parent.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene

    # Use CYCLES (fast CPU/GPU with low samples + denoising) or EEVEE with real 3-point sun lights
    available_engines = {
        e.identifier
        for e in scene.render.bl_rna.properties["engine"].enum_items
    }
    if "BLENDER_EEVEE_NEXT" in available_engines:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    elif "BLENDER_EEVEE" in available_engines:
        scene.render.engine = "BLENDER_EEVEE"
    else:
        scene.render.engine = "CYCLES"
        scene.cycles.samples = 32

    # Create a warm sculptor's clay / matte grey material and apply to all mesh objects for the render
    clay_mat = bpy.data.materials.new(name="EmberCore_Studio_Clay")
    clay_mat.use_nodes = True
    bsdf = clay_mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.62, 0.58, 0.54, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.42
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = 0.35

    for obj in mesh_objs:
        if obj.data.materials:
            obj.data.materials[0] = clay_mat
        else:
            obj.data.materials.append(clay_mat)

    # Compute combined world-space bounding box of all mesh objects
    min_v = mathutils.Vector((1e9, 1e9, 1e9))
    max_v = mathutils.Vector((-1e9, -1e9, -1e9))
    for obj in mesh_objs:
        for corner in obj.bound_box:
            wc = obj.matrix_world @ mathutils.Vector(corner)
            min_v.x = min(min_v.x, wc.x)
            min_v.y = min(min_v.y, wc.y)
            min_v.z = min(min_v.z, wc.z)
            max_v.x = max(max_v.x, wc.x)
            max_v.y = max(max_v.y, wc.y)
            max_v.z = max(max_v.z, wc.z)

    # If the mesh is lying flat (Z extent is much smaller than Y or X extent),
    # rotate it 90 degrees upright around X for a clean vertical portrait clay render,
    # then restore its original rotation right after rendering!
    extents = max_v - min_v
    saved_rotations = []
    if extents.z < min(extents.x, extents.y) * 0.65:
        import math as _math

        for obj in mesh_objs:
            saved_rotations.append((obj, obj.rotation_euler.copy()))
            obj.rotation_euler.rotate_axis("X", _math.radians(-90.0))
        bpy.context.view_layer.update()
        min_v = mathutils.Vector((1e9, 1e9, 1e9))
        max_v = mathutils.Vector((-1e9, -1e9, -1e9))
        for obj in mesh_objs:
            for corner in obj.bound_box:
                wc = obj.matrix_world @ mathutils.Vector(corner)
                min_v.x = min(min_v.x, wc.x)
                min_v.y = min(min_v.y, wc.y)
                min_v.z = min(min_v.z, wc.z)
                max_v.x = max(max_v.x, wc.x)
                max_v.y = max(max_v.y, wc.y)
                max_v.z = max(max_v.z, wc.z)

    center = (min_v + max_v) * 0.5
    size = max((max_v - min_v).length, 0.001)

    # Create 3-point Directional Sun Lights (scale-independent!)
    lights_spec = [
        ("KeyLight", (0.7, -1.0, 0.9), 4.2, (1.0, 0.96, 0.90)),
        ("FillLight", (-1.1, -0.8, 0.3), 1.6, (0.80, 0.88, 1.0)),
        ("RimLight", (0.2, 1.2, 0.8), 3.0, (1.0, 0.92, 0.85)),
    ]
    for l_name, dir_vec, energy, color in lights_spec:
        ldata = bpy.data.lights.new(name=l_name, type="SUN")
        ldata.energy = energy
        ldata.color = color
        ldata.angle = 0.15
        lobj = bpy.data.objects.new(name=l_name, object_data=ldata)
        scene.collection.objects.link(lobj)
        lobj.location = center + mathutils.Vector(dir_vec).normalized() * (size * 2.0)
        look_dir = center - lobj.location
        lobj.rotation_euler = look_dir.to_track_quat("-Z", "Y").to_euler()

    # Create a dedicated studio camera positioned at a flattering 3/4 angle
    cam_data = bpy.data.cameras.new(name="StudioClayCam")
    cam_data.lens = 58
    cam_data.clip_start = size * 0.001
    cam_data.clip_end = size * 50.0
    cam_obj = bpy.data.objects.new("StudioClayCam", cam_data)
    scene.collection.objects.link(cam_obj)

    offset = mathutils.Vector((-0.95, -1.15, 0.40)).normalized() * (size * 1.80)
    cam_obj.location = center + offset
    direction = center - cam_obj.location
    cam_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam_obj

    # Dark studio background
    if not scene.world:
        scene.world = bpy.data.worlds.new("StudioWorld")
    scene.world.use_nodes = True
    bg_node = scene.world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs[0].default_value = (0.05, 0.06, 0.08, 1.0)
        bg_node.inputs[1].default_value = 0.8

    scene.render.resolution_x = 1440
    scene.render.resolution_y = 1800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 94
    scene.render.filepath = str(out_render_path)

    bpy.ops.render.render(write_still=True)

    # Restore original mesh rotations if we stood it upright for the portrait render
    if saved_rotations:
        for obj, orig_rot in saved_rotations:
            obj.rotation_euler = orig_rot
        bpy.context.view_layer.update()


# ============================================================================
# PART B: Host CLI Wrapper (called by Antigravity or User from PowerShell)
# ============================================================================
def run_from_host_cli() -> None:
    import argparse
    from mw_pipeline import MW_MODELS_DIR, inspect_stl_file

    parser = argparse.ArgumentParser(
        description="Auto-decimate a .blend or .stl in headless Blender, export <500k .stl, and render MatCap clay image."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the sculpted .blend file or raw Tripo .stl/.glb file",
    )
    parser.add_argument(
        "--project",
        default="",
        help="Target project folder name inside 04_MakerWorld_Models (e.g. MW_01_EmberCore_Mage_Filigree_Bracer)",
    )
    parser.add_argument(
        "--prefix",
        default="",
        help="File prefix for outputs, e.g. EmberCore_Mage_Bracer",
    )
    parser.add_argument(
        "--target-tris",
        type=int,
        default=280_000,
        help="Target triangle count after decimation (default: 280,000 for 200k-350k EmberCore sweet spot)",
    )
    args = parser.parse_args()

    src_path = Path(args.input).resolve()
    if not src_path.exists():
        raise FileNotFoundError(f"Input file not found: {src_path}")

    # Determine target project folder
    if args.project:
        proj_dir = MW_MODELS_DIR / args.project
    elif "04_MakerWorld_Models" in src_path.parts:
        idx = src_path.parts.index("04_MakerWorld_Models")
        proj_dir = Path(*src_path.parts[: idx + 2])
    else:
        proj_dir = src_path.parent

    # Determine clean prefix (e.g. EmberCore_Mage_Filigree_Bracer)
    prefix = args.prefix
    if not prefix:
        if proj_dir.name.startswith("MW_"):
            prefix = "_".join(proj_dir.name.split("_")[2:])
        else:
            prefix = src_path.stem.replace("_Sculpted_HighPoly", "").replace("_raw", "")

    blender_working_dir = proj_dir / "04_Blender_Working"
    final_stl_dir = proj_dir / "05_Final_STL_Under500k"
    photos_dir = proj_dir / "07_Real_Print_Photos"
    blender_working_dir.mkdir(parents=True, exist_ok=True)
    final_stl_dir.mkdir(parents=True, exist_ok=True)
    photos_dir.mkdir(parents=True, exist_ok=True)

    # Keep a backup of the input high-poly .blend inside 04_Blender_Working/ if not already there
    if src_path.suffix.lower() == ".blend":
        highpoly_dst = blender_working_dir / f"{prefix}_A_Sculpted_HighPoly.blend"
        if src_path.resolve() != highpoly_dst.resolve():
            shutil.copy2(src_path, highpoly_dst)
            print(f"Backed up high-poly sculpt -> {highpoly_dst.name}")

    k_label = f"{args.target_tris // 1000}k"
    out_blend = blender_working_dir / f"{prefix}_B_Decimated_{k_label}.blend"
    out_stl = final_stl_dir / f"{prefix}_v1.stl"
    out_render = photos_dir / f"02_{prefix}_MatCap_Clay_Render.jpg"

    blender_exe = find_blender_exe()
    cmd = [
        blender_exe,
        "--background",
        "--factory-startup",
    ]
    if src_path.suffix.lower() == ".blend":
        cmd.append(str(src_path))
    cmd.extend(
        [
            "--python",
            str(Path(__file__).resolve()),
            "--",
            str(src_path),
            str(out_blend),
            str(out_stl),
            str(out_render),
            str(args.target_tris),
        ]
    )

    print(f"Launching headless Blender ({Path(blender_exe).parent.name})...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    for line in res.stdout.splitlines():
        if "[Blender Auto-Prep]" in line or "Saved:" in line or "Error" in line:
            print(line)
    if res.returncode != 0:
        print(res.stderr)
        raise RuntimeError(f"Blender exited with code {res.returncode}")

    if out_stl.exists():
        meta = inspect_stl_file(out_stl)
        print(
            f"[OK] Verified output STL: {out_stl.name} -> {meta['triangles']:,} triangles ({meta['size_mb']} MB)"
        )


if __name__ == "__main__":
    try:
        import bpy as _bpy  # type: ignore

        IN_BLENDER = True
    except ImportError:
        IN_BLENDER = False

    if IN_BLENDER:
        run_inside_blender()
    else:
        run_from_host_cli()

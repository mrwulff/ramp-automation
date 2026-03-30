import bpy
import csv
import os
import subprocess
import math
from mathutils import Vector

# =====================
# CONFIG
# =====================

CSV_FILE = "m.csv"
OUTPUT_DIR = "output"

ANCHOR_NAME = "GraphicAnchor"  # optional, not required anymore

MAX_WIDTH = 105
EXTRUDE_HEIGHT = 0.002
Z_OFFSET = 0.8  # height above plate

# GRID
GRID_MODE = True
GRID_COLUMNS = 5
GRID_SPACING_X = 100
GRID_SPACING_Y = 60


PLATE_WIDTH = 111
PLATE_HEIGHT = 28
MARGIN = 0.9  # 90% fill (prevents edge clipping)

# =====================

os.makedirs(OUTPUT_DIR, exist_ok=True)

# =====================
# CLEAN
# =====================


def clear_previous():
    for obj in list(bpy.data.objects):
        if obj.name.startswith("ART_") or obj.name.startswith("PLATE_"):
            bpy.data.objects.remove(obj, do_unlink=True)


# =====================
# PNG → SVG (POTRACE)
# =====================


def convert_png_to_svg(png):
    print("Tracing with potrace:", png)

    pbm = png.replace(".png", ".pbm")
    svg = png.replace(".png", "_trace.svg")

    subprocess.run(["magick", png, "-threshold", "50%", pbm], check=True)

    subprocess.run(["potrace", pbm, "-s", "-o", svg], check=True)

    return svg


# =====================
# IMPORT SVG SAFELY
# =====================


def import_svg(path):
    before = set(bpy.data.objects)

    bpy.ops.import_curve.svg(filepath=path)

    after = set(bpy.data.objects)

    new_objs = list(after - before)

    for o in new_objs:
        o.name = "ART_" + o.name

    return new_objs


# =====================
# FILTER VALID CURVES
# =====================


def filter_valid_curves(objs):
    valid = []

    for obj in objs:
        if obj.type == "CURVE" and obj.data and len(obj.data.splines) > 0:
            valid.append(obj)
        else:
            bpy.data.objects.remove(obj, do_unlink=True)

    return valid


# =====================
# CONVERT TO MESH
# =====================


def convert_to_mesh(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)

    try:
        mesh = bpy.data.meshes.new_from_object(eval_obj)
    except:
        return None

    new_obj = bpy.data.objects.new(obj.name + "_mesh", mesh)
    bpy.context.collection.objects.link(new_obj)

    new_obj.matrix_world = obj.matrix_world

    bpy.data.objects.remove(obj, do_unlink=True)

    return new_obj


# =====================
# JOIN MESHES
# =====================


def join_meshes(mesh_objs):
    if not mesh_objs:
        return None

    bpy.ops.object.select_all(action="DESELECT")

    for obj in mesh_objs:
        obj.select_set(True)

    bpy.context.view_layer.objects.active = mesh_objs[0]

    bpy.ops.object.join()

    return mesh_objs[0]


# =====================
# FIX ROTATION (SVG)
# =====================


def fix_svg_orientation(obj):
    obj.rotation_euler[0] = math.radians(90)

    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)


# =====================
# SCALE + CENTER
# =====================


def center_and_scale(obj):
    bpy.context.view_layer.update()

    # Reset transforms
    obj.location = (0, 0, 0)
    obj.scale = (1, 1, 1)

    bpy.context.view_layer.update()

    # --- get bounding box in local space ---
    bbox = [Vector(v) for v in obj.bound_box]

    min_x = min(v.x for v in bbox)
    max_x = max(v.x for v in bbox)
    min_y = min(v.y for v in bbox)
    max_y = max(v.y for v in bbox)

    width = max_x - min_x
    height = max_y - min_y

    if width == 0 or height == 0:
        print("Invalid bounds")
        return

    # --- 🔥 SCALE TO FIT BOTH AXES ---
    scale_x = (PLATE_WIDTH * MARGIN) / width
    scale_y = (PLATE_HEIGHT * MARGIN) / height

    scale = min(scale_x, scale_y)

    obj.scale = (scale, scale, scale)

    bpy.context.view_layer.update()

    # --- recalc world bbox AFTER scaling ---
    bbox = [obj.matrix_world @ Vector(v) for v in obj.bound_box]

    min_x = min(v.x for v in bbox)
    max_x = max(v.x for v in bbox)
    min_y = min(v.y for v in bbox)
    max_y = max(v.y for v in bbox)

    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2

    # --- 🔥 CENTER PERFECTLY ---
    obj.location.x -= center_x
    obj.location.y -= center_y


# =====================
# EXTRUDE
# =====================


def extrude(obj):
    mod = obj.modifiers.new("solid", "SOLIDIFY")
    mod.thickness = EXTRUDE_HEIGHT

    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)


# =====================
# DUPLICATE PLATE
# =====================


def duplicate_plate():
    base = bpy.data.objects["Plate_Base"]

    new = base.copy()
    new.data = base.data.copy()

    bpy.context.collection.objects.link(new)

    return new


# =====================
# EXPORT
# =====================


def export_scene(name):
    path = os.path.join(OUTPUT_DIR, name + ".stl")

    bpy.ops.export_mesh.stl(filepath=path)

    bpy.context.scene.render.filepath = os.path.join(OUTPUT_DIR, name + ".png")

    bpy.ops.render.render(write_still=True)


# =====================
# MAIN
# =====================

plates = []

with open(CSV_FILE) as f:
    reader = csv.DictReader(f)

    for i, row in enumerate(reader):
        print("Processing:", row["name"])

        clear_previous()

        name = row["name"]
        graphic = row["graphic"]

        if graphic.endswith(".png"):
            graphic = convert_png_to_svg(graphic)

        objs = import_svg(graphic)
        objs = filter_valid_curves(objs)

        mesh_objs = []

        for obj in objs:
            m = convert_to_mesh(obj)
            if m and len(m.data.vertices) > 0:
                mesh_objs.append(m)

        logo = join_meshes(mesh_objs)

        if not logo:
            print("Skipping:", name)
            continue

        # FIX ROTATION
        fix_svg_orientation(logo)

        # SCALE + CENTER
        center_and_scale(logo)

        # EXTRUDE
        extrude(logo)

        # CREATE PLATE
        # CREATE PLATE
        plate = duplicate_plate()
        plate.name = "PLATE_" + name

        # find the anchor INSIDE this plate
        anchor = None
        for child in plate.children:
            if child.name.startswith("GraphicAnchor"):
                anchor = child
                break

        # if not anchor:
        #    print("No anchor found")
        #    print(logo.rotation_euler[1], "logo rotation")
        #    continue
        # print(logo.rotation_euler[1], "logo rotation")
        # 🔥 PARENT LOGO TO ANCHOR (NOT PLATE)
        logo.parent = anchor
        # logo.rotation_euler[1] = math.radians(50)

        # 🔥 RESET LOCAL TRANSFORMS
        logo.location = (-52.5, -15, 2)
        logo.rotation_euler = (0, 00, 0)
        logo.rotation_euler[0] = math.radians(-90)
        print(logo.rotation_euler[1], "logo rotation")

        # GRID POSITION
        if GRID_MODE:
            col = i % GRID_COLUMNS
            row_i = i // GRID_COLUMNS

            plate.location.x += col * GRID_SPACING_X
            plate.location.y -= row_i * GRID_SPACING_Y

        plates.append(plate)

        if not GRID_MODE:
            export_scene(name)

# EXPORT FINAL
if GRID_MODE:
    export_scene("build_plate")

print("DONE")

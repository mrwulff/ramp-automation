import bpy
import csv
import os
import subprocess
from mathutils import Vector


# =====================
# CONFIG
# =====================

CSV_FILE = "plates.csv"
OUTPUT_DIR = "output"

ANCHOR_NAME = "GraphicAnchor"

INKSCAPE = r"C:\Program Files\Inkscape\bin\inkscape.exe"

MAX_WIDTH = 120
EXTRUDE_HEIGHT = 0.002

GRID_MODE = True
GRID_COLUMNS = 5
GRID_SPACING_X = 100
GRID_SPACING_Y = 60

# =====================

os.makedirs(OUTPUT_DIR, exist_ok=True)

anchor = bpy.data.objects[ANCHOR_NAME]

# =====================
# CLEANUP
# =====================


def clear_previous():
    for obj in list(bpy.data.objects):
        if obj.name.startswith("ART_") or obj.name.startswith("PLATE_"):
            bpy.data.objects.remove(obj, do_unlink=True)


# =====================
# PNG → SVG (Inkscape)
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
# FILTER REAL CURVES
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
# SAFE MESH CONVERSION
# =====================


def convert_to_mesh(obj):
    if obj.type != "CURVE":
        return None

    if not obj.data or len(obj.data.splines) == 0:
        return None

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
# JOIN ALL PARTS FIRST
# =====================


def join_meshes(mesh_objs):
    print(mesh_objs, "MESH OBJECTS")
    if not mesh_objs:
        return None

    # Deselect everything
    bpy.ops.object.select_all(action="DESELECT")

    # Select all mesh objects
    for obj in mesh_objs:
        obj.select_set(True)

    # Set active object
    bpy.context.view_layer.objects.active = mesh_objs[0]

    # Join
    bpy.ops.object.join()

    return mesh_objs[0]


# =====================
# CENTER + SCALE PROPERLY
# =====================


def center_and_scale(obj):
    bpy.context.view_layer.update()

    # --- STEP 1: reset transforms ---
    obj.location = (0, 0, 0)
    obj.scale = (1, 1, 1)

    bpy.context.view_layer.update()

    # --- STEP 2: get bounding box ---
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

    # --- STEP 3: scale to fit ---
    scale_factor = MAX_WIDTH / width
    obj.scale = (scale_factor, scale_factor, scale_factor)

    bpy.context.view_layer.update()

    # --- STEP 4: recalc bounds AFTER scaling ---
    bbox = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
    center = sum(bbox, Vector()) / 8

    # --- STEP 5: move to origin cleanly ---
    obj.location -= center

    # --- STEP 6: snap to anchor EXACTLY ---
    obj.location.z += 5.5
    obj.location = anchor.location.copy()


# =====================
# EXTRUDE
# =====================


def extrude(obj):
    mod = obj.modifiers.new("solid", "SOLIDIFY")
    mod.thickness = EXTRUDE_HEIGHT

    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)


# =====================
# DUPLICATE BASE PLATE
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
    # bpy.context.scene.render.filepath=

    bpy.ops.render.render(write_still=True)


# =====================
# MAIN LOOP
# =====================

plates = []

with open(CSV_FILE) as f:
    reader = csv.DictReader(f)

    for i, row in enumerate(reader):
        print("Processing:", row["name"])

        clear_previous()

        name = row["name"]
        graphic = row["graphic"]

        ext = os.path.splitext(graphic)[1].lower()

        if ext == ".png":
            graphic = convert_png_to_svg(graphic)

        objs = import_svg(graphic)

        objs = filter_valid_curves(objs)

        mesh_objs = []

        for obj in objs:
            m = convert_to_mesh(obj)
            print(m, "MMMM")
            if m:
                mesh_objs.append(m)

        logo = join_meshes(mesh_objs)

        if not logo:
            print("Skipping:", name)
            continue

        # 🔥 KEY FIX: operate AFTER join
        center_and_scale(logo)
        # logo.location.z += 5.5
        extrude(logo)

        plate = duplicate_plate()
        plate.name = "PLATE_" + name

        # grid placement
        if GRID_MODE:
            col = i % GRID_COLUMNS
            row_i = i // GRID_COLUMNS

            plate.location.x += col * GRID_SPACING_X
            plate.location.y -= row_i * GRID_SPACING_Y

            logo.parent = plate
            logo.location = (0, 0, 0)

        plates.append(plate)

        if not GRID_MODE:
            export_scene(name)

# export full batch
if GRID_MODE:
    export_scene("build_plate")

print("DONE")

import bpy
import sys
import os
import math
from mathutils import Vector


# ---------- ARGS ----------
argv = sys.argv
args = argv[argv.index("--") + 1 :]

SVG_PATH = os.path.abspath(args[0])
OUTPUT_STL = os.path.abspath(args[1])
X = float(args[2])
Y = float(args[3])
SCALE = float(args[4]) * 100
# ROT = float(args[5])

print("🔥 APPLY LOGO START")
print("SVG:", SVG_PATH)
print("OUT:", OUTPUT_STL)
# print("X,Y,SCALE,ROT:", X, Y, SCALE, ROT)

# ---------- CLEAN SCENE (keep template objects) ----------
# Only delete previous logo objects if they exist
for obj in list(bpy.data.objects):
    if obj.name.startswith("LOGO_"):
        bpy.data.objects.remove(obj, do_unlink=True)

# ---------- IMPORT SVG ----------
before = set(bpy.context.scene.objects)

bpy.ops.import_curve.svg(filepath=SVG_PATH)

after = set(bpy.context.scene.objects)
curves = [o for o in (after - before) if o.type == "CURVE"]

if not curves:
    raise Exception("❌ No curves imported")

print(f"[INFO] Imported {len(curves)} curves")

# Rename for tracking
for i, obj in enumerate(curves):
    obj.name = f"LOGO_{i}"

# ---------- CURVE SETUP ----------
for obj in curves:
    obj.data.dimensions = "2D"
    obj.data.fill_mode = "BOTH"
    obj.data.use_fill_caps = True
    obj.data.extrude = 0.05

    obj.data.resolution_u = 64
    obj.data.render_resolution_u = 128

    # 🔥 ensure closed shapes (fixes caps)
    for spline in obj.data.splines:
        spline.use_cyclic_u = True

# ---------- SELECT ----------
bpy.ops.object.select_all(action="DESELECT")
for o in curves:
    o.select_set(True)

bpy.context.view_layer.objects.active = curves[0]

# ---------- CONVERT TO MESH ----------
bpy.ops.object.convert(target="MESH")

meshes = [o for o in bpy.context.selected_objects if o.type == "MESH"]

if not meshes:
    raise Exception("❌ No mesh created")

# ---------- JOIN ----------
if len(meshes) > 1:
    bpy.ops.object.join()

logo = bpy.context.active_object
logo.name = "LOGO_FINAL"

# ---------- FIX ORIGIN ----------
bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")

# ---------- APPLY TRANSFORMS ----------
# 🔥 scale correctly (not *=)
# ---------- NORMALIZE SIZE ----------
bpy.context.view_layer.update()

bbox = [logo.matrix_world @ Vector(v) for v in logo.bound_box]

min_x = min(v.x for v in bbox)
max_x = max(v.x for v in bbox)

width = max_x - min_x

if width == 0:
    raise Exception("Logo width is zero")

# normalize to width = 1
normalize = 1.0 / width
logo.scale = (normalize, normalize, normalize)

bpy.context.view_layer.update()


# ---------- APPLY USER SCALE (REAL WORLD UNITS) ----------
logo.scale = (logo.scale.x * SCALE, logo.scale.y * SCALE, logo.scale.z)

# 🔥 rotate (Z axis)
# logo.rotation_euler[2] = math.radians(ROT)

# 🔥 position (flip Y from UI)
logo.location.x = X
logo.location.y = -Y

# ---------- PLACE ON TEMPLATE ----------
base = bpy.data.objects.get("Base")

if base:
    # put logo on top of base
    logo.location.z = base.dimensions.z

# ---------- OPTIONAL BOOLEAN ----------
if base:
    print("[INFO] Applying boolean union")

    mod = base.modifiers.new(name="LogoBoolean", type="BOOLEAN")
    mod.operation = "UNION"
    mod.object = logo

    bpy.context.view_layer.objects.active = base
    bpy.ops.object.modifier_apply(modifier=mod.name)

    # remove logo after applying
    bpy.data.objects.remove(logo, do_unlink=True)

    target = base
else:
    target = logo

# ---------- EXPORT ----------
bpy.ops.object.select_all(action="DESELECT")
target.select_set(True)

bpy.ops.wm.stl_export(
    filepath=OUTPUT_STL, export_selected_objects=True, apply_modifiers=True
)

print("✅ STL exported successfully")

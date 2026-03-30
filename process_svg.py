import bpy
import bmesh
import sys
import os

# ---------- CONFIG ----------
EXTRUDE = 0.002
RESOLUTION = 5122
RENDER_RESOLUTION = 25
MERGE_DIST = 0.00002

# ---------- ARGS ----------
argv = sys.argv
args = argv[argv.index("--") + 1 :]

SVG_PATH = os.path.abspath(args[0])
OUTPUT_STL = os.path.abspath(args[1])

print(f"[INFO] SVG: {SVG_PATH}")
print(f"[INFO] STL: {OUTPUT_STL}")

# ---------- RESET SCENE ----------
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

# ---------- IMPORT SVG ----------
before = set(bpy.context.scene.objects)
bpy.ops.import_curve.svg(filepath=SVG_PATH)
after = set(bpy.context.scene.objects)

curves = [o for o in (after - before) if o.type == "CURVE"]

if not curves:
    raise Exception("❌ No curves imported")
for obj in curves:
    for spline in obj.data.splines:
        spline.use_cyclic_u = True

print(f"[INFO] Imported {len(curves)} curves")

# ---------- CURVE SETUP (CRITICAL) ----------
for obj in curves:
    obj.data.dimensions = "2D"  # 🔥 REQUIRED
    obj.data.fill_mode = "BOTH"  # (was BOTH)
    obj.data.use_fill_caps = True  # ensure caps
    obj.data.extrude = EXTRUDE

    obj.data.resolution_u = 64
    obj.data.render_resolution_u = 128

    # 🔥 CRITICAL: close shapes
    for spline in obj.data.splines:
        spline.use_cyclic_u = True

# ---------- SELECT ----------
bpy.ops.object.select_all(action="DESELECT")
for o in curves:
    o.select_set(True)

bpy.context.view_layer.objects.active = curves[0]

# ---------- CONVERT TO MESH ----------
bpy.ops.object.convert(target="MESH")

meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]

if not meshes:
    raise Exception("❌ No mesh created")


# ---------- LIGHT CLEAN ONLY ----------
def clean_mesh(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    # 🔥 ONLY do safe cleanup
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=MERGE_DIST)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    bm.to_mesh(obj.data)
    bm.free()


for m in meshes:
    clean_mesh(m)

print("[OK] Mesh cleaned (non-destructive)")

# ---------- EXPORT ----------
bpy.ops.object.select_all(action="DESELECT")
for m in meshes:
    m.select_set(True)

bpy.context.view_layer.objects.active = meshes[0]

bpy.ops.wm.stl_export(
    filepath=OUTPUT_STL, export_selected_objects=True, apply_modifiers=True
)

print("✅ STL exported")

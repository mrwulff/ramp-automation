import bpy
import sys
import math
from mathutils import Vector

# ---------- ARGS ----------
argv = sys.argv
args = argv[argv.index("--") + 1 :]

svgA = args[0]
svgB = args[1]
OUTPUT = args[2]

xA, yA, scaleA, rotA, heightA = map(float, args[3:8])
xB, yB, scaleB, rotB, heightB = map(float, args[8:13])

RAMP_WIDTH = 111.0
RAMP_HEIGHT = 31.0

print("START CLEAN PIPELINE")


# ---------- IMPORT ----------
def import_svg(svg):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_curve.svg(filepath=svg)
    after = set(bpy.context.scene.objects)
    return [o for o in (after - before) if o.type == "CURVE"]


# ---------- BUILD ----------
def build_logo(curves, name):
    if not curves:
        return None

    for obj in curves:
        obj.data.dimensions = "2D"
        obj.data.fill_mode = "BOTH"
        for s in obj.data.splines:
            s.use_cyclic_u = True

    bpy.ops.object.select_all(action="DESELECT")
    for o in curves:
        o.select_set(True)

    bpy.context.view_layer.objects.active = curves[0]
    bpy.ops.object.convert(target="MESH")

    meshes = [o for o in bpy.context.selected_objects if o.type == "MESH"]
    if len(meshes) > 1:
        bpy.ops.object.join()

    logo = bpy.context.active_object
    logo.name = name

    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")

    return logo


# ---------- SCALE + PLACE ----------
def place(
    obj,
    target_x,
    target_y,
    target_width,
    target_rot,
):
    import bpy
    from mathutils import Vector
    import math

    print("\n========== NEW LOGO ==========")
    print("INPUT:", target_x, target_y, target_width, target_rot)

    # -------------------------------------------------
    # APPLY TRANSFORMS FIRST (important for clean bbox)
    # -------------------------------------------------
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # -------------------------------------------------
    # GET INITIAL BOUNDING BOX
    # -------------------------------------------------
    bbox = [obj.matrix_world @ Vector(v) for v in obj.bound_box]

    min_x = min(v.x for v in bbox)
    max_x = max(v.x for v in bbox)
    min_y = min(v.y for v in bbox)
    max_y = max(v.y for v in bbox)

    width = max_x - min_x
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2

    print("INITIAL BBOX:")
    print("  min:", min_x, min_y)
    print("  max:", max_x, max_y)
    print("  center:", center_x, center_y)
    print("  width:", width)

    # -------------------------------------------------
    # SCALE TO TARGET WIDTH
    # -------------------------------------------------
    if width > 0:
        scale_factor = target_width / width
        obj.scale *= scale_factor

        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # -------------------------------------------------
    # ROTATION
    # -------------------------------------------------
    obj.rotation_euler[2] = math.radians(target_rot)

    # -------------------------------------------------
    # RE-CALCULATE BBOX AFTER SCALE
    # -------------------------------------------------
    bbox = [obj.matrix_world @ Vector(v) for v in obj.bound_box]

    min_x = min(v.x for v in bbox)
    max_x = max(v.x for v in bbox)
    min_y = min(v.y for v in bbox)
    max_y = max(v.y for v in bbox)

    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2

    print("FINAL BBOX:")
    print("  min:", min_x, min_y)
    print("  max:", max_x, max_y)
    print("  center:", center_x, center_y)

    # -------------------------------------------------
    # MOVE USING CENTER (THIS WAS THE BUG)
    # -------------------------------------------------
    dx = target_x - center_x
    dy = target_y - center_y

    obj.location.x += dx
    obj.location.y += dy

    print("MOVE DELTA:", dx, dy)

    # -------------------------------------------------
    # FINAL CHECK
    # -------------------------------------------------
    bbox = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
    min_x = min(v.x for v in bbox)
    min_y = min(v.y for v in bbox)

    print("AFTER MOVE min:", min_x, min_y)

    # -------------------------------------------------
    # SET HEIGHT
    # -------------------------------------------------
    # obj.location.z = z_height


# ---------- EXTRUDE ----------
def extrude_logo(logo, height):
    bpy.ops.object.select_all(action="DESELECT")
    logo.select_set(True)
    bpy.context.view_layer.objects.active = logo

    solid = logo.modifiers.new(name="solid", type="SOLIDIFY")
    solid.thickness = height
    solid.offset = 1

    bpy.ops.object.modifier_apply(modifier=solid.name)


# ---------- MAIN ----------
logos = []

# LOGO A
curvesA = import_svg(svgA)
logoA = build_logo(curvesA, "LOGO_A")

if logoA:
    place(logoA, xA, yA, scaleA, rotA)
    extrude_logo(logoA, heightA)
    logos.append(logoA)

# LOGO B
if svgB != "NONE":
    curvesB = import_svg(svgB)
    logoB = build_logo(curvesB, "LOGO_B")

    if logoB:
        place(logoB, xB, yB, scaleB, rotB)
        extrude_logo(logoB, heightB)
        logos.append(logoB)


# ---------- EXPORT ----------
bpy.ops.object.select_all(action="DESELECT")

for obj in bpy.context.scene.objects:
    if obj.type == "MESH":
        obj.select_set(True)

bpy.ops.wm.stl_export(
    filepath=OUTPUT, export_selected_objects=True, apply_modifiers=True
)
bpy.ops.wm.save_as_mainfile(
    filepath=OUTPUT + "blend.blend", export_selected_objects=True, apply_modifiers=True
)

print("DONE")

import bpy, json, math, sys
from mathutils import Vector
views, out = json.load(open(sys.argv[-2])), sys.argv[-1]
scene = bpy.context.scene
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "OPTIX"; prefs.get_devices()
for d in prefs.devices: d.use = d.type == "OPTIX"
scene.render.engine = "CYCLES"; c = scene.cycles; c.device = "GPU"
c.samples = 96; c.use_adaptive_sampling = True; c.use_denoising = True; c.denoiser = "OPENIMAGEDENOISE"
r = scene.render; r.use_persistent_data = True; r.resolution_percentage = 100; r.image_settings.file_format = "PNG"
import os
DAY = {"none": 0.0, "low": 0.12, "medium": 0.45, "high": 1.0}.get(scene.get("ir_daylight", "high"), 1.0)   # style kit (non-home 20)
if os.environ.get("PROBE_DAYLIGHT") == "1":
    # daytime through the windows, like the dataset's lighting variants: window area-light portals at ~80 W/m2
    for o in bpy.data.objects:
        if o.type == "LIGHT" and o.data.type == "AREA" and o.parent is not None and "Window" in o.parent.name:
            area = (o.data.size * (o.data.size_y if o.data.shape in ("RECTANGLE", "ELLIPSE") else o.data.size))
            o.data.energy = 80.0 * max(area, 0.1) * DAY
    w = scene.world                                             # the sky through the glass follows the kit's daylight too
    if w and w.use_nodes:
        for nd in w.node_tree.nodes:
            if nd.type == "BACKGROUND":
                nd.inputs["Strength"].default_value *= DAY
if os.environ.get("CLAY") == "1":
    # clay check (user 2026-10-16: "does it read as an office with no textures?"): one grey diffuse override for every surface
    clay = bpy.data.materials.new("ir_clay"); clay.use_nodes = True
    clay.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.6, 0.6, 0.6, 1)
    clay.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.8
    bpy.context.view_layer.material_override = clay
cd = bpy.data.cameras.new("cmp"); cam = bpy.data.objects.new("cmp", cd); scene.collection.objects.link(cam); scene.camera = cam


def _mean_L(path):
    """Mean CIE L* of a rendered sRGB PNG (style_metrics' formula)."""
    import numpy as np
    im = bpy.data.images.load(path); a = np.array(im.pixels[:]).reshape(-1, 4)[:, :3]; bpy.data.images.remove(im)
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    Y = lin @ np.array([0.2126, 0.7152, 0.0722])
    f = np.where(Y > 0.008856, np.cbrt(Y), 7.787 * Y + 16 / 116)
    return float((116 * f - 16).mean())


if os.environ.get("REF_L"):
    # auto-exposure toward the reference's mean lightness (a camera setting): two low-res test frames of the first wide view
    target = float(os.environ["REF_L"]); wide = next((p for p in views if "wide" in p["name"]), views[0])
    loc, tgt = Vector(wide["location"]), Vector(wide["target"]); cam.location = loc
    cam.rotation_euler = (tgt - loc).to_track_quat("-Z", "Y").to_euler(); cd.angle = math.radians(wide["hfov"])
    keep = (c.samples, r.resolution_x, r.resolution_y); c.samples = 24; r.resolution_x, r.resolution_y = 160, 120
    for _ in range(2):
        r.filepath = f"{out}/_exposure_probe.png"; bpy.ops.render.render(write_still=True)
        L = _mean_L(r.filepath)
        Y = lambda l: ((l + 16) / 116) ** 3                     # noqa: E731
        ev = max(-1.5, min(1.0, math.log2(Y(target) / max(Y(L), 1e-4))))
        scene.view_settings.exposure = max(-2.5, min(1.5, scene.view_settings.exposure + ev))
        print(f"[exposure] probe L {L:.1f} target {target:.1f} -> exposure {scene.view_settings.exposure:+.2f}", flush=True)
    os.remove(r.filepath)
    c.samples, r.resolution_x, r.resolution_y = keep
cd.sensor_fit = "HORIZONTAL"; cd.clip_start = 0.05
for p in views:
    cd.angle = math.radians(p["hfov"]); r.resolution_x, r.resolution_y = p["res"]
    loc, tgt = Vector(p["location"]), Vector(p["target"])
    cam.location = loc; cam.rotation_euler = (tgt - loc).to_track_quat("-Z", "Y").to_euler()
    r.filepath = f"{out}/{p['name']}.png"
    bpy.ops.render.render(write_still=True)
    print("[view]", p["name"], flush=True)

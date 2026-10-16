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
if os.environ.get("PROBE_DAYLIGHT") == "1":
    # daytime through the windows, like the dataset's lighting variants: window area-light portals at ~80 W/m2
    for o in bpy.data.objects:
        if o.type == "LIGHT" and o.data.type == "AREA" and o.parent is not None and "Window" in o.parent.name:
            area = (o.data.size * (o.data.size_y if o.data.shape in ("RECTANGLE", "ELLIPSE") else o.data.size))
            o.data.energy = 80.0 * max(area, 0.1)
if os.environ.get("CLAY") == "1":
    # clay check (user 2026-10-16: "does it read as an office with no textures?"): one grey diffuse override for every surface
    clay = bpy.data.materials.new("ir_clay"); clay.use_nodes = True
    clay.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.6, 0.6, 0.6, 1)
    clay.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.8
    bpy.context.view_layer.material_override = clay
cd = bpy.data.cameras.new("cmp"); cam = bpy.data.objects.new("cmp", cd); scene.collection.objects.link(cam); scene.camera = cam
cd.sensor_fit = "HORIZONTAL"; cd.clip_start = 0.05
for p in views:
    cd.angle = math.radians(p["hfov"]); r.resolution_x, r.resolution_y = p["res"]
    loc, tgt = Vector(p["location"]), Vector(p["target"])
    cam.location = loc; cam.rotation_euler = (tgt - loc).to_track_quat("-Z", "Y").to_euler()
    r.filepath = f"{out}/{p['name']}.png"
    bpy.ops.render.render(write_still=True)
    print("[view]", p["name"], flush=True)

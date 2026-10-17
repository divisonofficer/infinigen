import bpy, json, math, os, sys
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
views, out = json.load(open(args[0])), args[1]
want = args[2].split(",") if len(args) > 2 else None
if want is None:                                              # the first wide of every room
    seen, want = set(), []
    for v in views:
        room = v["name"].split("_wide")[0]
        if "_wide" in v["name"] and room not in seen:
            seen.add(room); want.append(v["name"])
views = [v for v in views if v["name"] in want]
os.makedirs(out, exist_ok=True)
scene = bpy.context.scene
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "OPTIX"; prefs.get_devices()
for d in prefs.devices: d.use = d.type == "OPTIX"
scene.render.engine = "CYCLES"; c = scene.cycles; c.device = "GPU"
c.samples = 32; c.use_adaptive_sampling = False; c.use_denoising = False
vl = bpy.context.view_layer
vl.use_pass_diffuse_color = True; vl.use_pass_glossy_color = True; vl.use_pass_normal = True


def const(nt, v):
    n = nt.nodes.new("ShaderNodeValue"); n.outputs[0].default_value = float(v); return n.outputs[0]


covered = total = 0
trees = [(m.name, m.node_tree) for m in bpy.data.materials if m.use_nodes and m.users] + \
        [(g.name, g) for g in bpy.data.node_groups if g.bl_idname == "ShaderNodeTree" and g.users]   # Principled inside groups too
for name, nt in trees:
    total += 1
    ps = [x for x in nt.nodes if x.type == "BSDF_PRINCIPLED"]
    if not ps:
        continue
    covered += 1
    for b in ps:
        for aov, sock in (("GT_R", "Roughness"), ("GT_M", "Metallic")):
            n = nt.nodes.new("ShaderNodeOutputAOV"); n.aov_name = aov
            src = b.inputs[sock].links[0].from_socket if b.inputs[sock].is_linked else const(nt, b.inputs[sock].default_value)
            nt.links.new(src, n.inputs["Value"])
for aov in ("GT_R", "GT_M"):
    a = vl.aovs.add(); a.name = aov; a.type = "VALUE"
print(f"GTCOVERAGE trees with a Principled {covered} of {total} (materials + node groups)", flush=True)

scene.use_nodes = True
tree = scene.node_tree
for n in list(tree.nodes): tree.nodes.remove(n)
rl = tree.nodes.new("CompositorNodeRLayers")


def fout(name, color_mode, raw):
    f = tree.nodes.new("CompositorNodeOutputFile"); f.base_path = out
    f.format.file_format = "PNG"; f.format.color_mode = color_mode; f.format.color_depth = "8"
    f.format.color_management = "OVERRIDE"; f.format.view_settings.view_transform = "Raw" if raw else "Standard"
    f.format.view_settings.look = "None"
    f.file_slots[0].path = name + "_"
    return f


def mix(blend, a, b_col):
    mx = tree.nodes.new("CompositorNodeMixRGB"); mx.blend_type = blend; mx.inputs[0].default_value = 1.0
    mx.inputs[2].default_value = b_col
    tree.links.new(a, mx.inputs[1]); return mx.outputs[0]


albedo_o = fout("albedo", "RGB", False); normal_o = fout("normal", "RGB", True)
rough_o = fout("rough", "BW", True); metal_o = fout("metal", "BW", True)
alb = tree.nodes.new("CompositorNodeMixRGB"); alb.blend_type = "ADD"; alb.inputs[0].default_value = 1.0
tree.links.new(rl.outputs["DiffCol"], alb.inputs[1]); tree.links.new(rl.outputs["GlossCol"], alb.inputs[2])
tree.links.new(alb.outputs[0], albedo_o.inputs[0])
half = (0.5, 0.5, 0.5, 1.0)
nrm = mix("ADD", mix("MULTIPLY", rl.outputs["Normal"], half), half)
tree.links.new(nrm, normal_o.inputs[0])
tree.links.new(rl.outputs["GT_R"], rough_o.inputs[0]); tree.links.new(rl.outputs["GT_M"], metal_o.inputs[0])

cd = bpy.data.cameras.new("gt"); cam = bpy.data.objects.new("gt", cd); scene.collection.objects.link(cam); scene.camera = cam
cd.sensor_fit = "HORIZONTAL"; cd.clip_start = 0.05
r = scene.render; r.use_persistent_data = True; r.resolution_percentage = 100
scene.frame_current = 1
for p in views:
    cd.angle = math.radians(p["hfov"]); r.resolution_x, r.resolution_y = p["res"]
    loc, tgt = Vector(p["location"]), Vector(p["target"])
    cam.location = loc; cam.rotation_euler = (tgt - loc).to_track_quat("-Z", "Y").to_euler()
    for f, ch in ((albedo_o, "albedo"), (normal_o, "normal"), (rough_o, "rough"), (metal_o, "metal")):
        f.file_slots[0].path = f"{p['name']}_{ch}_"
    r.filepath = f"{out}/_rgb_unused.png"
    bpy.ops.render.render(write_still=True)
    print("[gt]", p["name"], flush=True)
for fn in os.listdir(out):                                      # drop Blender's frame suffix: <view>_<ch>_0001.png -> <view>_<ch>.png
    if fn.endswith("_0001.png"):
        os.replace(os.path.join(out, fn), os.path.join(out, fn[:-len("_0001.png")] + ".png"))
if os.path.exists(f"{out}/_rgb_unused.png"):
    os.remove(f"{out}/_rgb_unused.png")

"""Run inside Blender 4.2: replace the room shells' wall / floor / ceiling materials of an Infinigen 1.x scene.blend with
Infinigen 2.0 ones (wall_material_rand, floor_material_rand, ceiling_material_rand), deterministically from a seed.

    blender --background IN.blend --python rematerial_rooms_infinigen2.py -- --out OUT.blend --seed N [--site DIR]

Ceilings are left as they are (shader_invisible in Infinigen 1.x; the IR pipeline caps and lights rooms itself).
Tested 2026-10-08 on 62912187: the production bake accepted it (ok, 233 min vs 223, no exclusions) and the baked
atlases keep the patterns (tiles, plaster, carpet).

The 2.0 shaders read metre-scale UVs from a new map "m_uv" (planar per face by its dominant normal axis, as 2.0's own rooms do);
the object's existing UV maps and their active/render flags are left alone, so a later bake still sees what it saw before.
"""
import argparse
import math, json, os, re, sys, time
argv = sys.argv[sys.argv.index("--") + 1:]
ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--seed", type=int, required=True)
ap.add_argument("--venue", default="", help="cafe | grocery: finishes for a relabelled single-room layout")
ap.add_argument("--style", default="", help="venue style preset name (room_planner/styles.py) or a reference spec .json")
ap.add_argument("--site", default=os.environ.get("INFINIGEN2_SITE", "/root/robomituba-envs/infinigen2-2.0.0a2-site"),
                help="pip --target dir holding infinigen 2.0.0a2, procfunc 0.35.1 and numpy 1.26 (Blender 4.2 ships numpy 1.24)")
a = ap.parse_args(argv)
sys.path.insert(0, a.site)
import bpy
import numpy as np
import procfunc as pf
from infinigen2.shaders import functionality_lists as fl
from infinigen2.shaders.composites import tiles

t0 = time.time()
PAT = re.compile(r"^(?P<room>[a-z-]+_\d+/\d+)\.(?P<part>wall|floor)$")   # ceilings stay shader_invisible: the IR pipeline lights and caps rooms itself
FNS = {"wall": fl.wall_material_rand, "floor": fl.floor_material_rand, "ceiling": fl.ceiling_material_rand}
# 2.0 has one wall list for every room; a bathroom with wood-plank walls reads wrong (user 2026-10-13). Wet rooms get tiles/paint.
WET_ROOMS = {"bathroom", "restroom"}


def wet_wall(rng, vec):
    rng_choice, rng_func = rng.spawn(2)
    return pf.control.choice(rng_choice, [(tiles.tile_indoor_wall_rand, 2.0), (fl.paint_wall_rand, 1.0)])(rng_func, vec)


WET_FNS = {"wall": wet_wall, "floor": tiles.tile_indoor_ground_rand}

# Workplaces stand on concrete (a carpet-patterned warehouse read wrong, user 2026-10-16); half get a scratch/splat overlay.
WORK_ROOMS = {"warehouse", "garage", "utility"}


def work_floor(rng, vec):
    from infinigen2.shaders.base_materials import concrete
    rng_choice, rng_func = rng.spawn(2)
    return pf.control.choice(rng_choice, [(lambda r, v: concrete.concrete_rand(r, v), 1.0),
                                          (lambda r, v: fl._layer_rand(r, v, concrete.concrete_rand(r, v)), 1.0)])(rng_func, vec)


WORK_FNS = {"wall": fl.wall_material_rand, "floor": work_floor}

# Offices get painted walls (a dark mottled stone break room read wrong, user 2026-10-16): paint mostly, sometimes a wood-plank or
# smooth-concrete feature wall; no granite/gravel/flaked/patterned. Floors: carpet, wood planks or plain tiles.
OFFICE_ROOMS = {"office", "open-office", "meeting-room", "break-room", "factory-office"}


def office_wall(rng, vec):
    """Commercial interior paint (user 2026-10-16: wallpaper and coloured walls read as a house): warm white, off-white, light grey;
    the architecture pass adds the charcoal accent wall."""
    rng_choice, rng_func = rng.spawn(2)
    return pf.control.choice(rng_choice, [(_paint((0.87, 0.86, 0.83)), 2.0), (_paint((0.82, 0.82, 0.8)), 2.0),
                                          (_paint((0.68, 0.69, 0.69)), 1.0)])(rng_func, vec)


def office_floor(rng, vec):
    """~70% carpet tile, 30% polished concrete; no wood (critic r1 2026-10-16: a wood-plank meeting room read as a dining room)."""
    rng_choice, rng_func = rng.spawn(2)
    return pf.control.choice(rng_choice, [(fl.carpet.carpet_rand, 7.0), (fl.concrete.concrete_rand, 3.0)])(rng_func, vec)


OFFICE_FNS = {"wall": office_wall, "floor": office_floor}


def cafe_wall(rng, vec):
    from infinigen2.shaders.composites import bricks
    rng_choice, rng_func = rng.spawn(2)
    return pf.control.choice(rng_choice, [(_bricks, 2.5), (bricks.bricks_paint_rand, 1.0), (fl.wood_planks.wood_planks_rand, 1.5),
                                          (fl.paint_wall_rand, 2.0), (tiles.tile_indoor_wall_rand, 0.5)])(rng_func, vec)


def cafe_floor(rng, vec):
    rng_choice, rng_func = rng.spawn(2)
    return pf.control.choice(rng_choice, [(fl.wood_planks.wood_planks_rand, 3.0), (tiles.tile_indoor_ground_rand, 1.5),
                                          (fl.concrete.concrete_rand, 1.0)])(rng_func, vec)


def _pick(*options):
    def fn(rng, vec):
        rng_choice, rng_func = rng.spawn(2)
        return pf.control.choice(rng_choice, list(options))(rng_func, vec)
    return fn


def _bricks(rng, vec):
    """Exposed red brick (user 2026-10-16: 'the brick-brick cafes disappeared'): bricks_rand mostly gives grey/painted/cobble walls."""
    from infinigen2.shaders.composites import bricks
    rng_choice, _ = rng.spawn(2)
    return pf.control.choice(rng_choice, [(lambda r, v: bricks.bricks_red_preset(v), 3.0), (lambda r, v: bricks.bricks_red_concave_preset(v), 2.0),
                                          (lambda r, v: bricks.brick_masonry_brown_preset(v), 1.0)])(rng, vec)


def _paint(rgb):
    def fn(rng, vec):
        return fl.paint.paint_rand(rng, vec, displacement_pct=0.15, base_color=pf.Color(tuple(rgb)))
    return fn


def style_walls(st):
    """A style's (or reference spec's) wall finish: paint in its colour, brick, concrete, wood panel or tile."""
    finish = st.get("wall", "paint")
    if finish == "paint":
        return _paint(st.get("wall_rgb") or (0.85, 0.83, 0.78))
    return {"brick": _bricks, "concrete": fl.concrete.concrete_rand, "wood_panel": fl.wood_planks.wood_planks_rand,
            "tile": tiles.tile_indoor_wall_rand}[finish]


STYLE_FLOORS = {"wood": fl.wood_planks.wood_planks_rand, "concrete": fl.concrete.concrete_rand, "tile": tiles.tile_indoor_ground_rand}

#: --venue relabels a single-room layout (plan_scene --venue): its rooms get that venue's finishes
VENUE_FNS = {"cafe": {"wall": cafe_wall, "floor": cafe_floor},
             "grocery": {"wall": _paint((0.88, 0.88, 0.86)), "floor": tiles.tile_indoor_ground_rand},   # a sales floor, not a stockroom
             "break-room": {"wall": office_wall, "floor": fl.concrete.concrete_rand}}   # office pantry: not carpet (r2), not glossy green herringbone tile (r3)


def planar_group():
    """Node group 'm_planar': world position projected on the plane its normal faces most (x->yz, y->xz, z->xy), in metres.
    Computed in the shader so it survives the bake's mesh export, which drops extra UV layers."""
    g = bpy.data.node_groups.get("m_planar")
    if g:
        return g
    g = bpy.data.node_groups.new("m_planar", "ShaderNodeTree")
    g.interface.new_socket("Vector", in_out="OUTPUT", socket_type="NodeSocketVector")
    n = g.nodes; L = g.links
    geo = n.new("ShaderNodeNewGeometry"); out = n.new("NodeGroupOutput")
    sp = n.new("ShaderNodeSeparateXYZ"); L.new(geo.outputs["Position"], sp.inputs[0])
    nabs = n.new("ShaderNodeVectorMath"); nabs.operation = "ABSOLUTE"; L.new(geo.outputs["Normal"], nabs.inputs[0])
    sn = n.new("ShaderNodeSeparateXYZ"); L.new(nabs.outputs[0], sn.inputs[0])
    def cmp(a, b):  # 1 where a >= b
        m = n.new("ShaderNodeMath"); m.operation = "GREATER_THAN"; L.new(a, m.inputs[0]); L.new(b, m.inputs[1]); return m.outputs[0]
    def mx(a, b):
        m = n.new("ShaderNodeMath"); m.operation = "MAXIMUM"; L.new(a, m.inputs[0]); L.new(b, m.inputs[1]); return m.outputs[0]
    x_dom = n.new("ShaderNodeMath"); x_dom.operation = "MULTIPLY"
    L.new(cmp(sn.outputs[0], sn.outputs[1]), x_dom.inputs[0]); L.new(cmp(sn.outputs[0], sn.outputs[2]), x_dom.inputs[1])
    z_dom = cmp(sn.outputs[2], mx(sn.outputs[0], sn.outputs[1]))
    vx = n.new("ShaderNodeCombineXYZ"); L.new(sp.outputs[1], vx.inputs[0]); L.new(sp.outputs[2], vx.inputs[1])   # x-facing: (y, z)
    vy = n.new("ShaderNodeCombineXYZ"); L.new(sp.outputs[0], vy.inputs[0]); L.new(sp.outputs[2], vy.inputs[1])   # y-facing: (x, z)
    vz = n.new("ShaderNodeCombineXYZ"); L.new(sp.outputs[0], vz.inputs[0]); L.new(sp.outputs[1], vz.inputs[1])   # z-facing: (x, y)
    m1 = n.new("ShaderNodeMix"); m1.data_type = "VECTOR"; L.new(x_dom.outputs[0], m1.inputs["Factor"])
    L.new(vy.outputs[0], m1.inputs[4]); L.new(vx.outputs[0], m1.inputs[5])
    m2 = n.new("ShaderNodeMix"); m2.data_type = "VECTOR"; L.new(z_dom, m2.inputs["Factor"])
    L.new(m1.outputs[1], m2.inputs[4]); L.new(vz.outputs[0], m2.inputs[5])
    L.new(m2.outputs[1], out.inputs[0])
    return g


def rewire_to_planar(mat):
    """Feed every input the 'm_uv' UV-map node fed from the m_planar group instead, then drop the UV-map nodes."""
    nt = mat.node_tree; grp = planar_group(); n = 0
    for node in list(nt.nodes):
        if node.bl_idname == "ShaderNodeUVMap" and node.uv_map == "m_uv":
            gn = nt.nodes.new("ShaderNodeGroup"); gn.node_tree = grp
            for link in list(node.outputs[0].links):
                nt.links.new(gn.outputs[0], link.to_socket)
            nt.nodes.remove(node); n += 1
    return n


def level_wall_patterns(mat) -> int:
    """2.0 tile/brick shaders rotate their pattern by k*90 deg (+45 deg 30% of the time): fine on a floor, but bricks on a wall run
    horizontal. Snap every unlinked Mapping rotation to a multiple of 180 deg (rows stay horizontal, the pattern may flip)."""
    n = 0
    for node in mat.node_tree.nodes:
        if node.bl_idname != "ShaderNodeMapping" or node.inputs["Rotation"].is_linked:
            continue
        x, y, z = node.inputs["Rotation"].default_value
        level = (0.0, 0.0, round(z / math.pi) * math.pi)
        if (x, y, z) != level:
            node.inputs["Rotation"].default_value = level
            n += 1
    return n


STYLE_FNS = {}
if a.style:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from room_planner import styles as _styles
    _st = json.load(open(a.style)) if a.style.endswith(".json") else _styles.get(a.venue, a.style)   # preset name or spec file
    STYLE_FNS = {"wall": style_walls(_st), "floor": STYLE_FLOORS[_st.get("floor", "wood")]}
targets = sorted((o for o in bpy.data.objects if o.type == "MESH" and PAT.match(o.name)), key=lambda o: o.name)
rng = np.random.default_rng(a.seed)
record = []
for o in targets:
    part = PAT.match(o.name).group("part")
    (r,) = rng.spawn(1)
    before = [s.material.name for s in o.material_slots if s.material]
    room_type = PAT.match(o.name).group("room").split("_")[0]
    fns = (STYLE_FNS if STYLE_FNS and room_type not in WET_ROOMS else
           VENUE_FNS[a.venue] if a.venue in VENUE_FNS and room_type not in WET_ROOMS else WET_FNS if room_type in WET_ROOMS
           else WORK_FNS if room_type in WORK_ROOMS else OFFICE_FNS if room_type in OFFICE_ROOMS else FNS)
    mat = fns[part](r, pf.nodes.shader.uv_map(uv_map="m_uv"))
    pf.ops.object.set_material(pf.types.MeshObject(o), material=mat)
    after = [s.material.name for s in o.material_slots if s.material]
    rewired = sum(rewire_to_planar(s.material) for s in o.material_slots if s.material)
    assert rewired > 0, f"{o.name}: no m_uv node to rewire"
    leveled = sum(level_wall_patterns(s.material) for s in o.material_slots if s.material) if part == "wall" else 0
    record.append({"object": o.name, "part": part, "before": before, "after": after, "rewired_uv_nodes": rewired,
                   "leveled_mappings": leveled})
bpy.ops.wm.save_as_mainfile(filepath=a.out, copy=True)
json.dump({"seed": a.seed, "objects": record, "seconds": round(time.time() - t0, 1), "generator": "infinigen 2.0.0a2 functionality_lists"},
          open(a.out + ".rematerial.json", "w"), indent=1)
print("REMATERIAL", len(record), "objects in", round(time.time() - t0, 1), "s", flush=True)

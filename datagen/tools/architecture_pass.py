"""Architectural envelope for a commercial room (user 2026-10-16: the cafes read as "an empty box with cafe objects in it").

Runs in Blender on the rematerialled blend, BEFORE the room plan, so the planner sees the structure as existing objects and furnishes
around it:

  pilasters    0.3-0.45 m piers on long walls every 3-4 m (and a free-standing column in rooms over 60 m2)
  beams        down-stand beams across the short span, aligned with the pilasters
  soffit       a dropped bulkhead (0.35 m) along the back wall: where a counter sits in a real shop
  accent wall  one long wall gets the palette's accent material (a second material slot on the wall mesh, faces by plane)
  ceiling kit  a duct run along the room, a pipe pair, track rails with spot heads (+ narrow spot lights), an AC cassette, sprinkler
               heads -- the medium-frequency detail that gives a ceiling its depth and scale

    python architecture_pass.py IN.blend --out OUT.blend --seed N [--palette spec.json]   (infinigen env, bpy as a module)

Every object is named <Kind>Factory(seed).spawn_asset(i) like the rest, so extract_rooms / obstacles / the board see them. Ceiling
objects hang above 2.3 m and are listed as HANGING (no floor footprint).
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import furnish_rooms as fr  # noqa: E402
import room_dressing as rd  # noqa: E402
from room_planner import proc_assets as pa  # noqa: E402

#: per-element odds by archetype (user 2026-10-16: one fixed kit made every cafe the same shell; thick columns read as a car park)
ARCHETYPES = {
    "modern":     dict(pilaster=.6, beam=.5, column=.5, soffit=.7, duct=.2, pipe=.15, track=.8, ac=.6, sprinkler=.8),
    "industrial": dict(pilaster=.7, beam=.8, column=.6, soffit=.4, duct=.8, pipe=.7, track=.7, ac=.3, sprinkler=.8),
    "warm":       dict(pilaster=.4, beam=.3, column=.3, soffit=.6, duct=.05, pipe=.05, track=.4, ac=.4, sprinkler=.6),
    "bakery":     dict(pilaster=.3, beam=.2, column=.2, soffit=.8, duct=.1, pipe=.05, track=.5, ac=.5, sprinkler=.7),
    "office":     dict(pilaster=0, beam=0, column=.3, soffit=0, duct=0, pipe=0, track=0, ac=.3, sprinkler=.9, grid=1),
    "office_exposed": dict(pilaster=0, beam=.7, column=.4, soffit=0, duct=.6, pipe=.3, track=0, ac=1, sprinkler=.9, grid=0, linear=1),
    "warehouse":  dict(pilaster=.3, beam=0, column=.5, soffit=0, duct=.4, pipe=.8, track=0, ac=0, sprinkler=1, warehouse=1),
    "default":    dict(pilaster=.6, beam=.6, column=.6, soffit=.6, duct=.35, pipe=.3, track=.7, ac=.45, sprinkler=.8),
}

PALETTE_DEFAULT = {"frame": (0.03, 0.03, 0.03), "structure": (0.82, 0.81, 0.78), "duct": (0.62, 0.62, 0.64),
                   "accent": (0.16, 0.17, 0.18)}


def _mat(name, rgb, rough=0.6, metallic=0.0):
    return pa._flat(name, tuple(rgb), rough, metallic)


def _box(name, parts, mat):
    return pa._parts_object(name, [(mat, parts)])


def _cyl(name, p0, p1, r, mat, n=12):
    import bmesh
    v = Vector(p1) - Vector(p0)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=n, radius1=r, radius2=r, depth=v.length)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(mat)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    o.location = (Vector(p0) + Vector(p1)) / 2
    o.rotation_mode = "QUATERNION"; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(v.normalized())
    return o


def office_ceiling(L, S, zc, at, name, rng, stats):
    """Drop-ceiling grid (0.6 m T-bars), linear LED rows every ~2.4 m with an area light each, HVAC diffusers, smoke detectors: the
    repeated ceiling rhythm that reads 'office' in perspective (user 2026-10-16)."""
    tbar = _mat("ir_tbar", (0.62, 0.62, 0.62), 0.4, 0.5)   # darker than the tiles so the grid reads at eye level (critic r1)
    grid = [(at(u, S / 2)[0], at(u, S / 2)[1], zc - 0.01, 0.03, S, 0.02) for u in [k * 0.6 for k in range(1, int(L / 0.6))]]
    grid += [(at(L / 2, v)[0], at(L / 2, v)[1], zc - 0.01, L, 0.03, 0.02) for v in [k * 0.6 for k in range(1, int(S / 0.6))]]
    _box(name("CeilingGrid"), grid, tbar)
    led = pa._flat("ir_led_panel", (1.0, 1.0, 1.0), 0.3)
    nt = led.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Emission Color"].default_value = (1.0, 0.97, 0.92, 1); b.inputs["Emission Strength"].default_value = 4.0
    rows = max(1, int(S / 2.4))
    for r_ in range(rows):
        v = S * (r_ + 0.5) / rows
        n = max(1, int((L - 0.6) / 1.8))
        for k in range(n):
            u = 0.6 + (k + 0.5) * (L - 1.2) / n
            cx, cy = at(u, v)
            _box(name("LinearLed"), [(cx, cy, zc - 0.02, 1.2, 0.3, 0.03)], led)   # a 1200x300 troffer panel
            ld = bpy.data.lights.new(f"ir_led_{r_}_{k}", "AREA"); ld.shape = "RECTANGLE"; ld.size = 1.2; ld.size_y = 0.3; ld.energy = 45.0
            lo = bpy.data.objects.new(f"PointLampFactory(led).spawn_asset({r_}_{k})", ld)
            bpy.context.scene.collection.objects.link(lo); lo.location = (cx, cy, zc - 0.05)
            stats["linear_leds"] = stats.get("linear_leds", 0) + 1
    diff = _mat("ir_diffuser", (0.78, 0.78, 0.77), 0.5, 0.2)
    for k in range(max(1, int(L / 3.0))):
        cx, cy = at(1.5 + k * 3.0, S * (0.25 if k % 2 else 0.75))
        _box(name("Diffuser"), [(cx, cy, zc - 0.015, 0.6, 0.6, 0.02), (cx, cy, zc - 0.03, 0.4, 0.4, 0.02)], diff)
        cx, cy = at(1.5 + k * 3.0, S * 0.5)
        _cyl(name("SmokeDetector"), (cx, cy, zc - 0.005), (cx, cy, zc - 0.04), 0.06, _mat("ir_ac_white", (0.86, 0.86, 0.85), 0.4), n=16)


def linear_pendants(L, S, zc, at, name, rng, stats):
    """Exposed-ceiling office: slim linear LED pendants on two rods at ~2.55 m in rows, an AC cassette every ~4 m (reference photo
    2026-10-16)."""
    body = _mat("ir_linear_body", (0.06, 0.06, 0.06), 0.4, 1.0)
    led = pa._flat("ir_led_panel", (1.0, 1.0, 1.0), 0.3)
    led.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (1.0, 0.97, 0.92, 1)
    led.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 4.0
    rows = max(1, int(S / 2.2)); z = min(zc - 0.4, 2.6)
    for r_ in range(rows):
        v = S * (r_ + 0.5) / rows
        n = max(1, int((L - 0.8) / 2.0))
        for k in range(n):
            u = 0.4 + (k + 0.5) * (L - 0.8) / n
            cx, cy = at(u, v)
            _box(name("LinearPendant"), [(cx, cy, z, 1.5, 0.06, 0.06), (cx - 0.65, cy, (z + zc) / 2, 0.006, 0.006, zc - z),
                                          (cx + 0.65, cy, (z + zc) / 2, 0.006, 0.006, zc - z)], body)
            _box(name("LinearLed"), [(cx, cy, z - 0.031, 1.46, 0.045, 0.004)], led)
            ld = bpy.data.lights.new(f"ir_lin_{r_}_{k}", "AREA"); ld.shape = "RECTANGLE"; ld.size = 1.45; ld.size_y = 0.05; ld.energy = 50.0
            lo = bpy.data.objects.new(f"PointLampFactory(linear).spawn_asset({r_}_{k})", ld)
            bpy.context.scene.collection.objects.link(lo); lo.location = (cx, cy, z - 0.04)
            stats["linear_pendants"] = stats.get("linear_pendants", 0) + 1
    ac = _mat("ir_ac_white", (0.86, 0.86, 0.85), 0.4)
    for k in range(max(1, int(L / 4.0))):
        cx, cy = at(2.0 + k * 4.0, S * (0.3 if k % 2 else 0.7))
        _box(name("AcCassette"), [(cx, cy, zc - 0.04, 0.84, 0.84, 0.06), (cx, cy, zc - 0.09, 0.62, 0.62, 0.04)], ac)


def warehouse_roof(L, S, zc, at, name, rng, stats):
    """Industrial roof (warehouse r1 critic: 'a flat white plaster ceiling with dome/pendant lights reads as a basement'): a
    corrugated deck of ribs, steel girders every ~4.5 m with purlins, and high-bay dome lights on cords in rows over the aisles.
    Infinigen's ceiling pucks in the room are removed, so the fixture pass does not hang household lamps here."""
    steel = _mat("ir_wh_steel", rng.choice(((0.32, 0.36, 0.42), (0.55, 0.56, 0.58), (0.12, 0.2, 0.36))), 0.5, 0.6)
    deck = _mat("ir_wh_deck", (0.62, 0.63, 0.64), 0.45, 0.8)
    alu = _mat("ir_wh_alu", (0.8, 0.8, 0.82), 0.3, 1.0)
    glow = pa._flat("ir_highbay_glow", (1.0, 1.0, 1.0), 0.3)
    glow.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (1.0, 0.97, 0.92, 1)
    glow.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 12.0
    ribs = [(*at(L / 2, S / 2), zc - 0.004, L, S, 0.008)]      # the deck sheet hides the plaster; ribs give it the corrugation
    ribs += [(*at(0.15 + k * 0.3, S / 2), zc - 0.035, 0.1, S, 0.06) for k in range(int(L / 0.3))]
    _box(name("RoofDeck"), ribs, deck)
    gird = []
    n_g = max(1, round(L / 4.5))
    for k in range(1, n_g):
        cx, cy = at(L * k / n_g, S / 2)
        gird += [(cx, cy, zc - 0.08, 0.2, S, 0.02), (cx, cy, zc - 0.5, 0.2, S, 0.02), (cx, cy, zc - 0.29, 0.015, S, 0.42)]
    for v in [0.6 + k * 1.2 for k in range(int((S - 0.6) / 1.2))]:
        cx, cy = at(L / 2, v)
        gird.append((cx, cy, zc - 0.14, L, 0.08, 0.15))
    _box(name("RoofGirder"), gird, steel)
    rows = max(2, round(S / 4.0)); per = max(2, round(L / 4.0)); zh = zc - rng.uniform(0.9, 1.3)
    for r_ in range(rows):
        for k in range(per):
            cx, cy = at(L * (k + 0.5) / per, S * (r_ + 0.5) / rows)
            # linear strip fixtures on chains along the aisles (wh r16: dome high-bays seen from below read as flat residential discs)
            for dx in (-0.6, 0.6):
                _cyl(name("HighBayCord"), (cx + dx, cy, zc - 0.05), (cx + dx, cy, zh + 0.04), 0.006, steel, n=6)
            o = pa._prims(name("HighBayLamp"), [(alu, [("box", (cx, cy, zh), (1.5, 0.16, 0.08), (0, 0, 0)),
                                                       ("box", (cx, cy + 0.07, zh - 0.05), (1.5, 0.02, 0.06), (0, 0, 0)),
                                                       ("box", (cx, cy - 0.07, zh - 0.05), (1.5, 0.02, 0.06), (0, 0, 0))]),
                                                (glow, [("box", (cx, cy, zh - 0.045), (1.44, 0.12, 0.01), (0, 0, 0))])])
            ld = bpy.data.lights.new(f"ir_highbay_{r_}_{k}", "POINT"); ld.energy = 350.0; ld.color = (1.0, 0.97, 0.92); ld.shadow_soft_size = 0.2
            lo = bpy.data.objects.new(f"PointLampFactory(highbay).spawn_asset({r_}_{k})", ld)
            bpy.context.scene.collection.objects.link(lo); lo.location = (cx, cy, zh - 0.3)
            stats["highbay"] = stats.get("highbay", 0) + 1
    x0, x1 = min(at(0, 0)[0], at(L, S)[0]), max(at(0, 0)[0], at(L, S)[0])
    y0, y1 = min(at(0, 0)[1], at(L, S)[1]), max(at(0, 0)[1], at(L, S)[1])
    for o in [o for o in bpy.data.objects if rd._factory(o.name) == "CeilingLightFactory"]:
        t = o.matrix_world.translation
        if x0 <= t.x <= x1 and y0 <= t.y <= y1:
            for c in list(o.children_recursive):
                bpy.data.objects.remove(c, do_unlink=True)
            bpy.data.objects.remove(o, do_unlink=True)
            stats["pucks_removed"] = stats.get("pucks_removed", 0) + 1


def room_frame(room):
    """(x0, x1, y0, y1, floor z, ceiling z) of a roughly rectangular room, from its floor and wall meshes."""
    x0, x1, y0, y1 = room.box
    ceil = max((room.wall.matrix_world @ Vector(c)).z for c in room.wall.bound_box)
    return x0, x1, y0, y1, room.z, ceil


def accent_wall(room, mat, rng, stats):
    """Second material on the faces of one long wall (the one opposite the door if known, else random of the two)."""
    me, mw = room.wall.data, room.wall.matrix_world
    x0, x1, y0, y1 = room.box
    axis, at_ = rng.choice((("y", y1), ("y", y1), ("x", x0), ("x", x1)))   # back wall (behind the counter) or a side wall; never the glass
    if mat.name not in [m.name for m in me.materials if m]:
        me.materials.append(mat)
    slot = [m.name if m else "" for m in me.materials].index(mat.name)
    hit = 0
    for p in me.polygons:
        c = mw @ p.center; n = (mw.to_3x3() @ p.normal).normalized()
        if abs(n.z) > 0.3:
            continue
        if (abs(c.y - at_) < 0.25 and abs(n.y) > 0.8) if axis == "y" else (abs(c.x - at_) < 0.25 and abs(n.x) > 0.8):
            p.material_index = slot; hit += 1
    stats["accent_faces"] = stats.get("accent_faces", 0) + hit
    return axis, round(at_, 2)


def build(room, rng, pal, stats, seed, track=True, archetype="default"):
    odds = ARCHETYPES.get(archetype, ARCHETYPES["default"])
    has = {k: rng.random() < p for k, p in odds.items()}
    has["track"] = has["track"] and track
    stats["archetype"], stats["elements"] = archetype, sorted(k for k, v in has.items() if v)
    x0, x1, y0, y1, z0, zc = room_frame(room)
    W, D = x1 - x0, y1 - y0
    long_x = True                                               # u = x, v = y: the storefront is the y0 wall, the back wall y1
    L, S = W, D
    struct = _mat("ir_arch_structure", pal["structure"], 0.85)
    frame = _mat("ir_arch_black_metal", pal["frame"], 0.4, 1.0)
    duct = _mat("ir_arch_duct", pal["duct"], 0.35, 1.0)
    i = [0]

    def name(kind):
        i[0] += 1
        return f"{kind}Factory({seed}).spawn_asset({i[0]})"

    def at(u, v):                                               # u along the long axis, v across (room frame -> world)
        return (x0 + u, y0 + v) if long_x else (x0 + v, y0 + u)

    # pilasters + beams every 3-4 m along the long walls
    bays = max(1, round(L / rng.uniform(3.0, 4.0)))
    pw = rng.uniform(0.25, 0.35)
    beam_h = rng.uniform(0.3, 0.45)
    for k in range(1, bays if (has["pilaster"] or has["beam"]) else 1):
        u = L * k / bays
        for v in ((pw / 2, S - pw / 2) if has["pilaster"] else ()):
            cx, cy = at(u, v)
            _box(name("Pilaster"), [(cx, cy, (z0 + zc) / 2, pw, pw, zc - z0)], struct)
            stats["pilasters"] = stats.get("pilasters", 0) + 1
        if has["beam"]:
            cx, cy = at(u, S / 2)
            sx, sy = (0.3, S) if long_x else (S, 0.3)
            _box(name("CeilingBeam"), [(cx, cy, zc - beam_h / 2, sx, sy, beam_h)], struct)
            stats["beams"] = stats.get("beams", 0) + 1
    if W * D > 60 and bays >= 2 and has["column"]:                                # a free-standing column mid-room
        cx, cy = at(L / bays, S / 2)
        _box(name("Column"), [(cx, cy, (z0 + zc) / 2, 0.35, 0.35, zc - z0)], struct)
        stats["columns"] = 1
    # soffit along the back wall (v = S: the wall opposite the storefront at v = 0)
    sh = 0.35; sd = rng.uniform(0.9, 1.4)
    if has["soffit"]:
        cx, cy = at(L / 2, S - sd / 2)
        sx, sy = (L, sd) if long_x else (sd, L)
        _box(name("Soffit"), [(cx, cy, zc - sh / 2, sx, sy, sh)], struct)
    # ceiling kit: a duct run, a pipe pair, two track rails with spot heads, an AC cassette, sprinklers
    zd = zc - 0.3                                               # tight under the ceiling (café L: 'a duct at eye level cuts the frame')
    vduct = S * rng.uniform(0.3, 0.45)
    a, b = at(0.2, vduct), at(L - 0.2, vduct)
    if has["duct"]:
        _cyl(name("Duct"), (*a, zd), (*b, zd), rng.uniform(0.15, 0.22), duct, n=24)
    for dv in ((0.35, 0.45) if has["pipe"] else ()):
        a, b = at(0.1, vduct + dv), at(L - 0.1, vduct + dv)
        _cyl(name("Pipe"), (*a, zc - 0.12), (*b, zc - 0.12), 0.025, frame)
    spot_w = 12.0
    for vt in ((S * 0.62, S * 0.8) if has["track"] else ()):
        a, b = at(0.6, vt), at(L - 0.6, vt)
        _cyl(name("TrackRail"), (*a, zc - 0.05), (*b, zc - 0.05), 0.018, frame, n=8)
        n_spot = max(3, int((L - 1.2) / 1.1))
        for k in range(n_spot):
            u = 0.6 + (k + 0.5) * (L - 1.2) / n_spot
            cx, cy = at(u, vt)
            _cyl(name("TrackSpot"), (cx, cy, zc - 0.07), (cx, cy, zc - 0.22), 0.04, frame, n=12)
            ld = bpy.data.lights.new(f"ir_track_spot_{k}", "SPOT"); ld.energy = spot_w; ld.spot_size = math.radians(35)
            ld.spot_blend = 0.4; ld.shadow_soft_size = 0.03
            lo = bpy.data.objects.new(f"PointLampFactory(track).spawn_asset({i[0]}_{k})", ld)
            bpy.context.scene.collection.objects.link(lo)
            lo.location = (cx, cy, zc - 0.24)
            lo.rotation_euler = (math.radians(rng.uniform(15, 30)), 0, rng.uniform(0, 2 * math.pi))
            stats["track_spots"] = stats.get("track_spots", 0) + 1
    if has.get("grid"):
        office_ceiling(L, S, zc, at, name, rng, stats)
    if has.get("linear"):
        linear_pendants(L, S, zc, at, name, rng, stats)
    if has.get("warehouse"):
        warehouse_roof(L, S, zc, at, name, rng, stats)
    cx, cy = at(L * rng.uniform(0.6, 0.8), S * 0.2)
    if has["ac"]:
        _box(name("AcCassette"), [(cx, cy, zc - 0.04, 0.84, 0.84, 0.06), (cx, cy, zc - 0.09, 0.62, 0.62, 0.04)],
         _mat("ir_ac_white", (0.86, 0.86, 0.85), 0.4))
    for k in (range(max(2, int(L / 2.5))) if has["sprinkler"] else ()):
        cx, cy = at(1.2 + k * 2.5, S * 0.5 + (0.6 if k % 2 else -0.6))
        _cyl(name("Sprinkler"), (cx, cy, zc - 0.005), (cx, cy, zc - 0.06), 0.012, duct, n=8)


def exterior(hdr: str, rng, stats):
    """The world sees a city, not an empty gradient: an equirect HDRI into the world BACKGROUND colour. The renderer's lighting
    variants rename that node IR_Sky and set its strength; a linked colour input keeps the image."""
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = next((n for n in nt.nodes if n.type == "BACKGROUND"), None) or nt.nodes.new("ShaderNodeBackground")
    out = next((n for n in nt.nodes if n.type == "OUTPUT_WORLD"), None) or nt.nodes.new("ShaderNodeOutputWorld")
    if not bg.outputs["Background"].links:
        nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(hdr, check_existing=True)
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value[2] = rng.uniform(0, 2 * math.pi)
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
    for l in list(bg.inputs["Color"].links):
        nt.links.remove(l)
    nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    stats["exterior"] = Path(hdr).name


def office_doors(rng, stats):
    """Commercial doors (critic r2-r5: maroon / green / dark rustic leaves in panel frames read as a house): every door leaf gets one
    neutral finish (white, light oak or grey), every casing brushed aluminium. Handles share the leaf material."""
    leaf_rgb = rng.choice(((0.86, 0.86, 0.84), (0.62, 0.5, 0.36), (0.5, 0.51, 0.52)))
    leaf = _mat("ir_office_door_leaf", leaf_rgb, 0.45)
    frame = _mat("ir_office_door_frame", (0.7, 0.7, 0.72), 0.35)
    frame.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 1.0
    n = 0
    for o in bpy.data.objects:
        f = o.name.split("(")[0]
        if o.type != "MESH" or "Door" not in f:
            continue
        m = frame if "Casing" in f else leaf
        for sl in o.material_slots:
            sl.material = m
        if not o.material_slots:
            o.data.materials.append(m)
        n += 1
    stats["office_doors"] = n
    w = 0                                                    # window frames / blinds: wood read as curtains in a house (critic r6)
    for o in bpy.data.objects:
        if o.type == "MESH" and "Window" in o.name.split("(")[0]:
            for sl in o.material_slots:
                if sl.material and "glass" not in sl.material.name.lower():
                    sl.material = frame
            w += 1
    stats["office_windows"] = w


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("blend"); ap.add_argument("--out", required=True); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--palette", help="a style/spec json; its 'palette' (frame/structure/duct/accent linear RGB) overrides defaults")
    ap.add_argument("--exterior", help="equirect HDRI shown through the windows (world background colour)")
    ap.add_argument("--no-track", action="store_true", help="no track rails/spots (a sales floor is lit by an even fixture grid)")
    ap.add_argument("--archetype", default="default", choices=sorted(ARCHETYPES))
    a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
    bpy.ops.wm.open_mainfile(filepath=a.blend)
    rng = random.Random(a.seed)
    pal = dict(PALETTE_DEFAULT)
    spec = json.loads(Path(a.palette).read_text()) if a.palette else {}
    pal.update(spec.get("palette", {}))
    kit = spec.get("architecture")                             # a style kit: the feature wall comes from rematerial, ducts follow the ceiling
    if kit and kit.get("ceiling") in ("exposed_dark", "dark_painted"):
        pal["duct"] = (0.03, 0.03, 0.032); pal["structure"] = (0.03, 0.03, 0.032)
    if spec.get("metal_finish") == "brass":
        pal["frame"] = (0.55, 0.38, 0.12)
    stats = {}
    scene, deps = bpy.context.scene, bpy.context.evaluated_depsgraph_get()
    for nm, parts in sorted(rd._rooms().items()):
        if "floor" not in parts or "wall" not in parts:
            continue
        room = fr.Room(nm, parts, scene, deps)
        if not kit:                                             # with a kit the feature wall is rematerial's (one concept, not a random accent)
            accent = _mat("ir_arch_accent", pal["accent"], 0.8)
            stats["accent"] = accent_wall(room, accent, rng, stats)
        build(room, rng, pal, stats, a.seed, track=not a.no_track, archetype=a.archetype)
    if a.archetype.startswith("office") or a.archetype == "warehouse" or kit:   # warehouse r3: mauve residential panel doors;
        # café N: 'a purple door frame' against a white/sage/oak kit -- any styled venue gets the neutral leaf and metal casing
        office_doors(rng, stats)
    if a.archetype == "warehouse":                              # no skirting in an industrial unit (wh r22, 3 of 3: 'white skirting
        sk = [o for o in bpy.data.objects if o.name.startswith("skirtingboard")]   # boards on every wall say apartment')
        for o in sk:
            bpy.data.objects.remove(o, do_unlink=True)
        stats["skirting_removed"] = len(sk)
    if a.exterior:
        exterior(a.exterior, rng, stats)
    bpy.ops.wm.save_as_mainfile(filepath=a.out, compress=True)
    print("ARCH " + json.dumps(stats), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

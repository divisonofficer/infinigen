"""Light a furnished room from its style kit (non-home 20, 2026-10-16: 'warm, layered light became uniform room light' -- the kit's
colour temperature, ambient level, daylight and accent lights are applied together, never one at a time).

    python kit_lighting.py IN.blend --out OUT.blend --plans plans.json --seed N

Reads plans.json['style_spec']['lighting'] (from room_planner.reference): colour_temp_k tints every interior light and emissive
fixture, ambient scales fixture energy, accents add wall sconces and table candles, and the daylight level is stored on the scene
(scene['ir_daylight']) for the renderer to scale window light and the sky. No kit lighting: the file is saved unchanged.
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
import room_dressing as rd  # noqa: E402
from room_planner import proc_assets as pa  # noqa: E402

AMBIENT = {"low": 0.35, "medium": 1.0, "high": 1.4}


def kelvin_rgb(k: float):
    """Approximate black-body colour (Tanner Helland), linear-ish 0-1."""
    t = k / 100.0
    r = 1.0 if t <= 66 else min(1.0, 1.292936 * (t - 60) ** -0.1332047592)
    g = (0.39008157 * math.log(t) - 0.63184144) if t <= 66 else 1.129890861 * (t - 60) ** -0.0755148492
    b = 1.0 if t >= 66 else (0.0 if t <= 19 else 0.54320678 * math.log(t - 10) - 1.19625408)
    # mild linearisation + 10% white: gamma 2.2 turned 2300 K into (1, 0.31, 0.03) and the ablation came out +11 b* warmer than its
    # reference (floral_moody s2/s3, 2026-10-16)
    # and 30% toward white: a photo is white-balanced; the raw tint left a peach/pink cast in 3 of 4 cafe style evals (G, d_warmth +4..+6.5)
    return tuple(0.7 * (0.9 * max(0.0, min(1.0, c)) ** 1.4 + 0.1) + 0.3 for c in (r, g, b))


def is_window_light(o):
    return o.parent is not None and "Window" in o.parent.name


def sconce(i, warm):
    """A wall sconce (front +X, mounted on the wall): a back plate, an arm and a glowing shade, plus a point light."""
    brass = pa._flat("ir_sconce_metal", (0.55, 0.38, 0.12), 0.3, 1.0)
    glow = pa._flat("ir_sconce_glow", (1.0, 0.85, 0.65), 0.3)
    b = glow.node_tree.nodes["Principled BSDF"]
    b.inputs["Emission Color"].default_value = (*warm, 1); b.inputs["Emission Strength"].default_value = 8.0
    o = pa._prims(f"WallSconceFactory({i}).spawn_asset({i})",
                  [(brass, [("box", (0.01, 0, 0), (0.02, 0.1, 0.16), (0, 0, 0)), ("box", (0.09, 0, 0.04), (0.16, 0.02, 0.02), (0, 0, 0))]),
                   (glow, [("cyl", (0.17, 0, 0.06), (0.05, 0.07, 0.12), (0, 0, 0))])])
    return o


def candle(i, warm):
    wax = pa._flat("ir_candle_glass", (0.9, 0.85, 0.75), 0.2, transmission=0.6)
    flame = pa._flat("ir_flame", (1.0, 0.7, 0.3), 0.3)
    b = flame.node_tree.nodes["Principled BSDF"]
    b.inputs["Emission Color"].default_value = (1.0, 0.62, 0.25, 1); b.inputs["Emission Strength"].default_value = 15.0
    return pa._prims(f"CandleFactory({i}).spawn_asset({i})", [(wax, [("cyl", (0, 0, 0.04), (0.035, 0.035, 0.08), (0, 0, 0))]),
                                                              (flame, [("cyl", (0, 0, 0.095), (0.006, 0.001, 0.025), (0, 0, 0))])])


def add_point(name, at, energy, color, radius=0.05):
    ld = bpy.data.lights.new(name, "POINT"); ld.energy = energy; ld.color = color; ld.shadow_soft_size = radius
    lo = bpy.data.objects.new(f"PointLampFactory(kit).spawn_asset({name})", ld)
    bpy.context.scene.collection.objects.link(lo); lo.location = at
    return lo


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("blend"); ap.add_argument("--out", required=True); ap.add_argument("--plans", required=True)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
    bpy.ops.wm.open_mainfile(filepath=a.blend)
    spec = json.loads(Path(a.plans).read_text()).get("style_spec") or {}
    L = spec.get("lighting")
    stats = {}
    if L:
        rng = random.Random(a.seed)
        kk = L.get("color_temp_k", 3000)
        if spec.get("venue") in ("clinic-reception", "exam-room", "dental-room", "physio-room", "pharmacy"):                          # a clinic is lit neutral whatever its reference's mood
            kk = max(kk, 3800)                                   # (clinic r10: a 2800 K 'spa' kit read as a café or lounge)
        warm = kelvin_rgb(kk)
        amb = AMBIENT.get(L.get("ambient", "medium"), 1.0)
        n = 0
        key = 5.0 if L.get("key_fixture") == "track_spots" else 1.0   # the key fixture carries the room (shop r3: a track-lit boutique
        for o in bpy.data.objects:                               # rendered near black at the default 12 W per spot)
            if o.type == "LIGHT" and not is_window_light(o):
                o.data.color = warm; o.data.energy *= amb * (key if o.data.name.startswith("ir_track_spot") else 1.0); n += 1
        for m in bpy.data.materials:                          # emissive fixtures glow in the same colour
            if m.use_nodes and "Principled BSDF" in m.node_tree.nodes:
                b = m.node_tree.nodes["Principled BSDF"]
                if b.inputs["Emission Strength"].default_value > 0.5 and m.name.startswith(("ir_led", "ir_lamp", "shader_lamp")):
                    b.inputs["Emission Color"].default_value = (*warm, 1)
        stats["lights_tinted"] = n
        scene, deps = bpy.context.scene, bpy.context.evaluated_depsgraph_get()
        acc = set(L.get("accents") or [])
        if "wall_sconces" in acc:                               # 3-6 sconces at 1.9 m on free wall spots
            k = 0
            for name, room in rd._rooms().items():
                if "floor" not in room or "wall" not in room:
                    continue
                fz = max((room["floor"].matrix_world @ Vector(c)).z for c in room["floor"].bound_box)
                for p, nrm in rd._wall_spots(scene, deps, room, rng, fz + 1.9)[: rng.randint(3, 6)]:
                    o = sconce(k, warm)
                    o.rotation_euler = (0, 0, math.atan2(nrm.y, nrm.x)); o.location = p + nrm * 0.01
                    add_point(f"sconce{k}", p + nrm * 0.2 + Vector((0, 0, 0.06)), 25.0 * max(amb, 0.6), warm, 0.06)
                    k += 1
            stats["sconces"] = k
        if "candles" in acc:                                    # a candle on most café / dining tables
            k = 0
            for o in list(bpy.data.objects):
                f = rd._factory(o.name)
                if o.type == "MESH" and f in ("CafeTableFactory", "BreakTableFactory", "TableDiningFactory") and rng.random() < 0.8:
                    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
                    top = max(p.z for p in pts); cx = sum(p.x for p in pts) / 8; cy = sum(p.y for p in pts) / 8
                    c = candle(k, warm); c.location = (cx + rng.uniform(-0.1, 0.1), cy + rng.uniform(-0.1, 0.1), top)
                    add_point(f"candle{k}", Vector((c.location.x, c.location.y, top + 0.12)), 3.0, (1.0, 0.55, 0.22), 0.02)
                    k += 1
            stats["candles"] = k
    # lights buried in architecture: a ceiling fixture placed after the exposed ducts/beams ended up inside a duct, 2 cm of metal under
    # the bulb (floor H r4: the restroom read near black, 3 of 3) -- drop the light just below whatever covers it
    sc_, dg_ = bpy.context.scene, bpy.context.evaluated_depsgraph_get()
    n_unburied = 0
    for o in [o for o in bpy.data.objects if o.type == "LIGHT" and not is_window_light(o)]:
        p = o.matrix_world.translation.copy()
        h = sc_.ray_cast(dg_, p, Vector((0, 0, -1)), distance=0.15)
        if not h[0] or h[4].name.endswith(".floor"):
            continue
        cover, q, z = h[4], h[1], None
        for _ in range(8):                                       # march down through the cover's faces to its underside
            z = q.z
            q = q - Vector((0, 0, 0.003))
            h = sc_.ray_cast(dg_, q, Vector((0, 0, -1)), distance=0.6)
            if not h[0] or h[4] != cover:
                break
            q = h[1]
        m = o.matrix_world.copy(); m.translation.z = z - 0.08; o.matrix_world = m
        n_unburied += 1
    stats["lights_unburied"] = n_unburied
    # service rooms on a floor scene get a neutral ceiling light when none is inside them (floor G: the restroom and stockroom behind a
    # low-ambient café rendered near black -- the fixture pass lights the planned public rooms only)
    lit = [(o.matrix_world.translation, o.data.energy) for o in bpy.data.objects if o.type == "LIGHT" and not is_window_light(o)
           and "(track)" not in o.name]          # track spots aim at the hub's walls; the architecture pass ran them across the whole
                                                  # floor box, over the back rooms (floor G)
    n_svc = 0
    for name, room in rd._rooms().items():
        if "floor" not in room or not name.split("_")[0] in ("restroom", "utility", "kitchen", "closet", "hallway"):
            continue
        pts = [room["floor"].matrix_world @ Vector(c) for c in room["floor"].bound_box]
        x0, x1 = min(p.x for p in pts), max(p.x for p in pts); y0, y1 = min(p.y for p in pts), max(p.y for p in pts)
        fz = max(p.z for p in pts)
        if sum(e for q, e in lit if x0 <= q.x <= x1 and y0 <= q.y <= y1 and q.z > fz) >= 150.0:
            continue                             # one 92 W lamp over a stall row left a restroom near black (floor H r5)
        cz = (max((room["wall"].matrix_world @ Vector(c)).z for c in room["wall"].bound_box) if "wall" in room else fz + 2.7) - 0.25
        add_point(f"svc{n_svc}", Vector(((x0 + x1) / 2, (y0 + y1) / 2, cz)), 40.0 * max(1.0, (x1 - x0) * (y1 - y0) / 6.0),
                  kelvin_rgb(4000), 0.3)
        n_svc += 1
    stats["service_lights"] = n_svc
    # no mood cap on daylight: tried 2026-10-16 (round J) -- chain stayed +16 L bright, industrial fell 50 -> 44 in the style eval
    bpy.context.scene["ir_daylight"] = (L or {}).get("daylight", "high")
    bpy.context.scene["ir_mood"] = spec.get("mood", "bright_daylight") if L else "bright_daylight"
    bpy.ops.wm.save_as_mainfile(filepath=a.out, compress=True)
    print("KITLIGHT " + json.dumps(stats), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Simple procedural warehouse assets the realizer can spawn (factory-shaped like Infinigen's: Cls(seed).spawn_asset(i)).

Cardboard boxes (one size per seed, per-box brown via Object Info random), wooden pallets (EUR 1.2 x 0.8 m: top boards, blocks,
bottom boards) and box piles (a few boxes stacked on a pallet footprint). Materials are plain Principled BSDFs, so the GT AOVs
(albedo / roughness / metallic) read straight from their inputs.
"""
from __future__ import annotations

import math
import os
import random

import bpy


def _material(name, colors, rough):
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    info = nt.nodes.new("ShaderNodeObjectInfo"); ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*colors[0], 1); ramp.color_ramp.elements[1].color = (*colors[1], 1)
    nt.links.new(info.outputs["Random"], ramp.inputs["Fac"]); nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    if SURFACE_DETAIL and (k_ := _scan_kind(name, 0.0, False)):
        _scan(m, colors[1], rough, k_, name)
    return m


def cardboard(tone=None):
    """Kraft cardboard; `tone` 0-3 picks a shade (pale, standard, dark, white mailer) -- one tan for every box read as 'stamped out'
    (warehouse r17)."""
    shades = (((0.36, 0.22, 0.11), (0.52, 0.36, 0.2)), ((0.48, 0.34, 0.2), (0.62, 0.48, 0.32)), ((0.26, 0.15, 0.07), (0.38, 0.24, 0.12)),
              ((0.78, 0.77, 0.74), (0.88, 0.87, 0.84)))
    t = random.randrange(4) if tone is None else tone % 4
    return _material(f"ir_cardboard_{t}" if t else "ir_cardboard", shades[t], 0.85)


def pallet_wood():
    return _material("ir_pallet_wood", ((0.45, 0.33, 0.2), (0.62, 0.5, 0.34)), 0.8)


def _boxes(name, parts, mat):
    """One mesh object from axis-aligned boxes [(cx, cy, cz, sx, sy, sz)], origin at the bottom centre."""
    import bmesh
    bm = bmesh.new()
    for cx, cy, cz, sx, sy, sz in parts:
        r = bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=r["verts"])
        bmesh.ops.translate(bm, vec=(cx, cy, cz), verts=r["verts"])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    _bevel(o)
    return o


class CardboardBoxFactory:
    def __init__(self, seed):
        r = random.Random(seed)
        self.size = (r.uniform(0.25, 0.6), r.uniform(0.2, 0.45), r.uniform(0.15, 0.4))

    def spawn_asset(self, i):
        x, y, z = self.size
        o = _boxes(f"CardboardBoxFactory({i}).spawn_asset({i})", [(0, 0, z / 2, x, y, z)], cardboard())
        o.modifiers.new("bevel", "BEVEL").width = 0.006
        return o


class BagFactory:
    """A bag left by its owner (front +X): a backpack (rounded body, front pocket, top handle) or a tote with two handles -- signs of
    use the critics kept asking for (floors D3/E3/F3 r10-r12: 'no bags, nothing left around', use 4-6 in every room)."""
    def __init__(self, seed):
        r = random.Random(seed); self.r = r; self.kind = "backpack"   # no tote: a beige tote read as 'a sack-like blob' (floor D3 r14, 2/3)
        self.c = r.choice(((0.08, 0.1, 0.16), (0.28, 0.28, 0.3), (0.12, 0.25, 0.18), (0.05, 0.05, 0.05)))   # no red: by a desk it read
        # as 'a fire extinguisher lying on the floor' (floor J r19, 3 of 3)

    def spawn_asset(self, i):
        fab = _flat(f"ir_bag_{int(self.c[0] * 100)}_{int(self.c[2] * 100)}", self.c, 0.8)
        if self.kind == "backpack":
            return _prims(f"BagFactory({i}).spawn_asset({i})", [(fab, [("rbox", (0, 0, 0.21), (0.2, 0.3, 0.42), (0, -0.15, 0)),
                                                                      ("rbox", (0.11, 0, 0.13), (0.06, 0.22, 0.18), (0, -0.15, 0)),
                                                                      ("cyl", (-0.04, 0, 0.44), (0.015, 0.015, 0.08), (math.pi / 2, 0, 0))])])
        return _prims(f"BagFactory({i}).spawn_asset({i})", [(fab, [("rbox", (0, 0, 0.17), (0.12, 0.4, 0.34), (0, 0, 0)),
                                                                  ("box", (0, 0.1, 0.4), (0.01, 0.02, 0.14), (0, 0, 0)), ("box", (0, -0.1, 0.4), (0.01, 0.02, 0.14), (0, 0, 0))])])


class ExerciseMatFactory:
    """A gym floor mat (front +X): a 1.8 x 0.6 m pad, 1.5 cm thick, sometimes with a ball or a foam roller on it."""
    def __init__(self, seed):
        r = random.Random(seed); self.r = r
        self.c = r.choice(((0.15, 0.3, 0.55), (0.1, 0.45, 0.4), (0.55, 0.15, 0.2), (0.25, 0.25, 0.28)))

    def spawn_asset(self, i):
        r = self.r
        mat = _flat(f"ir_gym_mat_{int(self.c[2] * 100)}", self.c, 0.85)
        prop = _flat(f"ir_gym_prop_{r.randrange(3)}", r.choice(((0.9, 0.5, 0.1), (0.2, 0.6, 0.8), (0.7, 0.7, 0.72))), 0.6)
        extra = r.choice((
            [("sph", (0.1, 0.45, 0.33), (0.32, 0.32, 0.32), (0, 0, 0))],                         # a gym ball at the end
            [("cyl", (0.0, 0.6, 0.09), (0.075, 0.075, 0.45), (math.pi / 2, 0, 0))],              # a foam roller
            []))
        return _prims(f"ExerciseMatFactory({i}).spawn_asset({i})", [(mat, [("rbox", (0, 0, 0.0075), (0.6, 1.8, 0.015), (0, 0, 0))])] +
                      ([(prop, extra)] if extra else []))


class DryGoodsFactory:
    """Back-stockroom stock that is not a carton: a printed paper sack (flour, sugar, coffee beans), a row of tins, or a shrink-wrapped
    case of bottles (floors G/H/I r12-r14: 'generic cartons and bins, nothing says café dry goods', 3 of 3 each)."""
    def __init__(self, seed):
        r = random.Random(seed); self.r = r; self.kind = r.choice(("sack", "sack", "tins", "bottles"))

    def spawn_asset(self, i):
        r, k = self.r, self.kind
        if k == "sack":
            paper = _flat(f"ir_sack_{r.randrange(3)}", r.choice(((0.78, 0.7, 0.55), (0.85, 0.82, 0.75), (0.45, 0.32, 0.2))), 0.85)
            band = _flat(f"ir_sack_print_{r.randrange(3)}", r.choice(((0.6, 0.12, 0.08), (0.1, 0.3, 0.55), (0.15, 0.4, 0.2))), 0.6)
            return _prims(f"DryGoodsFactory({i}).spawn_asset({i})", [(paper, [("rbox", (0, 0, 0.12), (0.3, 0.42, 0.24), (0, 0, 0))]),
                                                                    (band, [("box", (0.151, 0, 0.13), (0.004, 0.24, 0.1), (0, 0, 0))])])
        if k == "tins":
            tin = _flat("ir_tin", (0.72, 0.72, 0.74), 0.3, 0.9); lab = _flat(f"ir_tin_label_{r.randrange(3)}", r.choice(((0.75, 0.15, 0.1), (0.95, 0.75, 0.15), (0.2, 0.45, 0.25))), 0.5)
            parts_t = [("cyl", (0, -0.15 + j * 0.1, 0.06), (0.042, 0.042, 0.12), (0, 0, 0)) for j in range(4)]
            parts_l = [("cyl", (0, -0.15 + j * 0.1, 0.06), (0.043, 0.043, 0.07), (0, 0, 0)) for j in range(4)]
            return _prims(f"DryGoodsFactory({i}).spawn_asset({i})", [(tin, parts_t), (lab, parts_l)])
        glass = _flat(f"ir_syrup_{r.randrange(3)}", r.choice(((0.5, 0.25, 0.08), (0.65, 0.1, 0.12), (0.3, 0.18, 0.1))), 0.1, transmission=0.6)
        wrap = _flat("ir_shrinkwrap", (0.9, 0.9, 0.92), 0.2, transmission=0.5)
        parts_b = [("cyl", (sx * 0.06, -0.12 + j * 0.08, 0.13), (0.03, 0.03, 0.26), (0, 0, 0)) for sx in (1, -1) for j in range(4)]
        return _prims(f"DryGoodsFactory({i}).spawn_asset({i})", [(glass, parts_b), (wrap, [("box", (0, 0, 0.02), (0.26, 0.36, 0.04), (0, 0, 0))])])


class CafeStockFactory:
    """A café's own back stock: a stack of milk crates with bottles, a carton of sleeved takeaway-cup tubes, or a sack of coffee beans
    with a valve and a printed band (floor G r28: 'generic coloured boxes, nothing says café stockroom', completeness 6, 3 of 3)."""
    def __init__(self, seed):
        r = random.Random(seed); self.r = r; self.kind = r.choice(("crates", "cups", "beans", "beans"))

    def spawn_asset(self, i):
        r, k = self.r, self.kind
        if k == "crates":
            pl = _flat(f"ir_crate_{r.randrange(3)}", r.choice(((0.6, 0.08, 0.06), (0.08, 0.22, 0.5), (0.12, 0.38, 0.18))), 0.5)
            milk = _flat("ir_milk", (0.93, 0.93, 0.9), 0.3); cap = _flat("ir_milk_cap", (0.1, 0.35, 0.75), 0.4)
            n = r.randint(1, 2); c, b, cp = [], [], []   # <= 2 high: three (0.87 m) fitted no shelf level (G r33-r34)
            for j in range(n):
                z = j * 0.29
                c += [("box", (0, 0, z + 0.01), (0.36, 0.36, 0.02), (0, 0, 0))] + \
                     [("box", (sx * 0.17, 0, z + 0.14), (0.02, 0.36, 0.28), (0, 0, 0)) for sx in (1, -1)] + \
                     [("box", (0, sy * 0.17, z + 0.14), (0.36, 0.02, 0.28), (0, 0, 0)) for sy in (1, -1)]
            zt = (n - 1) * 0.29
            for bx in (-0.08, 0.08):
                for by in (-0.08, 0.08):
                    b.append(("cyl", (bx, by, zt + 0.15), (0.05, 0.05, 0.26), (0, 0, 0)))
                    cp.append(("cyl", (bx, by, zt + 0.29), (0.022, 0.022, 0.025), (0, 0, 0)))
            return _prims(f"CafeStockFactory({i}).spawn_asset({i})", [(pl, c), (milk, b), (cap, cp)])
        if k == "cups":
            card = _flat("ir_carton", (0.62, 0.46, 0.28), 0.85); cup = _flat("ir_cup_paper", (0.95, 0.94, 0.9), 0.5)
            sl = _flat("ir_cup_sleeve", (0.85, 0.87, 0.9), 0.15, transmission=0.4)
            tubes = [("cyl", (0.05, -0.15 + j * 0.1, 0.28), (0.045, 0.045, 0.3), (0, 0, 0)) for j in range(4)]
            return _prims(f"CafeStockFactory({i}).spawn_asset({i})", [(card, [("box", (0, 0, 0.11), (0.3, 0.44, 0.22), (0, 0, 0))]),
                                                                      (cup, tubes), (sl, [("box", (0.05, 0, 0.42), (0.1, 0.42, 0.01), (0, 0, 0))])])
        kraft = _flat("ir_bean_bag", (0.45, 0.3, 0.18), 0.75); blk = _flat("ir_ink", (0.05, 0.05, 0.06), 0.6)
        band = _flat(f"ir_bean_band_{r.randrange(3)}", r.choice(((0.85, 0.75, 0.55), (0.7, 0.15, 0.1), (0.15, 0.3, 0.2))), 0.6)
        bags = [("box", (0, y, 0.15), (0.12, 0.17, 0.3), (0, 0, 0)) for y in (-0.1, 0.1)] + \
               [("box", (0, y, 0.315), (0.04, 0.17, 0.03), (0, 0, 0)) for y in (-0.1, 0.1)]   # flat-bottom bags with a folded top, two
        # side by side: one bevelled box read as 'soft beige blobs, pillows' (floor G r35)
        labels = [("box", (0.061, y, 0.14), (0.004, 0.13, 0.12), (0, 0, 0)) for y in (-0.1, 0.1)]
        valves = [("cyl", (0.062, y, 0.24), (0.016, 0.016, 0.004), (0, math.pi / 2, 0)) for y in (-0.1, 0.1)]
        return _prims(f"CafeStockFactory({i}).spawn_asset({i})", [(kraft, bags), (band, labels), (blk, valves)])


class PalletFactory:
    def __init__(self, seed):
        self.seed = seed

    def spawn_asset(self, i):
        L, W, h_top, h_blk, h_bot = 1.2, 0.8, 0.022, 0.078, 0.022
        parts = []
        for k in range(5):                                       # top boards across the length
            parts.append((0, -W / 2 + 0.05 + k * (W - 0.1) / 4, h_bot + h_blk + h_top / 2, L, 0.1, h_top))
        for xi in (-1, 0, 1):
            for yi in (-1, 0, 1):
                parts.append((xi * (L / 2 - 0.07), yi * (W / 2 - 0.07), h_bot + h_blk / 2, 0.14, 0.14, h_blk))
        for yi in (-1, 0, 1):                                    # bottom boards
            parts.append((0, yi * (W / 2 - 0.07), h_bot / 2, L, 0.14, h_bot))
        r, load, z = random.Random(self.seed), [], h_bot + h_blk + h_top
        if r.random() < 0.95:                                    # most pallets carry goods (wh r12: bare ones read as floor slabs) (warehouse r2: 'pallets lie bare')
            for layer in range(r.randint(1, 4)):
                h = r.uniform(0.25, 0.4); nx = r.choice((2, 3))
                for a in range(nx):
                    for b in range(2):
                        if layer and r.random() < 0.2:
                            continue
                        load.append((-L / 2 + (a + 0.5) * L / nx + r.uniform(-0.01, 0.01), -W / 2 + (b + 0.5) * W / 2 + r.uniform(-0.01, 0.01),
                                     z + h / 2, L / nx - 0.02, W / 2 - 0.02, h))
                z += h
        return _parts_object(f"PalletFactory({self.seed}).spawn_asset({i})", [(pallet_wood(), parts)] + ([(cardboard(), load)] if load else []))


class WorkbenchFactory:
    """Packing / work bench (front +X): steel frame, butcher-block or ply top at 0.9 m, a lower shelf, a pegboard upstand at the back,
    a tape gun and a stretch-film roll (warehouse r2: 'dark-topped tables on thin white legs read as an office or dining room')."""
    def __init__(self, seed):
        r = random.Random(seed); self.r = r
        self.L = r.choice((1.5, 1.8, 2.0)); self.frame = r.choice(((0.15, 0.3, 0.55), (0.35, 0.37, 0.4), (0.12, 0.12, 0.12)))

    def spawn_asset(self, i):
        L, D, H = self.L, 0.75, 0.9
        frame = _flat(f"ir_bench_frame_{int(self.frame[2] * 100)}", self.frame, 0.45, 0.6); top = _flat("ir_butcher", (0.6, 0.42, 0.26), 0.55, wood=True)
        peg = _flat("ir_pegboard", (0.62, 0.5, 0.36), 0.7); film = _flat("ir_film", (0.85, 0.9, 0.92), 0.1, transmission=0.6)
        red = _flat("ir_tapegun", (0.75, 0.12, 0.08), 0.4)
        legs = [("box", (sx * (D / 2 - 0.03), sy * (L / 2 - 0.03), H / 2 - 0.02), (0.05, 0.05, H - 0.04), (0, 0, 0)) for sx in (1, -1) for sy in (1, -1)]
        rails = [("box", (0, 0, 0.15), (D - 0.04, L - 0.04, 0.03), (0, 0, 0))]   # no top rail: benches in a row read as one 4 m rod (wh r16)
        rails += [("box", (-D / 2 + 0.03, sy * (L / 2 - 0.03), H + 0.2), (0.04, 0.04, 0.6), (0, 0, 0)) for sy in (1, -1)]
        return _prims(f"WorkbenchFactory({i}).spawn_asset({i})",
                      [(frame, legs + rails), (top, [("box", (0, 0, H - 0.02), (D, L, 0.04), (0, 0, 0)), ("box", (0, 0, 0.175), (D - 0.06, L - 0.06, 0.02), (0, 0, 0))]),
                       (peg, [("box", (-D / 2 + 0.15, 0, H + 0.42), (0.28, L - 0.06, 0.02), (0, 0, 0))]),   # an open shelf, not a panel
                                                                                                         # (wh r12: 'modesty panels -- office desks')
                       (film, [("cyl", (0.1, L / 2 - 0.35, 0.33), (0.07, 0.07, 0.4), (math.pi / 2, 0, 0))]),
                       (red, [("box", (0.15, -L / 2 + 0.3, H + 0.05), (0.06, 0.18, 0.1), (0, 0, 0.4))])])


class ShopStoolFactory:
    """Industrial shop stool: a square steel seat on four straight legs with low stretchers, 0.68 m (warehouse r13-r17: the round black
    stool with a foot ring read as 'a side table or plant stand')."""
    def __init__(self, seed):
        self.c = random.Random(seed).choice(((0.35, 0.37, 0.4), (0.15, 0.25, 0.45), (0.12, 0.12, 0.12)))

    def spawn_asset(self, i):
        steel = _flat(f"ir_shopstool_{int(self.c[2] * 100)}", self.c, 0.45, 0.7)
        legs = [("box", (sx * 0.15, sy * 0.15, 0.33), (0.03, 0.03, 0.66), (0, 0, 0)) for sx in (1, -1) for sy in (1, -1)]
        bars = [("box", (0, sy * 0.15, 0.22), (0.3, 0.02, 0.02), (0, 0, 0)) for sy in (1, -1)] + [("box", (sx * 0.15, 0, 0.22), (0.02, 0.3, 0.02), (0, 0, 0)) for sx in (1, -1)]
        return _prims(f"ShopStoolFactory({i}).spawn_asset({i})", [(steel, legs + bars + [("box", (0, 0, 0.675), (0.36, 0.36, 0.03), (0, 0, 0))])])


class PlatformCartFactory:
    """Flatbed warehouse trolley: a 0.9 x 0.6 deck on four castors, a U handle at one end, sometimes a box or two on it."""
    def __init__(self, seed):
        self.r = random.Random(seed)

    def spawn_asset(self, i):
        r = self.r
        deck = _flat("ir_cart_deck", r.choice(((0.15, 0.3, 0.6), (0.2, 0.2, 0.22), (0.7, 0.15, 0.1))), 0.5, 0.3)
        steel = _flat("ir_chrome", (0.8, 0.8, 0.82), 0.15, 1.0); rub = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0)
        wheels = [("cyl", (sx * 0.38, sy * 0.24, 0.05), (0.05, 0.05, 0.03), (math.pi / 2, 0, 0)) for sx in (1, -1) for sy in (1, -1)]
        handle = [("cyl", (-0.44, sy * 0.25, 0.55), (0.012, 0.012, 0.8), (0, 0, 0)) for sy in (1, -1)] + \
                 [("cyl", (-0.44, 0, 0.95), (0.012, 0.012, 0.5), (math.pi / 2, 0, 0))]
        groups = [(deck, [("box", (0, 0, 0.14), (0.9, 0.6, 0.04), (0, 0, 0))]), (steel, handle), (rub, wheels)]
        if r.random() < 0.6:
            groups.append((cardboard(), [("box", (0.1, 0, 0.16 + 0.15), (0.5, 0.4, 0.3), (0, 0, r.uniform(-0.2, 0.2)))]))
        return _prims(f"PlatformCartFactory({i}).spawn_asset({i})", groups)


class BoxPileFactory:
    """1-3 layers of cardboard boxes on a 1.2 x 0.8 m footprint, slightly irregular: goods waiting to be shelved."""
    def __init__(self, seed):
        self.r = random.Random(seed)

    def spawn_asset(self, i):
        r, parts = self.r, []
        z = 0.0
        for layer in range(r.randint(1, 3)):
            h = r.uniform(0.25, 0.4)
            nx, ny = r.choice((2, 3)), 2
            for a in range(nx):
                for b in range(ny):
                    if layer and r.random() < 0.25:
                        continue                                 # a gap where a box was taken
                    sx, sy = 1.2 / nx - 0.02, 0.8 / ny - 0.02
                    parts.append((-0.6 + (a + 0.5) * 1.2 / nx + r.uniform(-0.01, 0.01), -0.4 + (b + 0.5) * 0.4 + r.uniform(-0.01, 0.01),
                                  z + h / 2, sx, sy, h))
            z += h
        o = _boxes(f"BoxPileFactory({i}).spawn_asset({i})", parts, cardboard())
        o.modifiers.new("bevel", "BEVEL").width = 0.006
        return o


# ---- cafe ---------------------------------------------------------------------------------------------------------------------------
def _flat(name, rgb, rough, metallic=0.0, transmission=0.0, wood=False):
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    if transmission:
        b.inputs["Transmission Weight"].default_value = transmission
    if transmission or not SURFACE_DETAIL:
        if wood:
            _grain(m, rgb)
        return m
    kind = _scan_kind(name, metallic, wood)
    if not (kind and _scan(m, rgb, rough, kind, name)):          # a scanned surface where one fits, else the procedural detail
        _grain(m, rgb) if wood else _detail(m, rgb, rough, metallic, name)
    return m


# user 2026-10-17 'generated objects look too smooth': flat colours -> scanned PBR (texturecan) luminance on wood / metal / fabric at
# 60% contrast under our own colour, a procedural detail on the rest, and 3 mm bevels on every procedural mesh. A/B on floor G r36:
# shader-only noise was invisible at 512 px under the denoiser (mean |d| 0.5 grey levels); scans + bevels read as real oak and
# brushed steel. IR_SURFACE_DETAIL=0 restores the flat look.
SURFACE_DETAIL = os.environ.get("IR_SURFACE_DETAIL", "1") != "0"
_TC = "/bean/ir_pbr_assets/texturecan_environment_merged_v1/texturecan/texturecan_"
_TS = "/bean/ir_pbr_assets/texturecan_staging_v1/assets/texturecan_"   # the full staging set (497): plastics, paper, more metals
SCANS = {"wood": (_TC + "wood_0002", _TC + "wood_0054"),       # continuous grain: the library's planks/parquet/dark ebony read as
         "metal": (_TC + "metal_0024", _TC + "metal_0038", _TC + "metal_0058", _TC + "metal_0062",   # floorboards or turned light oak
                   _TS + "metal_0009", _TS + "metal_0014", _TS + "metal_0042"),                        # black (A/B pbr1-pbr2)
         "fabric": (_TC + "fabric_0022", _TC + "fabrics_0076", _TC + "fabrics_0085"),   # brushed/plain metal, plain weaves
         "card": (_TS + "paper_0008",),                         # kraft board: 228 plain cartons in floors I/J (census 10-17)
         "plastic": (_TS + "plastic_0003", _TS + "plastic_0005", _TS + "plastic_0007", _TS + "plastic_0021")}
SCAN_TILE = {"wood": 1.0, "metal": 0.8, "fabric": 0.4, "card": 0.6, "plastic": 0.5}   # metres per tile
_SCAN_MEAN = {}


def _scan_kind(name, metallic, wood):
    n_ = name.lower()
    if metallic > 0.5 or any(k in n_ for k in ("steel", "chrome", "metal", "alu")):
        return "metal"
    if wood:
        return "wood"
    if any(k in n_ for k in ("fabric", "cushion", "upholst", "seat", "banquette", "felt", "towel")):
        return "fabric"
    if any(k in n_ for k in ("cardboard", "kraft", "carton", "card_")):
        return "card"
    if "pallet_wood" in n_:
        return "wood"
    if any(k in n_ for k in ("plastic", "ir_bin_", "crate", "tub", "monitor", "ladder_grip")):
        return "plastic"
    return None


def _scan(m, rgb, rough, kind, name):
    import zlib
    d = SCANS[kind][zlib.crc32(name.encode()) % len(SCANS[kind])] + "/"
    if not os.path.isfile(d + "base_color.jpg"):
        return False
    nt = m.node_tree; N, L = nt.nodes, nt.links; b = N["Principled BSDF"]
    src = b.inputs["Base Color"].links[0].from_socket if b.inputs["Base Color"].is_linked else None   # a per-object ramp (cardboard)
    tc = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping"); s_ = 1.0 / SCAN_TILE[kind]
    mp.inputs["Scale"].default_value = (s_, s_, s_); L.new(tc.outputs["Object"], mp.inputs["Vector"])
    def tex(f, color):
        im = bpy.data.images.load(d + f, check_existing=True); im.colorspace_settings.name = "sRGB" if color else "Non-Color"
        if (d + f) not in _SCAN_MEAN:
            import numpy as np
            px = np.array(im.pixels[:], dtype=np.float32).reshape(-1, im.channels)[::97, :3]
            _SCAN_MEAN[d + f] = float((px @ np.array([0.2126, 0.7152, 0.0722], np.float32)).mean()) or 1.0
        t = N.new("ShaderNodeTexImage"); t.image = im; t.projection = "BOX"; t.projection_blend = 0.3
        L.new(mp.outputs["Vector"], t.inputs["Vector"]); return t, _SCAN_MEAN[d + f]
    bc, mean = tex("base_color.jpg", True)
    bw = N.new("ShaderNodeRGBToBW"); L.new(bc.outputs["Color"], bw.inputs["Color"])
    k_ = N.new("ShaderNodeMath"); k_.operation = "MULTIPLY_ADD"; k_.inputs[1].default_value = 0.6 / mean; k_.inputs[2].default_value = 0.4
    L.new(bw.outputs["Val"], k_.inputs[0])                        # 0.4 + 0.6 lum/mean: the grain at 60% contrast, mean 1
    cc = N.new("ShaderNodeCombineColor"); [L.new(k_.outputs["Value"], cc.inputs[i]) for i in range(3)]
    mul = N.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs["Factor"].default_value = 1.0
    mul.inputs[6].default_value = (*rgb, 1); L.new(cc.outputs["Color"], mul.inputs[7]); L.new(mul.outputs[2], b.inputs["Base Color"])
    if src is not None:
        L.new(src, mul.inputs[6])
    rt, rmean = tex("roughness.jpg", False)
    rm = N.new("ShaderNodeMath"); rm.operation = "MULTIPLY"; rm.use_clamp = True; rm.inputs[1].default_value = rough / rmean
    L.new(rt.outputs["Color"], rm.inputs[0]); L.new(rm.outputs["Value"], b.inputs["Roughness"])
    nm, _ = tex("normal_gl.png", False); nn = N.new("ShaderNodeNormalMap")
    L.new(nm.outputs["Color"], nn.inputs["Color"]); L.new(nn.outputs["Normal"], b.inputs["Normal"])
    return True


def _bevel(o):
    """3 mm rounded edges: razor-sharp box edges are the CG tell next to flat colours (user 2026-10-17)."""
    if SURFACE_DETAIL:
        md = o.modifiers.new("ir_bevel", "BEVEL"); md.width = 0.003; md.segments = 2; md.limit_method = "ANGLE"


def _detail(m, rgb, rough, metallic, name):
    """Surface detail on a flat colour (user 2026-10-17: 'generated objects look too smooth'), shader-only, object space:
    a slow +-6% colour and +-15% roughness drift, and a fine bump whose pattern follows the material class -- hairline streaks on
    metal, a weave on fabric, fibre on card/paper, orange-peel on paint/plastic, a faint waviness on glossy ceramic.
    No AO or edge darkening in the colour: it would leak lighting into the albedo ground truth."""
    nt = m.node_tree; N, L = nt.nodes, nt.links
    b = N["Principled BSDF"]
    n_ = name.lower()
    kind = ("metal" if metallic > 0.5 else "fabric" if any(k in n_ for k in ("fabric", "cushion", "upholst", "seat", "towel", "apron", "felt"))
            else "fibre" if any(k in n_ for k in ("card", "kraft", "paper", "box", "carton")) else "gloss" if rough < 0.15 else "paint")
    tc = N.new("ShaderNodeTexCoord")
    slow = N.new("ShaderNodeTexNoise"); slow.inputs["Scale"].default_value = 3.0; slow.inputs["Detail"].default_value = 3.0
    L.new(tc.outputs["Object"], slow.inputs["Vector"])
    col = N.new("ShaderNodeMapRange"); col.data_type = "FLOAT"
    col.inputs["To Min"].default_value, col.inputs["To Max"].default_value = 0.88, 1.1
    mot = N.new("ShaderNodeTexNoise"); mot.inputs["Scale"].default_value = 25.0; mot.inputs["Detail"].default_value = 8.0   # mottling
    L.new(tc.outputs["Object"], mot.inputs["Vector"])
    both = N.new("ShaderNodeMath"); both.operation = "MULTIPLY_ADD"; both.inputs[1].default_value = 0.5
    L.new(mot.outputs["Fac"], both.inputs[0]); L.new(slow.outputs["Fac"], both.inputs[2])   # slow + mottling/2, ~0.25..1.25
    col.inputs["From Min"].default_value, col.inputs["From Max"].default_value = 0.35, 1.15
    L.new(both.outputs["Value"], col.inputs["Value"])
    mul = N.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs["Factor"].default_value = 1.0
    mul.inputs[6].default_value = (*rgb, 1)
    cc = N.new("ShaderNodeCombineColor"); [L.new(col.outputs["Result"], cc.inputs[i]) for i in range(3)]
    L.new(cc.outputs["Color"], mul.inputs[7]); L.new(mul.outputs[2], b.inputs["Base Color"])
    rr = N.new("ShaderNodeMapRange"); rr.inputs["To Min"].default_value, rr.inputs["To Max"].default_value = rough * 0.75, min(1.0, rough * 1.25)
    rr.inputs["From Min"].default_value, rr.inputs["From Max"].default_value = 0.35, 1.15
    L.new(both.outputs["Value"], rr.inputs["Value"]); L.new(rr.outputs["Result"], b.inputs["Roughness"])
    mp = N.new("ShaderNodeMapping"); L.new(tc.outputs["Object"], mp.inputs["Vector"])
    if kind == "fabric":
        tex = N.new("ShaderNodeTexWave"); tex.wave_type = "BANDS"; tex.bands_direction = "DIAGONAL"; tex.inputs["Scale"].default_value = 120.0
        strength = 0.4
    else:
        tex = N.new("ShaderNodeTexNoise"); tex.inputs["Detail"].default_value = 6.0
        tex.inputs["Scale"].default_value, strength = {"metal": (80.0, 0.15), "fibre": (120.0, 0.3), "gloss": (15.0, 0.05),
                                                       "paint": (80.0, 0.2)}[kind]   # ~1 cm features: at 400 the
        # bump sat below a pixel and the A/B showed no change (G r36 close-ups, mean |d| 0.5 grey levels, 2026-10-17)
        if kind == "metal":                                      # hairline brushing: stretched along one axis
            mp.inputs["Scale"].default_value = (60.0, 1.0, 1.0)
    L.new(mp.outputs["Vector"], tex.inputs["Vector"])
    bump = N.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = strength; bump.inputs["Distance"].default_value = 0.002
    L.new(tex.outputs["Fac"], bump.inputs["Height"]); L.new(bump.outputs["Normal"], b.inputs["Normal"])


# a block stroke font for shop signs: (x, z, w, h) in a unit cell centred on 0; w or h 0 = one stroke thick
_SEG = {"L": (-0.5, 0, 0, 1), "R": (0.5, 0, 0, 1), "Lt": (-0.5, 0.25, 0, 0.5), "Lb": (-0.5, -0.25, 0, 0.5), "Rt": (0.5, 0.25, 0, 0.5),
        "Rb": (0.5, -0.25, 0, 0.5), "T": (0, 0.5, 1, 0), "M": (0, 0, 1, 0), "B": (0, -0.5, 1, 0), "C": (0, 0, 0, 1)}
_STROKES = {ch: [_SEG[k] for k in segs.split()] for ch, segs in {
    "A": "L R T M", "C": "L T B", "D": "L Rb Rt T B", "E": "L T M B", "F": "L T M", "H": "L R M", "I": "C", "L": "L B", "O": "L R T B",
    "P": "L Rt T M", "S": "Lt Rb T M B", "T": "T C", "U": "L R B"}.items()}
HEADER_WORDS = ("FOOD", "COLD", "TEA", "SOUP", "DELI", "SALE", "CUPS", "SODA", "HOT", "SALAD")   # only letters the font has


WOODS = ("butcher_block", "light_wood", "dark_wood")


def _grain(m, rgb):
    """Wood grain on a flat colour (style eval 2026-10-16: 'chairs and tables look like clay with a flat tint, no wood grain'):
    distorted wave bands in object space mix the colour with a 35% darker late wood, plus a faint bump of the same bands."""
    nt = m.node_tree; N, L = nt.nodes, nt.links
    b = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord"); wv = N.new("ShaderNodeTexWave"); mix = N.new("ShaderNodeMix"); bump = N.new("ShaderNodeBump")
    wv.wave_type = "BANDS"; wv.bands_direction = "X"
    wv.inputs["Scale"].default_value = 22.0; wv.inputs["Distortion"].default_value = 4.0; wv.inputs["Detail"].default_value = 4.0
    wv.inputs["Detail Scale"].default_value = 2.0                # fine grain (style eval H: 'oversized wavy procedural grain')
    mix.data_type = "RGBA"
    mix.inputs[6].default_value = (*rgb, 1); mix.inputs[7].default_value = (*(c * 0.65 for c in rgb), 1)
    bump.inputs["Strength"].default_value = 0.08; bump.inputs["Distance"].default_value = 0.002
    L.new(tc.outputs["Object"], wv.inputs["Vector"]); L.new(wv.outputs["Fac"], mix.inputs["Factor"])
    L.new(mix.outputs[2], b.inputs["Base Color"]); L.new(wv.outputs["Fac"], bump.inputs["Height"]); L.new(bump.outputs["Normal"], b.inputs["Normal"])


STYLE = {}                                                       # set by realize from the plan's venue style
_ROOM_PICK = {}                                                  # per-scene picks shared by every instance (one process per scene)
VENUE = ""                                                       # set by realize: cafe / grocery / ... (fixture density)
from room_planner.styles import COUNTER_FRONTS, COUNTER_TOPS  # noqa: E402  (bpy-free: the reference reader enumerates them)



def _parts_object(name, groups):
    """One object, one material slot per group: groups = [(material, [(cx, cy, cz, sx, sy, sz), ...]), ...]."""
    import bmesh
    bm = bmesh.new()
    for slot, (mat, parts) in enumerate(groups):
        for cx, cy, cz, sx, sy, sz in parts:
            r = bmesh.ops.create_cube(bm, size=1.0)
            bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=r["verts"])
            bmesh.ops.translate(bm, vec=(cx, cy, cz), verts=r["verts"])
            for f in {f for v in r["verts"] for f in v.link_faces}:
                f.material_index = slot
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for mat, _ in groups:
        me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    _bevel(o)
    return o


class TaskChairFactory:
    """Office task chair (front +X): five-star base on casters, gas column, upholstered seat, mesh-look back, armrests (floors J r9 /
    E3 r8: the Infinigen office chair came out as 'a white shell seat' or 'a blue lab stool' -- café or lab, not an office)."""
    def __init__(self, seed):
        r = random.Random(seed)
        self.c = _ROOM_PICK.setdefault("task_chair", r.choice(((0.05, 0.05, 0.06), (0.2, 0.21, 0.23), (0.08, 0.12, 0.2))))

    def spawn_asset(self, i):
        fab = _flat(f"ir_task_fabric_{int(self.c[2] * 100)}", self.c, 0.8); blk = _flat("ir_black_plastic", (0.04, 0.04, 0.045), 0.5)
        steel = _flat("ir_desk_frame", (0.75, 0.75, 0.76), 0.35, 0.8)
        spokes = [("box", (0.16 * math.cos(a), 0.16 * math.sin(a), 0.07), (0.32, 0.04, 0.03), (0, 0, a)) for a in [k * 2 * math.pi / 5 for k in range(5)]]
        casters = [("cyl", (0.31 * math.cos(a), 0.31 * math.sin(a), 0.03), (0.025, 0.025, 0.04), (math.pi / 2, 0, a)) for a in [k * 2 * math.pi / 5 for k in range(5)]]
        return _prims(f"TaskChairFactory({i}).spawn_asset({i})", [
            (blk, spokes + casters + [("box", (-0.02, 0, 0.44), (0.3, 0.3, 0.03), (0, 0, 0)),
                                      ("box", (-0.24, 0, 0.6), (0.03, 0.08, 0.3), (0, -0.1, 0))] +
                  [("box", (0.0, sy * 0.25, 0.62), (0.26, 0.05, 0.03), (0, 0, 0)) for sy in (1, -1)] +
                  [("box", (-0.05, sy * 0.25, 0.54), (0.03, 0.03, 0.16), (0, 0, 0)) for sy in (1, -1)]),
            (steel, [("cyl", (0, 0, 0.26), (0.025, 0.025, 0.34), (0, 0, 0))]),
            (fab, [("rbox", (0.0, 0, 0.48), (0.48, 0.48, 0.08), (0, 0, 0)), ("rbox", (-0.27, 0, 0.88), (0.06, 0.45, 0.55), (0, -0.12, 0))])])


class CheckoutCounterFactory:
    """Shop checkout (front +X = the customer side): a grey laminate till counter with a dark top and a kick plinth, an impulse rack
    of small coloured packs on the customer end, a back-counter shelf unit is the plan's backbar_shelf (floor I r11: 'a slatted café
    counter as the till', 3 of 3)."""
    def __init__(self, seed):
        r = random.Random(seed); self.L = r.choice((1.6, 2.0)); self.c = r.choice(((0.55, 0.57, 0.6), (0.82, 0.82, 0.8)))

    def spawn_asset(self, i):
        L, D, H = self.L, 0.7, 0.95
        body = _flat(f"ir_checkout_{int(self.c[0] * 100)}", self.c, 0.4); top = _flat("ir_checkout_top", (0.06, 0.06, 0.07), 0.3)
        wire = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0)
        packs = [_flat(f"ir_pack_{j}", c, 0.5) for j, c in enumerate(((0.8, 0.1, 0.1), (0.95, 0.75, 0.1), (0.1, 0.4, 0.75), (0.15, 0.6, 0.25)))]
        groups = [(body, [(0, 0, H / 2 - 0.02, D, L, H - 0.04)]), (top, [(0, 0, H - 0.02, D + 0.04, L + 0.04, 0.04), (D / 2 - 0.01, 0, 0.05, 0.02, L, 0.1)]),
                  (wire, [(D / 2 + 0.15, L / 2 - 0.25, 0.45 + z, 0.3, 0.4, 0.01) for z in (0.0, 0.25, 0.5)] +
                         [(D / 2 + 0.15, L / 2 - 0.25 + sy * 0.2, 0.45, 0.3, 0.01, 0.9) for sy in (1, -1)] +
                         [(D / 2 + 0.15, L / 2 - 0.25, 0.22, 0.04, 0.04, 0.45)])]
        for j in range(12):                                      # packs on the three rack levels
            lvl, k = j // 4, j % 4
            groups.append((packs[(j + lvl) % 4], [(D / 2 + 0.15, L / 2 - 0.4 + k * 0.1, 0.45 + lvl * 0.25 + 0.06, 0.12, 0.07, 0.11)]))
        return _parts_object(f"CheckoutCounterFactory({i}).spawn_asset({i})", groups)


class CafeCounterFactory:
    """A service counter (front +X like Infinigen): body with a slatted or tiled front, an overhanging top; 1.8-3.2 m long."""
    def __init__(self, seed):
        r = random.Random(seed)
        self.L = r.uniform(1.8, 3.2)
        self.front = STYLE.get("counter_front") or r.choice(sorted(COUNTER_FRONTS))
        self.top = STYLE.get("counter_top") or r.choice(sorted(COUNTER_TOPS))
        self.slats = any(k in self.front for k in ("slat", "fluted", "panel"))

    def spawn_asset(self, i):
        L, D, H = self.L, 0.65, 1.0
        fr_rgb, fr_r = COUNTER_FRONTS[self.front]; tp_rgb, tp_r = COUNTER_TOPS[self.top]
        front = _flat(f"ir_counter_{self.front}", fr_rgb, fr_r); top = _flat(f"ir_counter_top_{self.top}", tp_rgb, tp_r,
                                                                             metallic=1.0 if self.top == "steel" else 0.0, wood=self.top in WOODS)
        body = [(0, 0, (H - 0.04) / 2, D, L, H - 0.04)]
        if self.slats and "panel" not in self.front:             # vertical slats proud of the front face (+x)
            n = int(L / 0.06)
            body += [(D / 2 + 0.008, -L / 2 + (k + 0.5) * L / n, (H - 0.04) / 2, 0.016, L / n * 0.6, H - 0.1) for k in range(n)]
        else:                                                    # raised panels with a moulding frame (style eval: 'a plain block')
            n = max(2, int(L / 0.6))
            for k in range(n):
                y = -L / 2 + (k + 0.5) * L / n
                body += [(D / 2 + 0.01, y, 0.5, 0.02, L / n - 0.12, 0.62), (D / 2 + 0.005, y, 0.86, 0.01, L / n - 0.06, 0.03),
                         (D / 2 + 0.005, y, 0.14, 0.01, L / n - 0.06, 0.03)]
        return _parts_object(f"CafeCounterFactory({i}).spawn_asset({i})",
                             [(front, body), (top, [(0.03, 0, H - 0.02, D + 0.06, L + 0.04, 0.04)])])


class CafeTableFactory:
    """Bistro table: round-ish (octagonal) or square top on a pedestal, 0.6-0.8 m, 0.75 m high."""
    def __init__(self, seed):
        r = random.Random(seed)
        self.w = r.uniform(0.6, 0.8)
        self.top = STYLE.get("table_top") if STYLE.get("table_top") in COUNTER_TOPS else r.choice(("white_stone", "black_stone", "butcher_block"))

    def spawn_asset(self, i):
        w = self.w
        top = _flat(f"ir_counter_top_{self.top}", *COUNTER_TOPS[self.top], wood=self.top in WOODS); metal = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0)
        if STYLE.get("chair_style") == "bentwood" or STYLE.get("table_shape") == "round":   # round bistro tops (style eval)
            return _prims(f"CafeTableFactory({i}).spawn_asset({i})",
                          [(top, [("cyl", (0, 0, 0.745), (w / 2, w / 2, 0.03), (0, 0, 0))]),
                           (metal, [("cyl", (0, 0, 0.37), (0.03, 0.03, 0.7), (0, 0, 0)), ("cyl", (0, 0, 0.015), (0.22, 0.22, 0.03), (0, 0, 0))])])
        return _parts_object(f"CafeTableFactory({i}).spawn_asset({i})",
                             [(top, [(0, 0, 0.74, w, w, 0.03)]),
                              (metal, [(0, 0, 0.37, 0.06, 0.06, 0.70), (0, 0, 0.01, 0.45, 0.06, 0.02), (0, 0, 0.01, 0.06, 0.45, 0.02)])])


class CafeChairFactory:
    """A café chair in the reference's style (cafe r3: ABO pools gave grey/white upholstered chairs for every style). Front +X.
    bentwood: dark curved hoop back, round seat, splayed legs; light_wood: pale oak, spindle-free shell back; metal_bistro: black steel
    seat and back with a straight back."""
    def __init__(self, seed, style=None):
        r = random.Random(seed)
        self.style = style or STYLE.get("chair_style") or r.choice(("bentwood", "light_wood", "metal_bistro"))
        if self.style not in ("bentwood", "light_wood", "metal_bistro"):   # 'mixed': a café mixes two bistro families, never office chairs
            self.style = r.choice(("metal_bistro", "metal_bistro", "bentwood"))   # dark bistro family (style eval G: blond chairs in a brick cafe)

    def spawn_asset(self, i):
        st = self.style
        col = {"bentwood": ((0.035, 0.02, 0.012), 0.35, 0.0), "light_wood": ((0.62, 0.46, 0.3), 0.5, 0.0),   # near-black: reads dark under 2300 K
               "metal_bistro": ((0.04, 0.04, 0.045), 0.4, 1.0)}.get(st, ((0.12, 0.07, 0.04), 0.45, 0.0))
        m = _flat(f"ir_chair_{st}", col[0], col[1], col[2], wood=st in ("bentwood", "light_wood"))
        legs = [("cyl", (sx * 0.17, sy * 0.17, 0.22), (0.016, 0.014, 0.45), (sy * 0.06, -sx * 0.06, 0)) for sx in (1, -1) for sy in (1, -1)]
        if st == "bentwood":
            seat = [("cyl", (0, 0, 0.46), (0.21, 0.21, 0.035), (0, 0, 0))]
            back = [("box", (-0.19, sy * 0.15, 0.68), (0.025, 0.025, 0.46), (0, 0, 0)) for sy in (1, -1)] + \
                   [("box", (-0.2, 0, 0.9), (0.025, 0.34, 0.025), (0, 0, 0)), ("box", (-0.2, 0, 0.7), (0.02, 0.3, 0.02), (0, 0, 0))]
        elif st == "metal_bistro":
            seat = [("box", (0, 0, 0.46), (0.4, 0.4, 0.025), (0, 0, 0))]
            back = [("box", (-0.2, 0, 0.66), (0.025, 0.38, 0.38), (0, 0.08, 0))]
        else:
            seat = [("box", (0, 0, 0.46), (0.42, 0.42, 0.03), (0, 0, 0))]
            back = [("box", (-0.2, 0, 0.72), (0.03, 0.4, 0.14), (0, 0.12, 0))] + [("box", (-0.19, sy * 0.17, 0.6), (0.025, 0.025, 0.28), (0, 0, 0)) for sy in (1, -1)]
        return _prims(f"CafeChairFactory({i}).spawn_asset({i})", [(m, legs + seat + back)])


class BudVaseFactory:
    """A small glass or ceramic vase with 3-7 flowers (style eval floral: 'no flowers on the tables'), 0.15-0.3 m."""
    def __init__(self, seed, big=False):
        r = random.Random(seed); self.r, self.big = r, big
        self.pal = r.choice((((0.85, 0.3, 0.4), (0.95, 0.85, 0.9)), ((0.95, 0.7, 0.2), (0.95, 0.95, 0.9)), ((0.6, 0.2, 0.5), (0.9, 0.5, 0.6)),
                             ((0.95, 0.95, 0.92), (0.75, 0.1, 0.15))))

    def spawn_asset(self, i):
        r, s_ = self.r, (2.6 if self.big else 1.0)
        vase = _flat("ir_vase_glass" if r.random() < 0.5 else "ir_vase_ceramic", (0.85, 0.88, 0.85) if r.random() < 0.5 else (0.2, 0.25, 0.22), 0.1,
                     transmission=0.8 if r.random() < 0.5 else 0.0)
        stem = _flat("ir_stem", (0.12, 0.3, 0.1), 0.7); leaf = _flat("ir_leaf", (0.15, 0.38, 0.12), 0.6)
        groups = [(vase, [("cyl", (0, 0, 0.06 * s_), (0.03 * s_, 0.025 * s_, 0.12 * s_), (0, 0, 0))])]
        stems, heads, leaves = [], {}, []
        for k in range(r.randint(5, 9) if self.big else r.randint(3, 6)):
            a, t = r.uniform(0, 6.28), r.uniform(0.05, 0.35)
            h = r.uniform(0.14, 0.24) * s_
            tip = (math.sin(t) * math.cos(a) * h, math.sin(t) * math.sin(a) * h, 0.1 * s_ + math.cos(t) * h)
            stems.append(("cyl", (tip[0] / 2, tip[1] / 2, (0.1 * s_ + tip[2]) / 2), (0.003 * s_, 0.003 * s_, h), (t * math.sin(a), -t * math.cos(a), 0)))
            c = r.choice(self.pal)
            heads.setdefault(c, []).append(("sph", tip, (0.025 * s_, 0.025 * s_, 0.018 * s_), (0, 0, 0)))
            leaves.append(("sph", (tip[0] * 0.6, tip[1] * 0.6, 0.1 * s_ + tip[2] * 0.4), (0.02 * s_, 0.008 * s_, 0.012 * s_), (0, 0, a)))
        groups += [(stem, stems), (leaf, leaves)]
        for c, parts in heads.items():
            groups.append((_flat(f"ir_bloom_{int(c[0] * 100)}_{int(c[1] * 100)}", c, 0.6), parts))
        return _prims(f"BudVaseFactory({i}).spawn_asset({i})", groups)


class FlowerArrangementFactory(BudVaseFactory):
    """A large bouquet for the counter (floral cafés)."""
    def __init__(self, seed):
        super().__init__(seed, big=True)


class HangingPlantFactory:
    """A ceiling-hung trailing plant (pothos): a pot on three cords from a ceiling hook, leaf strands trailing 0.4-0.9 m below it.
    Origin at the hook; the pot hangs `drop` below (nordic / chain refs: hanging plants in every view, renders had none)."""
    def __init__(self, seed, drop=0.7):
        r = random.Random(seed); self.r = r; self.drop = drop
        self.pot = r.choice(((0.85, 0.83, 0.78), (0.6, 0.35, 0.22), (0.12, 0.12, 0.12)))

    def spawn_asset(self, i):
        r, z = self.r, -self.drop
        pot = _flat(f"ir_pot_{int(self.pot[0] * 100)}", self.pot, 0.6); cord = _flat("ir_cord", (0.75, 0.68, 0.55), 0.8)
        leaf = _flat(f"ir_pothos_{i % 3}", ((0.12, 0.32, 0.08), (0.18, 0.4, 0.1), (0.1, 0.26, 0.07))[i % 3], 0.55)
        cords = [("cyl", (0.06 * math.cos(a) / 2, 0.06 * math.sin(a) / 2, z / 2), (0.003, 0.003, abs(z)), (0.12 * math.sin(a), -0.12 * math.cos(a), 0))
                 for a in (0, 2.1, 4.2)]
        leaves = [("sph", (0, 0, z + 0.02), (0.13, 0.13, 0.07), (0, 0, 0))]
        for s_ in range(r.randint(5, 8)):                        # strands over the rim, each a chain of leaves drifting outward
            a = r.uniform(0, 2 * math.pi); L = r.uniform(0.3, 0.6)   # bottom stays above head height
            for k in range(int(L / 0.06)):
                rad = 0.12 + 0.02 * k ** 0.5
                leaves.append(("sph", (rad * math.cos(a) + r.uniform(-0.02, 0.02), rad * math.sin(a) + r.uniform(-0.02, 0.02), z - 0.05 - k * 0.06),
                               (0.035, 0.03, 0.012), (r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(0, 3))))
        return _prims(f"HangingPlantFactory({i}).spawn_asset({i})",
                      [(pot, [("cyl", (0, 0, z - 0.07), (0.08, 0.12, 0.16), (0, 0, 0))]), (cord, cords), (leaf, leaves)])


SHADES = {"black_metal_dome": ((0.02, 0.02, 0.022), 0.35, 1.0), "white_enamel_dome": ((0.9, 0.9, 0.88), 0.2, 0.0),
          "brass_dome": ((0.62, 0.45, 0.18), 0.25, 1.0), "copper_dome": ((0.7, 0.35, 0.2), 0.25, 1.0),
          "glass_globe": ((0.95, 0.95, 0.92), 0.05, 0.0), "fabric_drum": ((0.85, 0.82, 0.75), 0.9, 0.0), "bare_bulb": None}


class DomePendantFactory:
    """A café pendant in the reference's shade (style evals: '15 copper domes where the ref has black enamel'): a cord from the
    ceiling, a dome / globe / drum / bare-bulb head, a glowing bulb. Origin at the ceiling point; `drop` metres of cord."""
    def __init__(self, seed, shade="black_metal_dome", drop=0.9):
        self.shade, self.drop = shade, drop

    def spawn_asset(self, i):
        z = -self.drop
        cord = _flat("ir_cord_black", (0.02, 0.02, 0.02), 0.6)
        bulb = _flat("ir_bulb_warm", (1.0, 0.85, 0.6), 0.3)
        bulb.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (1.0, 0.75, 0.45, 1)
        bulb.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 2.5   # 6 blew out the shade undersides
        groups = [(cord, [("cyl", (0, 0, z / 2), (0.004, 0.004, abs(z)), (0, 0, 0)), ("cyl", (0, 0, -0.01), (0.04, 0.04, 0.02), (0, 0, 0))])]
        spec = SHADES.get(self.shade)
        if self.shade == "glass_globe":
            groups.append((_flat("ir_globe_glass", spec[0], spec[1], transmission=0.9), [("sph", (0, 0, z - 0.12), (0.13, 0.13, 0.13), (0, 0, 0))]))
        elif self.shade == "fabric_drum":
            groups.append((_flat("ir_drum_fabric", spec[0], spec[1], transmission=0.3), [("cyl", (0, 0, z - 0.1), (0.22, 0.22, 0.2), (0, 0, 0))]))
        elif spec is not None:                                    # domes: a wide shallow cone with a neck
            m = _flat(f"ir_shade_{self.shade}", *spec)
            # a bowl, not a cone (café M: 'the pendants are cones'): a rounded cap over a short flared skirt
            groups.append((m, [("cyl", (0, 0, z - 0.03), (0.03, 0.03, 0.06), (0, 0, 0)), ("sph", (0, 0, z - 0.1), (0.15, 0.15, 0.08), (0, 0, 0)),
                               ("cyl", (0, 0, z - 0.15), (0.2, 0.15, 0.08), (0, 0, 0))]))
        groups.append((bulb, [("sph", (0, 0, z - 0.2 if spec is not None and self.shade.endswith("dome") else z - 0.12), (0.035, 0.035, 0.05), (0, 0, 0))]))
        return _prims(f"DomePendantFactory({i}).spawn_asset({i})", groups)


class OliveTreeFactory:
    """A potted olive tree, 1.4-1.9 m: a terracotta or stone pot, a slim twisting trunk, clusters of grey-green leaf masses (floral / nordic
    refs: olive trees by the windows; Infinigen plants take minutes each)."""
    def __init__(self, seed):
        r = random.Random(seed); self.r = r; self.h = r.uniform(1.4, 1.9)
        self.pot = r.choice(((0.6, 0.35, 0.22), (0.55, 0.53, 0.5), (0.12, 0.12, 0.12)))

    def spawn_asset(self, i):
        r, h = self.r, self.h
        pot = _flat(f"ir_pot_{int(self.pot[0] * 100)}", self.pot, 0.8); bark = _flat("ir_bark", (0.18, 0.15, 0.12), 0.9)
        leaf = _flat("ir_olive_leaf", (0.22, 0.28, 0.18), 0.7)
        trunk, masses = [], []
        x = y = 0.0
        for k in range(4):                                      # a slightly crooked trunk in four segments
            z0 = 0.4 + k * (h - 0.9) / 4; dx, dy = r.uniform(-0.04, 0.04), r.uniform(-0.04, 0.04)
            trunk.append(("cyl", (x + dx / 2, y + dy / 2, z0 + (h - 0.9) / 8), (0.025, 0.022, (h - 0.9) / 4 + 0.02), (dy * 2, -dx * 2, 0)))
            x += dx; y += dy
        # branches out of the trunk top, each ending in a cloud of small leaves; 7-11 big ellipsoids read as 'low-poly lollipop
        # blobs' in three style evals (cafe G)
        for k in range(r.randint(5, 8)):
            a, el = r.uniform(0, 6.28), r.uniform(0.35, 1.0)
            Lb = r.uniform(0.25, 0.45)
            tip = (x + Lb * math.cos(el) * math.cos(a), y + Lb * math.cos(el) * math.sin(a), h - 0.5 + Lb * math.sin(el))
            mid = ((x + tip[0]) / 2, (y + tip[1]) / 2, (h - 0.5 + tip[2]) / 2)
            trunk.append(("cyl", mid, (0.012, 0.008, Lb), (0, math.pi / 2 - el, a)))
            for _ in range(r.randint(28, 40)):
                q = (tip[0] + r.gauss(0, 0.09), tip[1] + r.gauss(0, 0.09), tip[2] + r.gauss(0, 0.07))
                masses.append(("sph", q, (0.035, 0.011, 0.004), (r.uniform(-1.2, 1.2), r.uniform(-1.2, 1.2), r.uniform(0, 6.28))))
        return _prims(f"OliveTreeFactory({i}).spawn_asset({i})",
                      [(pot, [("cyl", (0, 0, 0.2), (0.17, 0.22, 0.4), (0, 0, 0))]), (bark, trunk), (leaf, masses)])


class ChandelierFactory:
    """A crystal / brass chandelier (origin at the top): a ring of 6-10 arms with glowing bulbs and hanging crystal drops."""
    def __init__(self, seed):
        r = random.Random(seed); self.n = r.choice((6, 8, 10)); self.R = r.uniform(0.3, 0.45)

    def spawn_asset(self, i):
        n, R = self.n, self.R
        brass = _flat("ir_sconce_metal", (0.55, 0.38, 0.12), 0.3, 1.0); crystal = _flat("ir_crystal", (0.95, 0.95, 1.0), 0.02, transmission=1.0)
        bulb = _flat("ir_chandelier_bulb", (1.0, 0.85, 0.6), 0.3)
        b = bulb.node_tree.nodes["Principled BSDF"]
        b.inputs["Emission Color"].default_value = (1.0, 0.62, 0.3, 1); b.inputs["Emission Strength"].default_value = 30.0
        arms, bulbs, drops = [("cyl", (0, 0, -0.25), (0.015, 0.015, 0.5), (0, 0, 0)), ("cyl", (0, 0, -0.5), (R, R, 0.02), (0, 0, 0))], [], []
        for k in range(n):
            a = 2 * math.pi * k / n
            x, y = R * math.cos(a), R * math.sin(a)
            arms.append(("cyl", (x / 2, y / 2, -0.5), (0.008, 0.008, R), (math.pi / 2, 0, a + math.pi / 2)))
            arms.append(("cyl", (x, y, -0.47), (0.018, 0.012, 0.05), (0, 0, 0)))          # candle cup
            bulbs.append(("sph", (x, y, -0.43), (0.012, 0.012, 0.03), (0, 0, 0)))          # candle-flame bulb (style eval: 'white globes')
            for j in range(5):                                                           # strands of crystal drops
                t = (k + j / 5) * 2 * math.pi / n
                drops.append(("sph", (R * 0.85 * math.cos(t), R * 0.85 * math.sin(t), -0.56 - 0.035 * (j % 3)), (0.008, 0.008, 0.018), (0, 0, 0)))
        drops += [("sph", (0, 0, -0.62 - 0.04 * j), (0.02 - 0.003 * j, 0.02 - 0.003 * j, 0.03), (0, 0, 0)) for j in range(4)]
        return _prims(f"ChandelierFactory({i}).spawn_asset({i})", [(brass, arms), (bulb, bulbs), (crystal, drops)])


class EspressoMachineFactory:
    """Two-group espresso machine (front +X): steel body, black top tray, two group heads, steam wand."""
    def __init__(self, seed):
        self.seed = seed

    def spawn_asset(self, i):
        # readable from the customer side too (cafe r4/r5: its plain back read as 'an oversized stainless cube', 2 of 3): a rounded
        # body, coloured side panels, a cup-warmer rail with white cups on top, group heads and portafilters on the barista side
        r = random.Random(self.seed)
        steel = _flat("ir_steel", (0.62, 0.62, 0.64), 0.2, 1.0); black = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0)
        side = _flat(f"ir_espresso_side_{self.seed % 3}", r.choice(((0.45, 0.05, 0.04), (0.04, 0.04, 0.045), (0.8, 0.76, 0.66))), 0.3, 0.3)
        cup = _flat("ir_plate_white", (0.9, 0.9, 0.88), 0.25)
        cups = [("cyl", (-0.12 + 0.12 * (k // 4), -0.24 + 0.16 * (k % 4), 0.475), (0.035, 0.03, 0.065), (0, 0, 0)) for k in range(8)]
        return _prims(f"EspressoMachineFactory({i}).spawn_asset({i})",
                      [(steel, [("rbox", (0, 0, 0.22), (0.46, 0.6, 0.4), (0, 0, 0)),
                                ("box", (0, 0, 0.44), (0.42, 0.62, 0.012), (0, 0, 0)),               # cup-warmer tray
                                ("cyl", (0.27, -0.15, 0.24), (0.035, 0.035, 0.06), (0, math.pi / 2, 0)),
                                ("cyl", (0.27, 0.15, 0.24), (0.035, 0.035, 0.06), (0, math.pi / 2, 0)),
                                ("cyl", (0.27, 0.3, 0.3), (0.006, 0.006, 0.2), (0, 0, 0))]),       # steam wand
                       (side, [("box", (0, sy * 0.305, 0.22), (0.44, 0.012, 0.36), (0, 0, 0)) for sy in (1, -1)]),
                       (black, [("box", (0.3, sy * 0.15, 0.2), (0.12, 0.03, 0.02), (0, 0, 0)) for sy in (1, -1)] +   # portafilter handles
                               [("box", (0.24, 0, 0.03), (0.1, 0.6, 0.05), (0, 0, 0))]),                     # drip tray
                       (cup, cups)])


class CakeDomeFactory:
    """A cake under a glass dome on a stand (domes read as glass; the GT glass mask covers them)."""
    def __init__(self, seed):
        self.r = random.Random(seed)

    def spawn_asset(self, i):
        import bmesh
        r = self.r
        cake = _flat(f"ir_cake_{i % 4}", [(0.55, 0.35, 0.2), (0.85, 0.75, 0.6), (0.4, 0.2, 0.15), (0.9, 0.6, 0.65)][i % 4], 0.7)
        plate = _flat("ir_plate_white", (0.9, 0.9, 0.88), 0.25)
        glass = _flat("ir_dome_glass", (0.95, 0.95, 0.95), 0.02, transmission=1.0)
        o = _parts_object(f"CakeDomeFactory({i}).spawn_asset({i})",
                          [(plate, [(0, 0, 0.05, 0.08, 0.08, 0.1), (0, 0, 0.105, 0.3, 0.3, 0.01)]),
                           (cake, [(0, 0, 0.16, 0.2, 0.2, r.uniform(0.07, 0.12))])])
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=0.15)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.001], context="VERTS")
        bmesh.ops.translate(bm, vec=(0, 0, 0.11), verts=bm.verts)
        me = bpy.data.meshes.new(f"dome{i}"); bm.to_mesh(me); bm.free(); me.materials.append(glass)
        d = bpy.data.objects.new(f"dome{i}", me); bpy.context.scene.collection.objects.link(d); d.parent = o
        return o


class BackBarShelfFactory:
    """Open wall shelving behind the counter (front +X): 3-4 boards 0.28 m deep on a frame, 1.6-2.6 m long, 0.9-2.2 m high zone."""
    def __init__(self, seed):
        r = random.Random(seed)
        self.L = r.uniform(1.6, 2.6); self.levels = r.choice((3, 4))
        self.wood = STYLE.get("backbar") or r.choice(("walnut_slat", "oak_slat", "matte_black"))

    def spawn_asset(self, i):
        L, D = self.L, 0.28
        wood = _flat(f"ir_counter_{self.wood}", *COUNTER_FRONTS[self.wood]); metal = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0)
        zs = [1.15 + k * (1.05 / (self.levels - 1)) for k in range(self.levels)]
        groups = [(wood, [(0, 0, z, D, L, 0.03) for z in zs] + [(-D / 2 + 0.006, 0, 1.6, 0.012, L, 1.0)] +   # back panel and end
                         [(0, sx * (L / 2 - 0.015), 1.6, D, 0.03, 1.0) for sx in (-1, 1)]),               # uprights: bare boards
                  (metal, [(-D / 2 + 0.01, sx * (L / 2 - 0.03), 1.1, 0.02, 0.02, 2.2) for sx in (-1, 1)])]   # read as floating (shop r5)
        if STYLE.get("mood") in ("warm_evening", "dark_moody"):   # glowing under-shelf strips (cafe refs: the back bar is the warm light source)
            led = _flat("ir_led_warm", (1.0, 0.75, 0.45), 0.3)
            b = led.node_tree.nodes["Principled BSDF"]
            b.inputs["Emission Color"].default_value = (1.0, 0.72, 0.42, 1); b.inputs["Emission Strength"].default_value = 6.0
            groups.append((led, [(D / 2 - 0.04, 0, z - 0.02, 0.015, L - 0.08, 0.008) for z in zs]))
        return _parts_object(f"BackBarShelfFactory({i}).spawn_asset({i})", groups)


class WindowBarFactory:
    """A ledge along shop-front glass (front +X): 0.4 m deep wooden top at 1.05 m on two steel legs, 1.6-3.0 m long."""
    def __init__(self, seed):
        self.L = random.Random(seed).uniform(1.6, 3.0)

    def spawn_asset(self, i):
        L = self.L
        wood = _flat("ir_counter_top_butcher_block", *COUNTER_TOPS["butcher_block"], wood=True); metal = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0)
        return _parts_object(f"WindowBarFactory({i}).spawn_asset({i})",
                             [(wood, [(0, 0, 1.03, 0.4, L, 0.04)]),
                              (metal, [(0, sx * (L / 2 - 0.15), 0.5, 0.04, 0.04, 1.0) for sx in (-1, 1)])])


# ---- retail -------------------------------------------------------------------------------------------------------------------------
HEADER_COLOURS = [(0.75, 0.08, 0.06), (0.05, 0.3, 0.6), (0.08, 0.45, 0.2), (0.85, 0.55, 0.05), (0.45, 0.1, 0.45)]


class PlasticBinFactory:
    """An open-front plastic picking bin (front +X) in blue, grey, red or yellow, with a label slot; warehouse r5: 'every box is the
    same tan cardboard -- a staged product shot'."""
    def __init__(self, seed):
        r = random.Random(seed)
        # mid-saturation blue / charcoal / green / red: muted (wh r13: 'toy-bright') but not the cardboard's beige -- 47 bins in packing
        # r18 at the old pale greys and beige read as boxes, 3 of 3 calls: 'every shelf the same pale cream boxes'
        # deeper still: the auto-exposed packing room lifted these to 'pastel salmon, mint, sky blue -- a toy store' (wh r19, 3 of 3)
        self.c = r.choice(((0.01, 0.05, 0.22), (0.01, 0.05, 0.22), (0.05, 0.055, 0.06), (0.45, 0.25, 0.0), (0.22, 0.015, 0.01)))
        self.w, self.d, self.h = r.choice(((0.2, 0.35, 0.15), (0.3, 0.45, 0.2), (0.4, 0.6, 0.25)))

    def spawn_asset(self, i):
        w, d, h = self.w, self.d, self.h
        m = _flat(f"ir_bin_{int(self.c[0] * 100)}_{int(self.c[2] * 100)}", self.c, 0.5); lab = _flat("ir_paper", (0.93, 0.93, 0.9), 0.7)
        t = 0.008
        return _parts_object(f"PlasticBinFactory({i}).spawn_asset({i})",
                             [(m, [(0, 0, t / 2, d, w, t), (-d / 2, 0, h / 2, t, w, h), (0, w / 2, h / 2, d, t, h), (0, -w / 2, h / 2, d, t, h),
                                   (d / 2, 0, h * 0.3, t, w, h * 0.6)]),
                              (lab, [(d / 2 + 0.002, 0, h * 0.35, 0.002, w * 0.5, h * 0.18)])])


class StepLadderFactory:
    """An A-frame aluminium step ladder (front +X), 1.2-1.6 m, standing open (ABO 'ladder' drew ladder shelves and ladder-back chairs:
    warehouse r6 'a white bookcase and spindle dining chairs')."""
    def __init__(self, seed):
        self.h = random.Random(seed).choice((1.2, 1.4, 1.6))

    def spawn_asset(self, i):
        h = self.h; alu = _flat("ir_wh_alu", (0.8, 0.8, 0.82), 0.3, 1.0); grip = _flat("ir_ladder_grip", (0.8, 0.15, 0.05), 0.6)
        a = 0.22                                                  # leg splay (rad)
        legs = [("box", (sx * math.sin(a) * h / 2, sy * 0.2, h / 2 * math.cos(a)), (0.04, 0.025, h), (0, sx * -a, 0)) for sx in (1, -1) for sy in (1, -1)]
        steps = [("box", (math.sin(a) * z, 0, z), (0.1, 0.42, 0.02), (0, 0, 0)) for z in [h * (k + 1) / 5 for k in range(4)]]
        return _prims(f"StepLadderFactory({i}).spawn_asset({i})",
                      [(alu, legs + steps), (grip, [("box", (0, 0, h * math.cos(a) + 0.02), (0.2, 0.44, 0.05), (0, 0, 0))])])


class OpenBoxFactory:
    """A carton being packed: open, four flaps folded out, crumpled kraft paper inside (warehouse r7: 'no box being packed')."""
    def __init__(self, seed):
        r = random.Random(seed); self.s = (r.uniform(0.25, 0.45), r.uniform(0.2, 0.35), r.uniform(0.15, 0.3)); self.r = r

    def spawn_asset(self, i):
        x, y, z = self.s; t = 0.005; card = cardboard(); kraft = _flat("ir_kraft", (0.55, 0.42, 0.28), 0.9)
        walls = [("box", (0, 0, t / 2), (x, y, t), (0, 0, 0)), ("box", (x / 2, 0, z / 2), (t, y, z), (0, 0, 0)), ("box", (-x / 2, 0, z / 2), (t, y, z), (0, 0, 0)),
                 ("box", (0, y / 2, z / 2), (x, t, z), (0, 0, 0)), ("box", (0, -y / 2, z / 2), (x, t, z), (0, 0, 0))]
        flaps = [("box", (sx * (x / 2 + y * 0.22), 0, z + 0.02), (y * 0.45, y, t), (0, sx * -0.35, 0)) for sx in (1, -1)]
        paper = [("sph", (self.r.uniform(-x / 4, x / 4), self.r.uniform(-y / 4, y / 4), z * 0.75), (x * 0.2, y * 0.2, z * 0.18), (0, 0, k)) for k in range(3)]
        return _prims(f"OpenBoxFactory({i}).spawn_asset({i})", [(card, walls + flaps), (kraft, paper)])


class TapeGunFactory:
    """A packing-tape dispenser gun with a roll of brown tape."""
    def __init__(self, seed):
        self.c = random.Random(seed).choice(((0.9, 0.7, 0.05), (0.08, 0.08, 0.08), (0.4, 0.42, 0.45)))   # industrial, not salmon (r17)

    def spawn_asset(self, i):
        body = _flat(f"ir_tapegun_{int(self.c[0] * 100)}", self.c, 0.4); tape = _flat("ir_tape", (0.6, 0.42, 0.22), 0.3)
        return _prims(f"TapeGunFactory({i}).spawn_asset({i})",
                      [(body, [("box", (0, 0, 0.06), (0.04, 0.2, 0.03), (0, 0, 0)), ("box", (0, -0.08, 0.03), (0.035, 0.03, 0.08), (0.3, 0, 0))]),
                       (tape, [("cyl", (0, 0.04, 0.09), (0.05, 0.05, 0.05), (0, math.pi / 2, 0))])])


class KraftRollFactory:
    """A roll of kraft packing paper lying on the bench."""
    def __init__(self, seed):
        self.L = random.Random(seed).uniform(0.5, 0.8)

    def spawn_asset(self, i):
        kraft = _flat("ir_kraft", (0.55, 0.42, 0.28), 0.9)
        return _prims(f"KraftRollFactory({i}).spawn_asset({i})", [(kraft, [("cyl", (0, 0, 0.06), (0.06, 0.06, self.L), (math.pi / 2, 0, 0))])])


class HandTruckFactory:
    """A two-wheel hand truck (front +X) standing upright on its toe plate, sometimes with a carton on it (warehouse r9: 'no hand truck,
    ladder or tape -- a showroom')."""
    def __init__(self, seed):
        r = random.Random(seed); self.c = r.choice(((0.85, 0.1, 0.05), (0.15, 0.3, 0.6), (0.2, 0.2, 0.2))); self.box = r.random() < 0.5

    def spawn_asset(self, i):
        frame = _flat(f"ir_truck_{int(self.c[0] * 100)}", self.c, 0.4, 0.5); rub = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0)
        rails = [("cyl", (-0.08, sy * 0.18, 0.62), (0.015, 0.015, 1.2), (0, -0.12, 0)) for sy in (1, -1)]
        groups = [(frame, rails + [("box", (-0.08 - 0.07 * k, 0, 0.3 + 0.3 * k), (0.02, 0.36, 0.02), (0, 0, 0)) for k in range(3)] +
                   [("box", (0.08, 0, 0.02), (0.2, 0.36, 0.02), (0, 0, 0))]),
                  (rub, [("cyl", (-0.1, sy * 0.24, 0.12), (0.12, 0.12, 0.06), (math.pi / 2, 0, 0)) for sy in (1, -1)])]
        if self.box:
            groups.append((cardboard(), [("box", (0.08, 0, 0.22), (0.3, 0.32, 0.38), (0, 0, 0))]))
        return _prims(f"HandTruckFactory({i}).spawn_asset({i})", groups)


class RecycleBinsFactory:
    """An office recycling station (front +X): three lidded bins in blue / green / grey with label strips (pantry r21: 'the back and right
    walls have nothing: no recycling bins, no noticeboard')."""
    def __init__(self, seed):
        self.r = random.Random(seed)

    def spawn_asset(self, i):
        groups = []
        for k, c in enumerate(((0.1, 0.3, 0.65), (0.15, 0.5, 0.2), (0.35, 0.36, 0.38))):
            y = (k - 1) * 0.38
            groups.append((_flat(f"ir_bin_{k}", c, 0.5), [("box", (0, y, 0.38), (0.4, 0.34, 0.76), (0, 0, 0))]))
            groups.append((_flat("ir_bin_lid", (0.12, 0.12, 0.12), 0.5), [("box", (0, y, 0.775), (0.42, 0.36, 0.03), (0, 0, 0))]))
            groups.append((_flat("ir_paper", (0.93, 0.93, 0.9), 0.7), [("box", (0.201, y, 0.62), (0.002, 0.2, 0.08), (0, 0, 0))]))
        return _prims(f"RecycleBinsFactory({i}).spawn_asset({i})", groups)


class ClinicWallItemFactory:
    """Wall-mounted clinic fixtures (front +X, origin at the bottom of the back plate), the signs of use a wide shot can see (clinic
    r17: signs of use median 4-5 with props only on worktops): an eye chart, an anatomy/notice poster, a three-box glove holder, a
    yellow sharps bin, a paper-towel dispenser, a sanitizer dispenser."""
    KINDS = ("eye_chart", "clinic_poster", "glove_holder", "sharps_bin", "towel_dispenser", "wall_sanitizer", "wall_clock", "brochure_rack",
             "grab_bar", "hand_dryer", "toilet_roll", "waste_bin", "coat_hooks", "baby_change", "door_sign", "diagnostic_set",
             "cleaning_kit", "roll_shelf", "handrail")

    def __init__(self, seed, kind="clinic_poster", length=1.0):
        self.kind, self.r, self.length = kind, random.Random(seed), length

    def spawn_asset(self, i):
        r, k = self.r, self.kind
        white = _flat("ir_ac_white", (0.86, 0.86, 0.85), 0.4); ink = _flat("ir_ink", (0.05, 0.05, 0.06), 0.6)
        if k in ("eye_chart", "clinic_poster"):
            frame = _flat("ir_poster_frame", (0.75, 0.75, 0.76), 0.35, 0.8)
            W, H = (0.5, 0.75) if k == "eye_chart" else (0.6, 0.85)
            parts = [("box", (0.005, 0, H / 2), (0.01, W, H), (0, 0, 0))]
            if k == "eye_chart":                                 # rows of letters shrinking down the chart
                marks = [("box", (0.012, (j - (n - 1) / 2) * (0.36 / n), H - 0.1 - row * 0.085), (0.002, 0.36 / n * 0.6, 0.06 / (1 + row * 0.35)), (0, 0, 0))
                         for row in range(7) for n in [row + 1] for j in range(n)]
                return _prims(f"ClinicWallItemFactory({i}).spawn_asset({i})", [(frame, [("box", (0.004, 0, H / 2), (0.008, W + 0.03, H + 0.03), (0, 0, 0))]),
                                                                              (white, [("box", (0.009, 0, H / 2), (0.002, W, H), (0, 0, 0))]), (ink, marks)])
            col = _flat(f"ir_poster_{r.randrange(4)}", r.choice(((0.75, 0.3, 0.3), (0.3, 0.5, 0.7), (0.4, 0.6, 0.4), (0.85, 0.7, 0.4))), 0.6)
            lines = [("box", (0.012, 0, H - 0.3 - j * 0.05), (0.002, W * 0.75, 0.012), (0, 0, 0)) for j in range(8)]
            return _prims(f"ClinicWallItemFactory({i}).spawn_asset({i})", [(frame, [("box", (0.004, 0, H / 2), (0.008, W + 0.03, H + 0.03), (0, 0, 0))]),
                                                                          (white, [("box", (0.009, 0, H / 2), (0.002, W, H), (0, 0, 0))]),
                                                                          (col, [("sph", (0.012, 0, H - 0.15), (0.002, W * 0.25, 0.1), (0, 0, 0))]), (ink, lines)])
        if k == "handrail":                                      # a clinic corridor's wall rail, door to door: the posters and plates
            # alone read as 'four bare white walls' (floor F3 r19: corridor use 4, 3 of 3)
            L = self.length; wood = _flat("ir_rail_oak", (0.42, 0.28, 0.16), 0.45); steel = _flat("ir_chrome", (0.8, 0.8, 0.82), 0.15, 1.0)
            n = max(2, int(L / 1.0) + 1)
            brk = [("box", (0.035, -L / 2 + 0.08 + j * (L - 0.16) / (n - 1), 0.0), (0.07, 0.02, 0.03), (0, 0, 0)) for j in range(n)]
            return _prims(f"ClinicWallItemFactory({i}).spawn_asset({i})", [(wood, [("cyl", (0.075, 0, 0.0), (0.022, 0.022, L), (math.pi / 2, 0, 0))]),
                                                                          (steel, brk)])
        if k == "roll_shelf":                                    # spare toilet rolls on a small wall shelf: a restroom someone restocks
            # ('no spare paper rolls, nothing used', floors F3 r18 / H r26, 3 of 3) -- quieter than the mop kit, which read as clutter
            shelf = _flat("ir_ac_white", (0.86, 0.86, 0.85), 0.4); paper = _flat("ir_paper", (0.93, 0.93, 0.9), 0.7)
            rolls = [("cyl", (0.07, y, 0.035 + 0.055 + dz), (0.055, 0.055, 0.11), (0, 0, 0)) for y, dz in ((-0.12, 0), (0.0, 0), (0.12, 0), (-0.06, 0.11), (0.06, 0.11))]
            return _prims(f"ClinicWallItemFactory({i}).spawn_asset({i})", [(shelf, [("box", (0.07, 0, 0.0175), (0.14, 0.4, 0.035), (0, 0, 0)),
                                                                                    ("box", (0.005, 0, -0.05), (0.01, 0.4, 0.1), (0, 0, 0))]),
                                                                           (paper, rolls)])
        if k == "cleaning_kit":                                  # a restroom being looked after: a yellow mop bucket with its mop leant on
            # the wall and a wet-floor A-frame (floors H r19 / I r14: restroom signs of use 5-6, 'clinically bare', 3 of 3)
            yel = _flat("ir_janitor_yellow", (0.85, 0.65, 0.05), 0.45); grey = _flat("ir_mop_grey", (0.55, 0.55, 0.55), 0.9)
            pole = _flat("ir_mop_pole", (0.7, 0.72, 0.74), 0.3, 0.9); a_ = 0.2
            return _prims(f"ClinicWallItemFactory({i}).spawn_asset({i})", [
                (yel, [("box", (0.2, -0.15, 0.15), (0.3, 0.4, 0.3), (0, 0, 0)), ("box", (0.2, 0.0, 0.32), (0.3, 0.1, 0.04), (0, 0, 0)),
                       ("box", (0.24, 0.42, 0.3), (0.025, 0.32, 0.62), (0, a_, 0))]),   # ONE sign face leaning on a back leg: the two
                # A-frame leaves read as 'two wet-floor signs side by side' (floor H r25, 3 of 3)
                (_flat("ir_mop_pole", (0.7, 0.72, 0.74), 0.3, 0.9), [("box", (0.38, 0.42, 0.29), (0.015, 0.02, 0.58), (0, -0.4, 0))]),
                # the two leaves meet at the top: 0.24 m apart they read as two or three loose signs (floor E3 r13, 3 of 3)
                (grey, [("box", (0.2, -0.22, 0.31), (0.18, 0.18, 0.06), (0, 0, 0))]),
                # no mop pole: leant on the wall it read as 'a loose rod, debris' (floor F3 r16, 3 of 3)
                (_flat("ir_ink", (0.05, 0.05, 0.06), 0.6), [("box", (0.24 - 0.016, 0.42, 0.37), (0.002, 0.18, 0.14), (0, a_, 0))])])
        if k == "glove_holder":
            boxes = [(_flat(f"ir_glovebox_{j}", c, 0.6), [("box", (0.07, 0, 0.06 + j * 0.13), (0.12, 0.26, 0.11), (0, 0, 0))])
                     for j, c in enumerate(((0.3, 0.35, 0.75), (0.55, 0.3, 0.65), (0.85, 0.85, 0.88)))]
            return _prims(f"ClinicWallItemFactory({i}).spawn_asset({i})", [(white, [("box", (0.005, 0, 0.21), (0.01, 0.3, 0.42), (0, 0, 0))])] + boxes)
        if k == "sharps_bin":
            # red body on a grey wall bracket, white lid and label (clinic r19: the yellow box with a red cap read as a desk lamp, 2 of 3 calls)
            red = _flat("ir_sharps_red", (0.62, 0.06, 0.05), 0.35); lid = _flat("ir_sharps_lid", (0.9, 0.9, 0.88), 0.4)
            steel = _flat("ir_sharps_bracket", (0.55, 0.56, 0.58), 0.35, 1.0)
            return _prims(f"ClinicWallItemFactory({i}).spawn_asset({i})", [(steel, [("box", (0.006, 0, 0.17), (0.012, 0.2, 0.34), (0, 0, 0)),
                                                                                   ("box", (0.08, 0, 0.012), (0.15, 0.24, 0.012), (0, 0, 0))]),
                                                                          (red, [("box", (0.09, 0, 0.14), (0.15, 0.22, 0.24), (0, 0, 0))]),
                                                                          (lid, [("box", (0.09, 0, 0.275), (0.16, 0.23, 0.03), (0, 0, 0)),
                                                                                 ("box", (0.166, 0, 0.15), (0.002, 0.12, 0.08), (0, 0, 0))])])
        if k == "wall_clock":                                    # reception r22: 'no clock, no signage' (3 of 3)
            rim = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0)
            hands = [("box", (0.032, 0, 0.18 + 0.05), (0.004, 0.012, 0.1), (0, 0, 0)), ("box", (0.032, 0.04, 0.18), (0.004, 0.08, 0.01), (0, 0, 0))]
            return _prims(f"ClinicWallItemFactory({i}).spawn_asset({i})", [(rim, [("cyl", (0.02, 0, 0.18), (0.18, 0.18, 0.04), (0, math.pi / 2, 0))] + hands),
                                                                          (white, [("cyl", (0.03, 0, 0.18), (0.165, 0.165, 0.01), (0, math.pi / 2, 0))])])
        if k == "brochure_rack":                                 # clear pockets with coloured leaflets (reception: 'no brochure rack')
            acr = _flat("ir_acrylic", (0.9, 0.92, 0.93), 0.1, transmission=0.8)
            cols = [_flat(f"ir_leaflet_{j}", c, 0.6) for j, c in enumerate(((0.15, 0.45, 0.7), (0.85, 0.85, 0.82), (0.2, 0.55, 0.35), (0.85, 0.5, 0.15)))]
            pockets = [("box", (0.05, -0.15 + (j % 3) * 0.15, 0.1 + (j // 3) * 0.22), (0.04, 0.13, 0.16), (0, 0, 0)) for j in range(6)]
            return _prims(f"ClinicWallItemFactory({i}).spawn_asset({i})", [(white, [("box", (0.005, 0, 0.3), (0.01, 0.48, 0.62), (0, 0, 0))]), (acr, pockets)] +
                          [(cols[j % 4], [("box", (0.045, -0.15 + (j % 3) * 0.15, 0.13 + (j // 3) * 0.22), (0.01, 0.1, 0.2), (0, 0, 0))]) for j in range(6)])
        if k == "grab_bar":                                      # restrooms read 'empty with a toilet in it' (floor D3 r7, 3 of 3)
            chrome = _flat("ir_chrome", (0.8, 0.8, 0.82), 0.15, 1.0)
            return _prims(f"ClinicWallItemFactory({i}).spawn_asset({i})", [(chrome, [
                ("cyl", (0.07, 0, 0.06), (0.018, 0.018, 0.75), (math.pi / 2, 0, 0)),
                ("box", (0.035, 0.35, 0.06), (0.07, 0.03, 0.03), (0, 0, 0)), ("box", (0.035, -0.35, 0.06), (0.07, 0.03, 0.03), (0, 0, 0))])])
        if k == "diagnostic_set":                                # wall BP gauge + otoscope/ophthalmoscope handles (floor D3 r9-r11, 3 of 3)
            grey = _flat("ir_diag_grey", (0.55, 0.57, 0.6), 0.4); blk = _flat("ir_black_plastic", (0.04, 0.04, 0.045), 0.5)
            cuff = _flat("ir_bp_cuff", (0.1, 0.18, 0.35), 0.7)
            return _prims(f"ClinicWallItemFactory({i}).spawn_asset({i})", [
                (grey, [("box", (0.01, 0, 0.22), (0.02, 0.42, 0.44), (0, 0, 0))]),
                (white, [("cyl", (0.03, -0.09, 0.32), (0.07, 0.07, 0.02), (0, math.pi / 2, 0))]),
                (blk, [("cyl", (0.045, 0.08, 0.28), (0.018, 0.018, 0.16), (0, 0, 0)), ("cyl", (0.045, 0.14, 0.28), (0.018, 0.018, 0.16), (0, 0, 0)),
                       ("box", (0.035, -0.09, 0.32), (0.004, 0.004, 0.05), (0, 0, 0.6))]),
                (cuff, [("rbox", (0.05, -0.09, 0.1), (0.06, 0.16, 0.12), (0, 0, 0))])])
        if k == "door_sign":                                     # a room plate beside each corridor door (floors D3/E3/F3: 'no room signs')
            plate = _flat("ir_door_sign", r.choice(((0.12, 0.3, 0.45), (0.2, 0.22, 0.25), (0.1, 0.4, 0.38))), 0.4)
            ink3 = _flat("ir_sign_ink", (0.95, 0.95, 0.93), 0.5)
            lines = [("box", (0.012, -0.08 + j * 0.04, 0.075), (0.002, 0.03, 0.035), (0, 0, 0)) for j in range(r.randint(3, 5))]
            return _prims(f"ClinicWallItemFactory({i}).spawn_asset({i})", [(plate, [("box", (0.005, 0, 0.075), (0.01, 0.3, 0.15), (0, 0, 0))]),
                                                                          (ink3, lines + [("box", (0.012, 0.09, 0.075), (0.002, 0.06, 0.06), (0, 0, 0))])])
        if k == "baby_change":                                   # a fold-down baby-change unit (floors D3/J: 'an oversized WC, nothing in use')
            grey = _flat("ir_babychange", (0.82, 0.84, 0.86), 0.4); ink2 = _flat("ir_sign_blue", (0.1, 0.3, 0.6), 0.5)
            return _prims(f"ClinicWallItemFactory({i}).spawn_asset({i})", [(grey, [("rbox", (0.06, 0, 0.27), (0.12, 0.86, 0.54), (0, 0, 0)),
                                                                                  ("box", (0.121, 0, 0.47), (0.004, 0.7, 0.03), (0, 0, 0))])])   # a
            # handle strip, no blue square: the sign read as 'a clinic wall unit' in café WCs (floor G r14, 3 of 3)
        if k == "coat_hooks":                                    # a changing room's hook rail with two jackets (floor F3 r7: 'no coat hooks')
            oak = _flat("ir_hook_board", (0.55, 0.42, 0.28), 0.5); chrome = _flat("ir_chrome", (0.8, 0.8, 0.82), 0.15, 1.0)
            jk = [_flat(f"ir_jacket_{j}", c, 0.8) for j, c in enumerate(((0.12, 0.16, 0.28), (0.45, 0.12, 0.1)))]
            hooks = [("box", (0.04, -0.36 + j * 0.24, 0.0), (0.06, 0.015, 0.015), (0, 0, 0)) for j in range(4)]
            return _prims(f"ClinicWallItemFactory({i}).spawn_asset({i})", [(oak, [("box", (0.01, 0, 0.02), (0.02, 0.9, 0.09), (0, 0, 0))]),
                (chrome, hooks), (jk[0], [("rbox", (0.09, -0.36, -0.38), (0.1, 0.42, 0.72), (0, 0, 0))]),
                (jk[1], [("rbox", (0.09, 0.12, -0.33), (0.1, 0.4, 0.62), (0, 0, 0))])])
        if k == "toilet_roll":                                   # restrooms: 'no toilet-roll holder, no bin' (floors C/D3/F3/H, 3 of 3 each)
            chrome = _flat("ir_chrome", (0.8, 0.8, 0.82), 0.15, 1.0); paper = _flat("ir_paper", (0.93, 0.93, 0.9), 0.7)
            return _prims(f"ClinicWallItemFactory({i}).spawn_asset({i})", [(chrome, [("box", (0.01, 0, 0.06), (0.02, 0.16, 0.08), (0, 0, 0)),
                                                                                    ("cyl", (0.07, 0, 0.04), (0.008, 0.008, 0.15), (math.pi / 2, 0, 0))]),
                                                                          (paper, [("cyl", (0.07, 0, 0.04), (0.055, 0.055, 0.1), (math.pi / 2, 0, 0))])])
        if k == "waste_bin":                                     # an open bin at the wall (z = 0) with used paper towels above its rim:
            # a closed pedal bin showed 'nothing in the bins, no sign of use' in every restroom (floors H/I/J r24-r40, 3 of 3 each)
            steel = _flat("ir_bin_steel", (0.62, 0.63, 0.64), 0.3, 1.0); blk = _flat("ir_black_plastic", (0.04, 0.04, 0.045), 0.5)
            paper = _flat("ir_paper", (0.93, 0.93, 0.9), 0.7)
            wads = [("sph", (0.16 + dx, dy, 0.42 + dz), (0.075, 0.065, 0.05), (0, 0, 0)) for dx, dy, dz in   # heaped over the rim:
                    ((0, 0, 0.03), (0.06, 0.05, 0.0), (-0.05, -0.06, 0.01), (0.04, -0.04, 0.07), (-0.06, 0.04, 0.05),   # smaller wads were a
                     (0.0, 0.07, 0.04), (-0.02, -0.01, 0.1), (0.07, -0.06, 0.03))]   # few pixels at 512 px, use 5-6 (floor H r41, 3 of 3)
            return _prims(f"ClinicWallItemFactory({i}).spawn_asset({i})", [(paper, wads), (steel, [("cyl", (0.16, 0, 0.21), (0.14, 0.14, 0.42), (0, 0, 0))]),
                                                                          (blk, [("box", (0.32, 0, 0.02), (0.06, 0.1, 0.02), (0, 0, 0)),
                                                                                 ("cyl", (0.16, 0, 0.01), (0.145, 0.145, 0.02), (0, 0, 0))])])
        if k == "hand_dryer":                                    # brushed steel: a white box on white tile was never seen (floor H r27, 3 of 3)
            steel = _flat("ir_dryer_steel", (0.6, 0.61, 0.63), 0.3, 1.0)
            return _prims(f"ClinicWallItemFactory({i}).spawn_asset({i})", [(steel, [("rbox", (0.1, 0, 0.17), (0.2, 0.3, 0.34), (0, 0, 0))]),
                                                                          (ink, [("box", (0.12, 0, 0.005), (0.08, 0.16, 0.02), (0, 0, 0))])])
        if k == "towel_dispenser":
            return _prims(f"ClinicWallItemFactory({i}).spawn_asset({i})", [(white, [("box", (0.06, 0, 0.18), (0.12, 0.28, 0.36), (0, 0, 0))]),
                                                                          (ink, [("box", (0.121, 0, 0.03), (0.002, 0.2, 0.01), (0, 0, 0))])])
        return _prims(f"ClinicWallItemFactory({i}).spawn_asset({i})", [(white, [("box", (0.05, 0, 0.12), (0.1, 0.11, 0.24), (0, 0, 0))]),
                                                                      (ink, [("box", (0.101, 0, 0.05), (0.002, 0.06, 0.03), (0, 0, 0))])])


class ToiletStallFactory:
    """A commercial WC cubicle (front +X = the door side): laminate side panels and a half-open door on legs, a white wall-hung
    toilet and cistern box inside, a paper holder (floor scenes: 'two toilets loose in an open room', 3 of 3 calls)."""
    def __init__(self, seed):
        r = random.Random(seed); self.c = r.choice(((0.45, 0.52, 0.58), (0.55, 0.6, 0.6), (0.6, 0.53, 0.46)))   # mid laminates: navy read black (floor H r4), white
        # stalls vanished against white walls (floor J r5, 3 of 3)

    def spawn_asset(self, i):
        D, W, H = 1.5, 0.95, 1.95
        panel = _flat(f"ir_stall_{int(self.c[2] * 100)}", self.c, 0.4); ceramic = _flat("ir_ceramic_white", (0.92, 0.92, 0.9), 0.08)
        chrome = _flat("ir_chrome", (0.8, 0.8, 0.82), 0.15, 1.0)
        sides = [("box", (0, sy * W / 2, H / 2 + 0.12), (D, 0.025, H - 0.24), (0, 0, 0)) for sy in (1, -1)]
        # a cubicle front: a fixed pilaster, a door hinged to it and opened ~35 deg, a chrome headrail over front and sides -- two side
        # panels and a loose door read as 'free-standing screens, no door, no headrail' (floor J r24, 3 of 3)
        pw, dw, a_ = 0.25, W - 0.25 - 0.02, 0.22   # ajar: at 0.6 rad the leaf 'swung into the only aisle' (floor H r43, 3 of 3)
        pil = [("box", (D / 2, W / 2 - pw / 2, H / 2 + 0.06), (0.03, pw, H - 0.12), (0, 0, 0))]
        hx, hy = D / 2, W / 2 - pw
        door = [("box", (hx + math.sin(a_) * dw / 2, hy - math.cos(a_) * dw / 2, H / 2 + 0.12), (0.025, dw, H - 0.24), (0, 0, a_))]
        rail = [("box", (D / 2, 0, H + 0.02), (0.04, W + 0.04, 0.04), (0, 0, 0))] + \
               [("box", (0, sy * W / 2, H + 0.02), (D, 0.04, 0.04), (0, 0, 0)) for sy in (1, -1)]
        lock = [("box", (D / 2 + 0.02, W / 2 - pw + 0.04, 1.05), (0.02, 0.05, 0.05), (0, 0, 0))]
        legs = [("cyl", (x, sy * W / 2, 0.06), (0.015, 0.015, 0.12), (0, 0, 0)) for x in (-D / 2 + 0.05, D / 2 - 0.05) for sy in (1, -1)]
        bowl = [("rbox", (-D / 2 + 0.3, 0, 0.4), (0.5, 0.38, 0.32), (0, 0, 0)), ("box", (-D / 2 + 0.07, 0, 0.75), (0.12, 0.4, 0.4), (0, 0, 0)),
                ("box", (-D / 2 + 0.06, 0, 0.12), (0.1, 0.2, 0.24), (0, 0, 0))]   # bowl, cistern, wall bracket
        return _prims(f"ToiletStallFactory({i}).spawn_asset({i})", [(panel, sides + door + pil), (chrome, legs + rail + lock + [("cyl", (-D / 2 + 0.6, W / 2 - 0.04, 0.7),
                                                                    (0.06, 0.06, 0.1), (math.pi / 2, 0, 0))]), (ceramic, bowl)])


class WashBasinFactory:
    """Commercial wall-hung washbasin (front +X): white ceramic bowl on the wall, chrome tap, mirror above, soap and paper-towel
    dispensers beside (floor scenes 2026-10-16: Infinigen's pedestal sinks drew pink/green residential basins, 3 of 3 calls)."""
    def __init__(self, seed):
        self.seed = seed

    def spawn_asset(self, i):
        white = _flat("ir_ac_white", (0.86, 0.86, 0.85), 0.4); ceramic = _flat("ir_ceramic_white", (0.92, 0.92, 0.9), 0.08)
        chrome = _flat("ir_chrome", (0.8, 0.8, 0.82), 0.15, 1.0); mirror = _flat("ir_mirror", (0.9, 0.92, 0.93), 0.02, 1.0)
        return _prims(f"WashBasinFactory({i}).spawn_asset({i})",
                      [(ceramic, [("rbox", (0.22, 0, 0.8), (0.42, 0.55, 0.16), (0, 0, 0))]),
                       (chrome, [("cyl", (0.06, 0, 0.93), (0.015, 0.015, 0.12), (0, 0, 0)), ("box", (0.11, 0, 0.98), (0.1, 0.02, 0.02), (0, 0, 0)),
                                 ("cyl", (0.12, 0, 0.375), (0.025, 0.025, 0.75), (0, 0, 0))] +        # waste pipe to the floor: _place
                                [("box", (0.014, 0, 1.45 + sz * 0.41), (0.025, 0.64, 0.02), (0, 0, 0)) for sz in (1, -1)] +   # a chrome
                                [("box", (0.014, sy * 0.31, 1.45), (0.025, 0.02, 0.84), (0, 0, 0)) for sy in (1, -1)]),       # frame: the bare
                       # reflection of the tiles read as 'a tiled panel tilted off the wall' (floors A2 r6 / F3 r7, 4 calls)
                                                                                                       # stands an asset on its lowest point
                       (mirror, [("box", (0.01, 0, 1.45), (0.01, 0.6, 0.8), (0, 0, 0))]),
                       (white, [("box", (0.05, 0.45, 1.15), (0.1, 0.12, 0.22), (0, 0, 0)),              # soap
                                ("box", (0.06, -0.55, 1.3), (0.12, 0.3, 0.38), (0, 0, 0))])])         # paper towels


class LockerFactory:
    """A bank of 3-4 grey steel staff/patient lockers with vents and handles (front +X): a changing room's defining piece."""
    def __init__(self, seed):
        r = random.Random(seed); self.n = r.choice((3, 4)); self.c = r.choice(((0.55, 0.57, 0.6), (0.2, 0.35, 0.55), (0.75, 0.76, 0.76)))

    def spawn_asset(self, i):
        n, w, d, h = self.n, 0.4, 0.5, 1.8
        steel = _flat(f"ir_locker_{int(self.c[2] * 100)}", self.c, 0.4, 0.6); dark = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0)
        L = n * w
        doors = [("box", (d / 2, -L / 2 + (k + 0.5) * w, h / 2 + 0.05), (0.01, w - 0.02, h - 0.12), (0, 0, 0)) for k in range(n)]
        vents = [("box", (d / 2 + 0.006, -L / 2 + (k + 0.5) * w, h - 0.25 - j * 0.04), (0.004, w * 0.5, 0.012), (0, 0, 0))
                 for k in range(n) for j in range(4)]
        handles = [("box", (d / 2 + 0.015, -L / 2 + (k + 0.5) * w + w * 0.35, h / 2), (0.02, 0.02, 0.1), (0, 0, 0)) for k in range(n)]
        return _prims(f"LockerFactory({i}).spawn_asset({i})", [(steel, [("box", (0, 0, h / 2 + 0.05), (d, L, h - 0.1), (0, 0, 0))] + doors),
                                                                (dark, vents + handles + [("box", (0, 0, 0.025), (d - 0.04, L, 0.05), (0, 0, 0))])])


class ChangingBenchFactory:
    """A plain backless changing-room bench: slatted wood top on two steel legs (front +X)."""
    def __init__(self, seed):
        self.L = random.Random(seed).choice((1.2, 1.5))

    def spawn_asset(self, i):
        L = self.L
        wood = _flat("ir_bench_slat", (0.55, 0.4, 0.26), 0.5, wood=True); steel = _flat("ir_desk_frame", (0.75, 0.75, 0.76), 0.35, 0.8)
        slats = [("box", (-0.13 + k * 0.09, 0, 0.45), (0.07, L, 0.03), (0, 0, 0)) for k in range(4)]
        legs = [("box", (0, sy * (L / 2 - 0.12), 0.22), (0.3, 0.04, 0.44), (0, 0, 0)) for sy in (1, -1)]
        return _prims(f"ChangingBenchFactory({i}).spawn_asset({i})", [(wood, slats), (steel, legs)])


class TowelStackFactory:
    """Two to four folded towels in a stack (physio beds; clinic r18: 'no towels -- a showroom')."""
    def __init__(self, seed):
        r = random.Random(seed); self.n = r.randint(2, 4); self.c = r.choice(((0.92, 0.92, 0.9), (0.6, 0.75, 0.85), (0.75, 0.82, 0.78)))

    def spawn_asset(self, i):
        m = _flat(f"ir_towel_{int(self.c[0] * 100)}", self.c, 0.95)
        return _prims(f"TowelStackFactory({i}).spawn_asset({i})",
                      [(m, [("box", (0.005 * (k % 2), 0, 0.02 + k * 0.04), (0.3, 0.42, 0.04), (0, 0, 0.05 * (k % 2))) for k in range(self.n)])])


class PhysioKitFactory:
    """Therapy supplies against a wall (front +X): an open steel shelf with rolled towels, foam rollers and coiled bands, and two gym
    balls on the floor beside it (clinic r21: physio signs of use 3-4 -- 'bare mats, no balls, bands or towels')."""
    def __init__(self, seed):
        r = random.Random(seed); self.side = r.choice((1, -1))
        self.ball = r.choice(((0.1, 0.25, 0.5), (0.45, 0.3, 0.05), (0.12, 0.35, 0.2), (0.4, 0.4, 0.42)))

    def spawn_asset(self, i):
        sd = self.side
        steel = _flat("ir_desk_frame", (0.75, 0.75, 0.76), 0.35, 0.8); towel = _flat("ir_towel_92", (0.92, 0.92, 0.9), 0.95)
        foam = _flat("ir_foam_roller", (0.05, 0.25, 0.55), 0.8); band = [_flat(f"ir_band_{k}", c, 0.5) for k, c in
                                                                         enumerate(((0.6, 0.08, 0.06), (0.1, 0.3, 0.6), (0.5, 0.5, 0.05)))]
        ball = _flat(f"ir_gymball_{int(self.ball[2] * 100)}", self.ball, 0.3)
        W, D = 1.0, 0.4
        frame = [("box", (0, sy * (W / 2 - 0.015), 0.45), (D, 0.03, 0.9), (0, 0, 0)) for sy in (1, -1)] + \
                [("box", (0, 0, z), (D, W, 0.02), (0, 0, 0)) for z in (0.05, 0.45, 0.88)]
        towels = [("box", (0.02, -0.3 + k * 0.2, 0.89 + 0.05), (0.3, 0.16, 0.08), (0, 0, 0)) for k in range(4)]
        # standing upright on the middle shelf: lying flat and dark they read as 'slippers on a shoe rack' (physio r32)
        rollers = [("cyl", (0.0, -0.3 + k * 0.2, 0.46 + 0.19), (0.07, 0.07, 0.38), (0, 0, 0)) for k in range(4)]
        bands = [(band[k], [("cyl", (0.02, -0.3 + k * 0.3, 0.1), (0.1, 0.1, 0.06), (0, 0, 0))]) for k in range(3)]
        balls = [("sph", (D / 2 + 0.33, sd * 0.28, 0.33), (0.33, 0.33, 0.33), (0, 0, 0)),     # both in front, within the shelf's 1 m:
                 ("sph", (D / 2 + 0.27, -sd * 0.33, 0.27), (0.27, 0.27, 0.27), (0, 0, 0))]   # 2.2 / 1.6 m wide found no wall (r22, r24)
        return _prims(f"PhysioKitFactory({i}).spawn_asset({i})", [(steel, frame), (towel, towels), (foam, rollers), (ball, balls)] + bands)


class DumbbellRackFactory:
    """A two-tier dumbbell rack (front +X) with pairs of hex dumbbells, light to heavy (physio; clinic r18: 'no weights')."""
    def __init__(self, seed):
        self.r = random.Random(seed)

    def spawn_asset(self, i):
        frame = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0); bell = _flat("ir_dumbbell", (0.12, 0.12, 0.13), 0.5, 0.3)
        grip = _flat("ir_chrome", (0.8, 0.8, 0.82), 0.15, 1.0)
        legs = [("box", (sx * 0.15, sy * 0.48, 0.35), (0.04, 0.04, 0.7), (0, 0, 0)) for sx in (1, -1) for sy in (1, -1)]
        tiers = [("box", (0.05, 0, 0.35), (0.25, 1.0, 0.02), (0, 0, 0)), ("box", (0.0, 0, 0.65), (0.25, 1.0, 0.02), (0, 0, 0))]
        bells, grips = [], []
        for t, z in enumerate((0.36, 0.66)):
            for k in range(4):
                y = -0.36 + k * 0.24; s_ = 0.035 + 0.008 * (k + 4 * t)
                for dx in (-0.08, 0.08):
                    bells.append(("cyl", (0.05 + dx, y, z + s_), (s_, s_, 0.05), (0, math.pi / 2, 0)))
                grips.append(("cyl", (0.05, y, z + s_), (0.014, 0.014, 0.12), (0, math.pi / 2, 0)))
        return _prims(f"DumbbellRackFactory({i}).spawn_asset({i})", [(frame, legs + tiers), (bell, bells), (grip, grips)])


class StorageRackFactory:
    """Steel warehouse rack (front +X): two upright frames per bay, orange step beams and solid decks on 4-5 levels, so the shelf
    filler finds every level (ABO wire racks: 0 items stocked on 9 racks, warehouse r1 2026-10-16: 'every rack is bare')."""
    def __init__(self, seed):
        r = random.Random(seed)
        self.L = r.choice((1.8, 2.4)); self.D = r.choice((0.8, 1.0)); self.H = r.choice((3.0, 3.6))   # pallet-rack height under a 5 m roof
                                                                                                # (warehouse r10: 'short shelving -- a stockroom')
        self.up = _ROOM_PICK.setdefault("rack_up", r.choice(((0.1, 0.22, 0.5), (0.35, 0.37, 0.4), (0.82, 0.82, 0.8))))   # one rack family
        self.deck = _ROOM_PICK.setdefault("rack_deck", r.choice(((0.62, 0.5, 0.36), (0.6, 0.62, 0.64))))   # per room (floor J r11: 'two
        # rack styles mixed', chipboard or galvanised)

    def spawn_asset(self, i):
        L, D, H = self.L, self.D, self.H
        beam_rgb = getattr(self, "beam_rgb", (0.85, 0.32, 0.05))
        up = _flat(f"ir_rack_up_{int(self.up[2] * 100)}", self.up, 0.45, 0.6); beam = _flat(f"ir_rack_beam_{int(beam_rgb[1] * 100)}", beam_rgb, 0.4, 0.5)
        deck = _flat(f"ir_rack_deck_{int(self.deck[0] * 100)}", self.deck, 0.6, 0.0 if self.deck[0] > self.deck[2] + 0.1 else 0.7)
        posts = [(sx * (D / 2 - 0.04), sy * (L / 2 - 0.04), H / 2, 0.07, 0.07, H) for sx in (1, -1) for sy in (1, -1)]
        braces = [(0, sy * (L / 2 - 0.04), z, D - 0.08, 0.03, 0.03) for sy in (1, -1) for z in (0.3, H / 2, H - 0.3)]
        zs = [0.12] + [0.12 + k * (H - 0.25) / 4.6 for k in range(1, 5)] + [H - 0.04]
        beams = [(sx * (D / 2 - 0.04), 0, z - 0.06, 0.05, L - 0.08, 0.1) for sx in (1, -1) for z in zs]
        decks = [(0, 0, z + 0.005, D - 0.06, L - 0.1, 0.02) for z in zs]
        return _parts_object(f"StorageRackFactory({i}).spawn_asset({i})", [(up, posts + braces), (beam, beams), (deck, decks)])


class SupplyShelfFactory(StorageRackFactory):
    """Clinic supply shelving: the same rack (its name stays StorageRackFactory for the shelf filler) in white, 2 m tall -- orange
    pallet racking read as 'a shop back room, not sterilisation' (floor E3 r6, 3 of 3)."""
    def __init__(self, seed):
        super().__init__(seed)
        r = random.Random(seed + 1)
        self.L = r.choice((0.9, 1.2)); self.D = 0.45; self.H = 2.0
        self.up = (0.9, 0.9, 0.9); self.deck = (0.86, 0.87, 0.88); self.beam_rgb = (0.88, 0.88, 0.88)


class StockShelfFactory(SupplyShelfFactory):
    """Back-stockroom shelving (name stays StorageRackFactory for the filler): galvanised, 1.5-1.8 m runs, 2.1 m tall -- the 0.9-1.2 m
    clinic unit read as 'one small shelf in an empty room' in café/shop stockrooms (floors G r13, H r14, 3 of 3 each)."""
    def __init__(self, seed):
        super().__init__(seed)
        r = random.Random(seed + 3)
        self.L = r.choice((1.5, 1.8)); self.D = 0.55; self.H = 2.1
        self.up = (0.62, 0.63, 0.65); self.deck = (0.6, 0.62, 0.64); self.beam_rgb = (0.62, 0.63, 0.65)


class OfficeShelfFactory(SupplyShelfFactory):
    """A plain office bookcase / binder shelf (name stays StorageRackFactory for the filler): the Infinigen bookcase came out as a
    purple kids' cube shelf (floor A2 r5, 3 of 3)."""
    def __init__(self, seed):
        super().__init__(seed)
        r = random.Random(seed + 2)
        self.L = r.choice((0.8, 1.0)); self.D = 0.35; self.H = 1.8
        c = r.choice(((0.86, 0.86, 0.85), (0.32, 0.33, 0.35)))   # no pine: 'a raw pine rack of books -- a home study' (floor F3 r7, 3/3)
        self.up = c; self.deck = c; self.beam_rgb = c

    def spawn_asset(self, i):
        # a closed carcass -- side panels, back, top, plinth -- not posts and beams: 'a white ladder utility rack' (floor A2 r6, 3 of 3)
        L, D, H, t = self.L, self.D, self.H, 0.02
        m = _flat(f"ir_office_shelf_{int(self.up[0] * 100)}", self.up, 0.45)
        zs = [0.08] + [0.08 + k * (H - 0.12) / 4 for k in range(1, 4)]
        parts = [(0, sy * (L / 2 - t / 2), H / 2, D, t, H) for sy in (1, -1)] + [(-D / 2 + t / 2, 0, H / 2, t, L, H), (0, 0, H - t / 2, D, L, t),
                 (D / 2 - 0.02, 0, 0.04, 0.02, L - 2 * t, 0.08)] + [(0, 0, z, D - t, L - 2 * t, t) for z in zs]
        return _parts_object(f"StorageRackFactory({i}).spawn_asset({i})", [(m, parts)])


class AutoclaveFactory:
    """Benchtop steam autoclave (front +X): a steel body with a round dark chamber door and a small display -- the piece that makes a
    sterilisation room read as one (floor E3 r6: 'no autoclave, a stockroom with a kitchenette', 3 of 3)."""
    def __init__(self, seed):
        # under the 1.45 m upper cabinets of a 0.94 m worktop (floor E3 r7: 0.45 m tall / 0.5 m deep found 'no fit', 3 of 3 saw none)
        r = random.Random(seed); self.W = r.choice((0.42, 0.5)); self.H = r.choice((0.34, 0.38))

    def spawn_asset(self, i):
        W, H, D = self.W, self.H, 0.42
        steel = _flat("ir_autoclave_body", (0.78, 0.79, 0.8), 0.3, 0.7); door = _flat("ir_autoclave_door", (0.12, 0.13, 0.14), 0.35, 0.8)
        disp = _flat("ir_autoclave_display", (0.15, 0.45, 0.65), 0.2)
        return _prims(f"AutoclaveFactory({i}).spawn_asset({i})", [
            (steel, [("box", (0, 0, H / 2), (D, W, H), (0, 0, 0)),          # a box, not a rounded blob ('a chrome
                      ("box", (0.02, W / 2 + 0.2, 0.08), (0.3, 0.26, 0.16), (0, 0, 0))]),   # sphere like a speaker', E3 r10) + an ultrasonic bath
            # a square chamber door with a lever, not a round porthole: two round-door boxes read as 'a washer and dryer' (floor E3 r15, 3/3)
            (door, [("box", (D / 2 + 0.008, -W * 0.08, H * 0.48), (0.016, W * 0.62, H * 0.62), (0, 0, 0)),
                    ("box", (D / 2 + 0.03, -W * 0.08 + W * 0.26, H * 0.48), (0.03, 0.02, H * 0.3), (0, 0, 0))]),
            (disp, [("box", (D / 2 + 0.005, W * 0.33, H * 0.62), (0.01, W * 0.18, H * 0.16), (0, 0, 0))])])


class DisplayCoolerFactory:
    """Upright glass-door drinks cooler (front +X), 0.75 x 0.7 x 2.0 m: a dark cabinet, a lit header, an aluminium-framed glass
    door, a white-lit interior and 5 shelves of bottles and cans in rows. Infinigen's BeverageFridge is an under-counter unit and
    rendered as 'knee-high black boxes' (shop r2 critic)."""
    PACK = ((0.75, 0.1, 0.08), (0.1, 0.35, 0.7), (0.95, 0.6, 0.1), (0.2, 0.55, 0.2), (0.85, 0.85, 0.8), (0.1, 0.1, 0.1))

    def __init__(self, seed):
        r = random.Random(seed)
        self.r = r; self.body = r.choice(((0.85, 0.85, 0.84), (0.6, 0.6, 0.62)))   # no black: a black side edge-on read as a slab (floor I r2-r4, 3/3)   # style eval G: a coral cooler broke two cafes

    def spawn_asset(self, i):
        r, W, D, H = self.r, 0.75, 0.7, 2.0
        body = _flat(f"ir_cooler_{int(self.body[0] * 100)}", self.body, 0.4, 0.3); alu = _flat("ir_wh_alu", (0.8, 0.8, 0.82), 0.3, 1.0)
        glass = _flat("ir_cooler_glass", (0.9, 0.95, 0.97), 0.03, transmission=0.95)
        lit = _flat("ir_cooler_lit", (1.0, 1.0, 1.0), 0.4)
        lit.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (0.92, 0.97, 1.0, 1)
        lit.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 2.5
        shell = [("box", (-D / 2 + 0.02, 0, H / 2), (0.04, W, H), (0, 0, 0)), ("box", (0, W / 2 - 0.02, H / 2), (D, 0.04, H), (0, 0, 0)),
                 ("box", (0, -W / 2 + 0.02, H / 2), (D, 0.04, H), (0, 0, 0)), ("box", (0, 0, 0.06), (D, W, 0.12), (0, 0, 0)),
                 ("box", (0, 0, H - 0.1), (D, W, 0.2), (0, 0, 0))]
        frame = [("box", (D / 2 - 0.01, 0, 0.14), (0.03, W, 0.04), (0, 0, 0)), ("box", (D / 2 - 0.01, 0, H - 0.22), (0.03, W, 0.04), (0, 0, 0)),
                 ("box", (D / 2 - 0.01, W / 2 - 0.03, H / 2), (0.03, 0.04, H - 0.32), (0, 0, 0)),
                 ("box", (D / 2 - 0.01, -W / 2 + 0.03, H / 2), (0.03, 0.04, H - 0.32), (0, 0, 0)),
                 ("box", (D / 2 + 0.02, -W / 2 + 0.08, H / 2), (0.03, 0.025, 0.7), (0, 0, 0))]        # handle
        shelves = [("box", (0.0, 0, z), (D - 0.12, W - 0.08, 0.012), (0, 0, 0)) for z in (0.16, 0.5, 0.84, 1.18, 1.52)]
        stock = {}
        for z in (0.16, 0.5, 0.84, 1.18, 1.52):
            c = r.choice(self.PACK); can = r.random() < 0.4
            h, rad = (0.12, 0.033) if can else (0.24, 0.035)
            for row in range(3):
                for k in range(int((W - 0.12) / (2 * rad + 0.008))):
                    if r.random() < 0.1:                         # a few sold
                        continue
                    y = -W / 2 + 0.07 + rad + k * (2 * rad + 0.008)
                    stock.setdefault(c, []).append(("cyl", (D / 2 - 0.1 - row * 0.12, y, z + 0.006 + h / 2), (rad, rad * (1 if can else 0.6), h), (0, 0, 0)))
        groups = [(body, shell), (alu, frame + shelves), (lit, [("box", (-D / 2 + 0.045, 0, H / 2), (0.005, W - 0.1, H - 0.4), (0, 0, 0)),
                                                                ("box", (D / 2 - 0.005, 0, H - 0.1), (0.01, W - 0.1, 0.14), (0, 0, 0))]),
                  (glass, [("box", (D / 2 - 0.01, 0, H / 2 - 0.04), (0.008, W - 0.06, H - 0.36), (0, 0, 0))])]
        groups += [(_flat(f"ir_pack_{int(c[0] * 100)}_{int(c[1] * 100)}_{int(c[2] * 100)}", c, 0.3, 0.5), parts) for c, parts in stock.items()]
        o = _prims(f"DisplayCoolerFactory({i}).spawn_asset({i})", groups)
        ld = bpy.data.lights.new(f"ir_cooler_{i}", "AREA"); ld.shape = "RECTANGLE"; ld.size, ld.size_y = 0.6, 1.6; ld.energy = 25.0
        lo = bpy.data.objects.new(f"PointLampFactory(cooler).spawn_asset({i})", ld)
        bpy.context.scene.collection.objects.link(lo); lo.parent = o; lo.location = (D / 2 - 0.15, 0, H / 2); lo.rotation_euler = (0, math.pi / 2, 0)
        return o


class GondolaFactory:
    """Supermarket gondola (front +X): a base deck and 4 shelves per side, a price strip on every shelf edge, a coloured header on
    one end. Double-sided (0.9 m deep, free-standing aisles) or single-sided (0.45 m, against a wall). 1.2-2.4 m long, 1.45-1.6 m."""
    double = True

    def __init__(self, seed):
        r = random.Random(seed)
        self.L = r.choice((1.25, 1.875, 2.5)); self.H = r.uniform(1.45, 1.6); self.header = r.choice(HEADER_COLOURS)

    def spawn_asset(self, i):
        L, H = self.L, self.H
        D = 0.9 if self.double else 0.45
        body = _flat("ir_gondola_white", (0.86, 0.86, 0.85), 0.35, 0.3); strip = _flat("ir_price_strip", (0.92, 0.9, 0.55), 0.4)
        head = _flat(f"ir_header_{HEADER_COLOURS.index(self.header)}", self.header, 0.5)
        sides = (1, -1) if self.double else (1,)
        parts, strips = [], []
        back_x = 0.0 if self.double else -D / 2 + 0.02
        parts.append((back_x, 0, H / 2, 0.04, L, H))                                    # back panel / spine
        parts += [(sx * (D / 2 - 0.02), sy * (L / 2 - 0.02), H / 2, 0.04, 0.04, H) for sx in (1, -1) for sy in (1, -1)]   # corner posts, not
        # solid end panels: 'tall blank white end panels like cubicle partitions' (floor I r12-r13, 3 of 3 each)
        for sx in sides:
            x_mid = sx * D / 4 if self.double else 0.0
            depth = D / 2 - 0.03 if self.double else D - 0.05
            parts.append((x_mid, 0, 0.06, depth, L - 0.04, 0.12))                       # base deck
            for k in range(1, 5):
                z = 0.12 + k * (H - 0.2) / 4.6
                parts.append((x_mid, 0, z, depth, L - 0.04, 0.02))
                strips.append((x_mid + sx * depth / 2, 0, z - 0.01, 0.01, L - 0.06, 0.035))
        # the header carries an aisle word in white block letters on both faces (floor I r9: 'large blank coloured boards on the shelf
        # tops read as cubicle partitions', 3 of 3)
        word = HEADER_WORDS[(i * 7 + int(L * 10)) % len(HEADER_WORDS)]; n = len(word); lw = D * 0.55 / max(n, 4)   # spread over the
        # list, not random: 'DELI five times, COLD four times' (floor I r28, 3 of 3)
        zh = H + 0.55                                            # hung above the gondola on two rods, smaller: at H + 0.14 the boards sat
        glyphs = []                                              # at eye level and 'filled the frame' (floor I r28, 3 of 3)                                              # real words in a stroke font: random strokes read as 'mirrored
        gw, gh, t_ = lw * 0.6, 0.12, 0.014                       # nonsense text' (floor I r27, 3 of 3); solid blocks as 'blank
        for k, ch in enumerate(word):                            # placeholder signs' (I r21-r26)
            xt = -lw * n / 2 + (k + 0.5) * lw
            for sy in (1, -1):                                   # each face reads left to right from its own side: x_world = -sy * x_text
                glyphs += [(-sy * (xt + ux * gw), L / 2 + 0.01 + sy * 0.012, zh + uz * gh * 0.8, max(t_, uw * gw), 0.004, max(t_, uh * gh * 0.8))
                           for ux, uz, uw, uh in _STROKES[ch]]
        ink = _flat("ir_header_ink", (0.95, 0.95, 0.93), 0.5)
        o = _parts_object(f"{type(self).__name__}({i}).spawn_asset({i})",
                          [(body, parts), (strip, strips), (head, [(0, L / 2 + 0.01, zh, D * 0.7, 0.02, 0.2)]), (ink, glyphs),
                           (body, [(sx * D * 0.25, L / 2 + 0.01, (H + zh - 0.1) / 2, 0.012, 0.012, zh - 0.1 - H) for sx in (1, -1)])])
        return o


class WallGondolaFactory(GondolaFactory):
    double = False


class ChestFreezerFactory:
    """Supermarket chest freezer (front +X): white body, dark inner tub under a glass lid, 1.2-2.0 m long, 0.85 m high."""
    def __init__(self, seed):
        self.L = random.Random(seed).uniform(1.2, 2.0)

    def spawn_asset(self, i):
        L = self.L
        white = _flat("ir_appliance_white", (0.88, 0.88, 0.87), 0.3); dark = _flat("ir_freezer_inner", (0.15, 0.2, 0.25), 0.5)
        glass = _flat("ir_dome_glass", (0.95, 0.95, 0.95), 0.02, transmission=1.0)
        return _parts_object(f"ChestFreezerFactory({i}).spawn_asset({i})",
                             [(white, [(0, 0, 0.4, 0.8, L, 0.8)]), (dark, [(0, 0, 0.79, 0.7, L - 0.1, 0.02)]),
                              (glass, [(0, 0, 0.84, 0.76, L - 0.06, 0.012)])])


class RegisterFactory:
    """Point-of-sale register (front +X): a till base, a card reader and a customer-facing screen on a stem."""
    def __init__(self, seed):
        self.seed = seed

    def spawn_asset(self, i):
        black = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0); screen = _flat("ir_pos_screen", (0.02, 0.03, 0.05), 0.15)
        return _parts_object(f"RegisterFactory({i}).spawn_asset({i})",
                             [(black, [(0, 0, 0.05, 0.36, 0.42, 0.1), (0.0, 0, 0.2, 0.04, 0.04, 0.2), (0.15, 0.25, 0.03, 0.08, 0.06, 0.06)]),
                              (screen, [(-0.02, 0, 0.36, 0.03, 0.34, 0.24)])])


class GrinderFactory:
    """Coffee grinder (front +X): a body, a dark bean hopper on top, a spout."""
    def __init__(self, seed):
        self.c = random.Random(seed).choice(((0.03, 0.03, 0.03), (0.62, 0.62, 0.64), (0.85, 0.85, 0.83)))

    def spawn_asset(self, i):
        body = _flat(f"ir_grinder_{int(self.c[0] * 100)}", self.c, 0.3, 0.6); hop = _flat("ir_hopper", (0.12, 0.08, 0.05), 0.15)
        return _parts_object(f"GrinderFactory({i}).spawn_asset({i})",
                             [(body, [(0, 0, 0.17, 0.2, 0.16, 0.34), (0.11, 0, 0.12, 0.05, 0.05, 0.04)]),
                              (hop, [(0, 0, 0.42, 0.14, 0.14, 0.16)])])


class CupStackFactory:
    """A stack of 4-8 white or kraft takeaway cups."""
    def __init__(self, seed):
        r = random.Random(seed); self.n = r.randint(4, 8); self.c = r.choice(((0.92, 0.92, 0.9), (0.62, 0.45, 0.3)))

    def spawn_asset(self, i):
        m = _flat(f"ir_cup_{int(self.c[0] * 100)}", self.c, 0.5)
        return _parts_object(f"CupStackFactory({i}).spawn_asset({i})", [(m, [(0, 0, 0.06 + k * 0.02, 0.085, 0.085, 0.12) for k in range(self.n)])])


class PastryCaseFactory:
    """A glass pastry case on the counter: a base, two shelves of pastries behind glass."""
    def __init__(self, seed):
        self.r = random.Random(seed)

    def spawn_asset(self, i):
        r = self.r
        base = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0); glass = _flat("ir_dome_glass", (0.95, 0.95, 0.95), 0.02, transmission=1.0)
        pastry = _flat(f"ir_pastry_{i % 3}", [(0.7, 0.45, 0.2), (0.85, 0.7, 0.45), (0.45, 0.25, 0.12)][i % 3], 0.7)
        # croissants / buns / tarts as ellipsoids and discs (style eval 2026-10-16: 'placeholder blocks in the glass case')
        items = []
        for z in (0.03, 0.22):
            for k in range(6):
                x, y = r.uniform(-0.1, 0.1), -0.3 + k * 0.12
                kind = r.choice(("croissant", "bun", "tart"))
                if kind == "croissant":
                    items.append(("sph", (x, y, z + 0.025), (0.045, 0.028, 0.022), (0, 0, r.uniform(0, 3))))
                elif kind == "bun":
                    items.append(("sph", (x, y, z + 0.025), (0.035, 0.035, 0.024), (0, 0, 0)))
                else:
                    items.append(("cyl", (x, y, z + 0.012), (0.04, 0.038, 0.024), (0, 0, 0)))
        return _prims(f"PastryCaseFactory({i}).spawn_asset({i})",
                      [(base, [("box", (0, 0, 0.015), (0.42, 0.78, 0.03), (0, 0, 0)), ("box", (0, 0, 0.21), (0.4, 0.76, 0.01), (0, 0, 0))]),
                       (pastry, items),
                       (glass, [("box", (0.2, 0, 0.21), (0.01, 0.78, 0.4), (0, 0, 0)), ("box", (-0.2, 0, 0.21), (0.01, 0.78, 0.4), (0, 0, 0)),
                                ("box", (0, 0.39, 0.21), (0.42, 0.01, 0.4), (0, 0, 0)), ("box", (0, -0.39, 0.21), (0.42, 0.01, 0.4), (0, 0, 0)),
                                ("box", (0, 0, 0.41), (0.42, 0.78, 0.01), (0, 0, 0))])])


class SyrupRackFactory:
    """A row of 4-6 syrup bottles with pumps on a small tray."""
    def __init__(self, seed):
        self.n = random.Random(seed).randint(4, 6)

    def spawn_asset(self, i):
        tray = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0)
        cols = [_flat(f"ir_syrup_{k}", c, 0.15) for k, c in enumerate(((0.45, 0.2, 0.05), (0.6, 0.1, 0.1), (0.2, 0.35, 0.1), (0.5, 0.4, 0.1)))]
        groups = [(tray, [(0, 0, 0.01, 0.1, 0.09 * self.n, 0.02)])]
        for k in range(self.n):
            groups.append((cols[k % 4], [(0, -0.045 * (self.n - 1) + k * 0.09, 0.15, 0.07, 0.07, 0.26)]))
        groups.append((tray, [(0, -0.045 * (self.n - 1) + k * 0.09, 0.31, 0.015, 0.015, 0.06) for k in range(self.n)]))
        return _parts_object(f"SyrupRackFactory({i}).spawn_asset({i})", groups)


# ---- office -------------------------------------------------------------------------------------------------------------------------
DIVIDER = [(0.42, 0.45, 0.47), (0.28, 0.36, 0.3), (0.55, 0.52, 0.46), (0.2, 0.25, 0.32)]


class WorkstationPodFactory:
    """Bench workstation (front +X = the +x row): 2x2 or 2x3 desks back to back, a fabric divider screen down the spine, a pedestal
    and a monitor (stand + screen) on every desk. obj['seats'] lists (x, y, yaw) seat spots in local frame for the chairs."""
    def __init__(self, seed, n=None):
        r = random.Random(seed)
        self.n = n or r.choice((2, 3, 3, 4)); self.w = r.uniform(1.2, 1.4); self.d = 0.7; self.div = r.choice(DIVIDER)   # 4/6/6/8 desks
        self.dual = r.random() < 0.4
        self.top = r.choice(((0.88, 0.87, 0.84), (0.55, 0.42, 0.3), (0.3, 0.3, 0.3)))

    def spawn_asset(self, i):
        n, w, d = self.n, self.w, self.d
        top = _flat(f"ir_desk_top_{int(self.top[0] * 100)}", self.top, 0.5); metal = _flat("ir_desk_frame", (0.75, 0.75, 0.76), 0.35, 0.8)
        div = _flat(f"ir_divider_{DIVIDER.index(self.div)}", self.div, 0.9); ped = _flat("ir_pedestal", (0.5, 0.5, 0.52), 0.4, 0.3)
        black = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0); screen = _flat("ir_pos_screen", (0.02, 0.03, 0.05), 0.15)
        tops, legs, peds, mons, scr, seats = [], [], [], [], [], []
        L = n * w
        for side in (1, -1):
            for k in range(n):
                y = -L / 2 + (k + 0.5) * w
                x = side * (d / 2 + 0.01)
                tops.append((x, y, 0.735, d, w - 0.01, 0.03))
                peds.append((x - side * 0.05, y + w / 2 - 0.25, 0.3, 0.55, 0.4, 0.58))
                # monitor arm clamped at the spine, one or two screens
                mons += [(side * 0.06, y, 0.95, 0.03, 0.03, 0.4), (side * 0.12, y, 1.1, 0.14, 0.025, 0.025)]
                for dy in ((-0.31, 0.31) if self.dual else (0.0,)):
                    scr.append((side * 0.19, y + dy, 1.1, 0.02, 0.58, 0.34))
                seats.append((side * (d + 0.45), y, math.atan2(0, -side)))
        for sx in (1, -1):                                       # end frames and a centre leg per pair
            for yy in (-L / 2 + 0.03, L / 2 - 0.03):
                legs.append((sx * (d / 2 + 0.01), yy, 0.36, d - 0.05, 0.04, 0.72))
        tray = [(0, 0, 0.6, 0.18, L - 0.1, 0.05)]                          # cable tray under the spine
        o = _parts_object(f"WorkstationPodFactory({i}).spawn_asset({i})",
                          [(top, tops), (metal, legs + tray), (div, [(0, 0, 0.98, 0.04, L, 0.46)]), (ped, peds), (black, mons), (screen, scr)])
        o["seats"] = [list(s) for s in seats]
        return o


class WallDisplayFactory:
    """Meeting-room display on the wall (front +X): a 65-75" panel and a camera bar under it. Origin at the bottom; mount at ~0.9 m."""
    def __init__(self, seed):
        self.W = random.Random(seed).choice((1.45, 1.66))

    def spawn_asset(self, i):
        black = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0); screen = _flat("ir_pos_screen", (0.02, 0.03, 0.05), 0.15)
        W, H = self.W, self.W * 9 / 16
        return _parts_object(f"WallDisplayFactory({i}).spawn_asset({i})",
                             [(black, [(0, 0, 0.12 + H / 2, 0.05, W + 0.02, H + 0.02), (0.02, 0, 0.04, 0.05, 0.6, 0.06)]),
                              (screen, [(0.026, 0, 0.12 + H / 2, 0.005, W - 0.02, H - 0.02)])])


class WhiteboardFactory:
    """Wall whiteboard (front +X): white panel in an aluminium frame with a marker tray. Origin at the bottom; mount at ~0.9 m."""
    def __init__(self, seed):
        self.W = random.Random(seed).choice((1.2, 1.5, 1.8))

    def spawn_asset(self, i):
        white = _flat("ir_whiteboard", (0.93, 0.93, 0.92), 0.08); alu = _flat("ir_alu", (0.7, 0.7, 0.72), 0.3, 1.0)
        W, H = self.W, 1.0
        return _parts_object(f"WhiteboardFactory({i}).spawn_asset({i})",
                             [(white, [(0, 0, H / 2, 0.02, W, H)]),
                              (alu, [(0.005, 0, H, 0.03, W + 0.03, 0.025), (0.005, 0, 0.0, 0.03, W + 0.03, 0.025),
                                     (0.005, W / 2, H / 2, 0.03, 0.025, H), (0.005, -W / 2, H / 2, 0.03, 0.025, H),
                                     (0.04, 0, 0.0, 0.06, W * 0.6, 0.02)])])


class SpeakerphoneFactory:
    def __init__(self, seed):
        self.seed = seed

    def spawn_asset(self, i):
        import bmesh
        m = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0)
        bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.12, radius2=0.1, depth=0.035)
        bmesh.ops.translate(bm, vec=(0, 0, 0.0175), verts=bm.verts)
        me = bpy.data.meshes.new(f"spk{i}"); bm.to_mesh(me); bm.free(); me.materials.append(m)
        o = bpy.data.objects.new(f"SpeakerphoneFactory({i}).spawn_asset({i})", me); bpy.context.scene.collection.objects.link(o)
        return o


class PaperStackFactory:
    """A4 paper / a document folder (critic r1: BookStackFactory on a meeting table reads as a home's books)."""
    def __init__(self, seed):
        r = random.Random(seed)
        self.h = r.uniform(0.004, 0.025); self.folder = r.random() < 0.4
        self.col = r.choice(((0.1, 0.18, 0.4), (0.05, 0.05, 0.05), (0.55, 0.08, 0.06)))

    def spawn_asset(self, i):
        paper = _flat("ir_paper", (0.86, 0.86, 0.84), 0.7)
        groups = [(paper, [(0, 0, self.h / 2, 0.297, 0.21, self.h)])]
        if self.folder:
            groups.append((_flat(f"ir_folder_{int(self.col[0] * 100)}", self.col, 0.5), [(0, 0, self.h + 0.0015, 0.31, 0.225, 0.003)]))
        return _parts_object(f"PaperStackFactory({i}).spawn_asset({i})", groups)


def _prims(name, groups):
    """Like _parts_object, with tilted boxes and cylinders: parts are ("box", (cx, cy, cz), (sx, sy, sz), (rx, ry, rz)) or
    ("cyl", (cx, cy, cz), (r_bottom, r_top, h), (rx, ry, rz)); rotations in radians about the part's centre. "rbox" is a box with
    rounded edges (upholstery: dental r20, the slab chair read as 'scattered planks')."""
    import bmesh
    from mathutils import Euler
    bm = bmesh.new()
    for slot, (mat, parts) in enumerate(groups):
        for kind, c, size, rot in parts:
            if kind == "rbox":                                   # bevelled in its own bmesh, then appended
                tb = bmesh.new(); bmesh.ops.create_cube(tb, size=1.0); bmesh.ops.scale(tb, vec=size, verts=tb.verts)
                bmesh.ops.bevel(tb, geom=list(tb.edges) + list(tb.verts), offset=min(size) * 0.4, segments=3, profile=0.5, affect="EDGES")
                bmesh.ops.rotate(tb, cent=(0, 0, 0), matrix=Euler(rot).to_matrix(), verts=tb.verts)
                bmesh.ops.translate(tb, vec=c, verts=tb.verts)
                for f in tb.faces:
                    f.material_index = slot; f.smooth = True
                tm = bpy.data.meshes.new("_rbox"); tb.to_mesh(tm); tb.free(); bm.from_mesh(tm); bpy.data.meshes.remove(tm)
                continue
            if kind == "box":
                r = bmesh.ops.create_cube(bm, size=1.0)
                bmesh.ops.scale(bm, vec=size, verts=r["verts"])
            elif kind == "sph":                                  # ellipsoid with semi-axes `size`
                r = bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)   # 2 left the gym ball faceted (clinic r24)
                bmesh.ops.scale(bm, vec=size, verts=r["verts"])
            else:
                r = bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=size[0], radius2=size[1], depth=size[2])
            bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Euler(rot).to_matrix(), verts=r["verts"])
            bmesh.ops.translate(bm, vec=c, verts=r["verts"])
            for f in {f for v in r["verts"] for f in v.link_faces}:
                f.material_index = slot; f.smooth = kind == "sph"     # a smooth ball (clinic r24: 'faceted, placeholder')
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for mat, _ in groups:
        me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    _bevel(o)
    return o


# ---- desk clutter (user 2026-10-16: 'the office is too clean, nobody's hands on it -- leftover snacks, books, pencils, cups') ------
_BRIGHT = ((0.75, 0.12, 0.1), (0.95, 0.65, 0.1), (0.1, 0.35, 0.7), (0.15, 0.55, 0.25), (0.85, 0.85, 0.82), (0.55, 0.15, 0.5))


class GloveBoxFactory:
    """A box of exam gloves (clinic r6 critic: 'no glove boxes, sanitizer or trays'): a coloured carton with a white tuft at its slot."""
    def __init__(self, seed):
        self.r = random.Random(seed)

    def spawn_asset(self, i):
        c = self.r.choice(((0.3, 0.35, 0.75), (0.55, 0.3, 0.65), (0.85, 0.85, 0.88), (0.2, 0.55, 0.6)))
        box = _flat(f"ir_glovebox_{int(c[0] * 100)}", c, 0.6); tuft = _flat("ir_glove_white", (0.92, 0.92, 0.95), 0.5)
        return _prims(f"GloveBoxFactory({i}).spawn_asset({i})", [(box, [("box", (0, 0, 0.035), (0.12, 0.24, 0.07), (0, 0, 0))]),
                                                                 (tuft, [("sph", (0, 0, 0.075), (0.03, 0.05, 0.015), (0, 0, 0))])])


class SanitizerFactory:
    """A pump bottle of hand sanitizer / soap: a clear or white bottle, a pump head with a nozzle."""
    def __init__(self, seed):
        self.r = random.Random(seed)

    def spawn_asset(self, i):
        c = self.r.choice(((0.85, 0.92, 0.95), (0.95, 0.95, 0.95), (0.6, 0.8, 0.9)))
        body = _flat(f"ir_sanitizer_{int(c[0] * 100)}", c, 0.15, transmission=0.4 if c[0] < 0.9 else 0.0)
        pump = _flat("ir_pump_white", (0.92, 0.92, 0.9), 0.4)
        return _prims(f"SanitizerFactory({i}).spawn_asset({i})",
                      [(body, [("cyl", (0, 0, 0.08), (0.035, 0.03, 0.16), (0, 0, 0))]),
                       (pump, [("cyl", (0, 0, 0.18), (0.012, 0.012, 0.05), (0, 0, 0)), ("box", (0.02, 0, 0.2), (0.05, 0.012, 0.012), (0, 0, 0))])])


class PaperTowelFactory:
    """A paper towel roll on an upright holder."""
    def __init__(self, seed):
        self.r = random.Random(seed)

    def spawn_asset(self, i):
        paper = _flat("ir_paper_towel", (0.94, 0.94, 0.92), 0.8); steel = _flat("ir_chrome", (0.8, 0.8, 0.82), 0.15, 1.0)
        return _prims(f"PaperTowelFactory({i}).spawn_asset({i})",
                      [(steel, [("cyl", (0, 0, 0.005), (0.08, 0.08, 0.01), (0, 0, 0)), ("cyl", (0, 0, 0.14), (0.008, 0.008, 0.28), (0, 0, 0))]),
                       (paper, [("cyl", (0, 0, 0.125), (0.06, 0.06, 0.22), (0, 0, 0))])])


class ClipboardFactory:
    """A clipboard with a form, lying flat: a hardboard back, a sheet, a metal clip."""
    def __init__(self, seed):
        self.r = random.Random(seed)

    def spawn_asset(self, i):
        board = _flat("ir_clipboard", (0.45, 0.32, 0.2), 0.6); sheet = _flat("ir_paper", (0.93, 0.93, 0.9), 0.7)
        clip = _flat("ir_chrome", (0.8, 0.8, 0.82), 0.15, 1.0)
        return _prims(f"ClipboardFactory({i}).spawn_asset({i})",
                      [(board, [("box", (0, 0, 0.003), (0.23, 0.32, 0.006), (0, 0, 0))]),
                       (sheet, [("box", (0, -0.01, 0.0065), (0.21, 0.28, 0.001), (0, 0, 0))]),
                       (clip, [("box", (0, 0.145, 0.012), (0.08, 0.03, 0.012), (0, 0, 0))])])


class KidneyTrayFactory:
    """A stainless kidney dish with an instrument or two in it."""
    def __init__(self, seed):
        self.r = random.Random(seed)

    def spawn_asset(self, i):
        steel = _flat("ir_chrome", (0.8, 0.8, 0.82), 0.15, 1.0)
        return _prims(f"KidneyTrayFactory({i}).spawn_asset({i})",
                      [(steel, [("sph", (0, 0, 0.02), (0.07, 0.13, 0.02), (0, 0, 0)), ("box", (0.01, 0.02, 0.03), (0.008, 0.14, 0.004), (0, 0, 0.3))])])


class PenCupFactory:
    """A pen pot (mesh metal or ceramic) with 3-7 pencils/pens leaning in it."""
    def __init__(self, seed):
        self.r = random.Random(seed)

    def spawn_asset(self, i):
        r = self.r
        pot = _flat(f"ir_pencup_{r.randrange(3)}", r.choice(((0.15, 0.15, 0.16), (0.85, 0.84, 0.8), (0.6, 0.6, 0.62))), 0.4, 0.6)
        h = r.uniform(0.09, 0.11)
        sticks = []
        for k in range(r.randint(3, 7)):
            a = r.uniform(0, 2 * math.pi); t = r.uniform(0.08, 0.3); L = r.uniform(0.14, 0.18)
            sticks.append(("box", (0.015 * math.cos(a), 0.015 * math.sin(a), h * 0.4 + L / 2 * math.cos(t)), (0.007, 0.007, L),
                           (t * math.sin(a), -t * math.cos(a), 0)))
        col = _flat(f"ir_pencil_{r.randrange(len(_BRIGHT))}", r.choice(_BRIGHT), 0.5)
        return _prims(f"PenCupFactory({i}).spawn_asset({i})", [(pot, [("cyl", (0, 0, h / 2), (0.037, 0.04, h), (0, 0, 0))]), (col, sticks)])


class TakeawayCupFactory:
    """A paper coffee cup with a lid and a sleeve."""
    def __init__(self, seed):
        self.r = random.Random(seed)

    def spawn_asset(self, i):
        r = self.r
        paper = _flat("ir_cup_paper", r.choice(((0.92, 0.91, 0.88), (0.55, 0.38, 0.22))), 0.6)
        lid = _flat("ir_cup_lid", r.choice(((0.05, 0.05, 0.05), (0.92, 0.92, 0.92))), 0.4)
        sleeve = _flat("ir_cup_sleeve", (0.45, 0.3, 0.18), 0.8)
        return _prims(f"TakeawayCupFactory({i}).spawn_asset({i})",
                      [(paper, [("cyl", (0, 0, 0.065), (0.028, 0.042, 0.13), (0, 0, 0))]), (lid, [("cyl", (0, 0, 0.137), (0.044, 0.04, 0.014), (0, 0, 0))]),
                       (sleeve, [("cyl", (0, 0, 0.07), (0.037, 0.04, 0.05), (0, 0, 0))])])


class SnackFactory:
    """A snack: a chip/candy bag (half the time torn open, flattened), a biscuit box, or a few loose biscuits on a wrapper."""
    def __init__(self, seed):
        self.r = random.Random(seed)

    def spawn_asset(self, i):
        r = self.r
        col = _flat(f"ir_snack_{r.randrange(len(_BRIGHT))}", r.choice(_BRIGHT), 0.3, 0.4)
        kind = r.choice(("bag", "bag", "box", "loose"))
        if kind == "bag":
            opened = r.random() < 0.5
            parts = [("box", (0, 0, 0.02 if opened else 0.035), (0.16, 0.22, 0.04 if opened else 0.07), (0, 0, 0))]
            if opened:                                          # crumbs / chips spilled beside the torn bag
                crumb = _flat("ir_crumb", (0.85, 0.65, 0.3), 0.7)
                bits = [("box", (r.uniform(-0.1, 0.1), r.uniform(0.12, 0.18), 0.004), (0.03, 0.025, 0.006), (0, 0, r.uniform(0, 3))) for _ in range(r.randint(2, 5))]
                return _prims(f"SnackFactory({i}).spawn_asset({i})", [(col, parts), (crumb, bits)])
            return _prims(f"SnackFactory({i}).spawn_asset({i})", [(col, parts)])
        if kind == "box":
            return _prims(f"SnackFactory({i}).spawn_asset({i})", [(col, [("box", (0, 0, 0.025), (0.2, 0.08, 0.05), (0, 0, 0))])])
        wrap = _flat("ir_wrapper", (0.85, 0.85, 0.85), 0.3, 0.7); bisc = _flat("ir_biscuit", (0.72, 0.5, 0.25), 0.8)
        return _prims(f"SnackFactory({i}).spawn_asset({i})", [(wrap, [("box", (0, 0, 0.001), (0.18, 0.12, 0.002), (0, 0, 0.2))]),
                      (bisc, [("cyl", (r.uniform(-0.05, 0.05), r.uniform(-0.03, 0.03), 0.006 + 0.008 * k), (0.025, 0.025, 0.007), (0, 0, 0)) for k in range(r.randint(1, 3))])])


class PhoneFactory:
    """A smartphone lying face up (screen dark or lit)."""
    def __init__(self, seed):
        self.r = random.Random(seed)

    def spawn_asset(self, i):
        body = _flat("ir_phone_body", self.r.choice(((0.05, 0.05, 0.06), (0.8, 0.8, 0.82), (0.2, 0.3, 0.45))), 0.3, 0.6)
        scr = _flat("ir_pos_screen", (0.02, 0.03, 0.05), 0.15)
        return _prims(f"PhoneFactory({i}).spawn_asset({i})", [(body, [("box", (0, 0, 0.004), (0.072, 0.15, 0.008), (0, 0, 0))]),
                                                              (scr, [("box", (0, 0, 0.0085), (0.066, 0.142, 0.001), (0, 0, 0))])])


class NotebookFactory:
    """A notebook or A4 pad, closed or open, sometimes with sticky notes and a pen on it."""
    def __init__(self, seed):
        self.r = random.Random(seed)

    def spawn_asset(self, i):
        r = self.r
        cover = _flat(f"ir_notebook_{r.randrange(len(_BRIGHT))}", r.choice(_BRIGHT), 0.6)
        paper = _flat("ir_paper", (0.86, 0.86, 0.84), 0.7)
        w, h, t = r.choice(((0.15, 0.21, 0.012), (0.21, 0.297, 0.01)))
        groups = []
        if r.random() < 0.4:                                    # open: two pages side by side
            groups = [(cover, [("box", (0, 0, 0.002), (2 * w + 0.01, h + 0.01, 0.003), (0, 0, 0))]),
                      (paper, [("box", (-w / 2, 0, 0.006), (w, h, 0.006), (0, 0, 0)), ("box", (w / 2, 0, 0.006), (w, h, 0.006), (0, 0, 0))])]
        else:
            groups = [(paper, [("box", (0, 0, t / 2), (w - 0.004, h - 0.004, t), (0, 0, 0))]), (cover, [("box", (0, 0, t + 0.001), (w, h, 0.002), (0, 0, 0))])]
        if r.random() < 0.5:
            note = _flat("ir_sticky", r.choice(((0.98, 0.9, 0.3), (0.98, 0.6, 0.7), (0.6, 0.9, 0.6))), 0.7)
            groups.append((note, [("box", (r.uniform(-0.04, 0.04), r.uniform(-0.06, 0.06), t + 0.004), (0.076, 0.076, 0.002), (0, 0, r.uniform(-0.4, 0.4)))]))
        if r.random() < 0.5:
            pen = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0)
            groups.append((pen, [("box", (0.02, 0, t + 0.008), (0.009, 0.14, 0.009), (0, 0, r.uniform(-0.6, 0.6)))]))
        return _prims(f"NotebookFactory({i}).spawn_asset({i})", groups)


class OfficeDeskFactory:
    """A private-office desk (front +X = the user's side): 1.4-1.8 x 0.75-0.85 m top on panel legs with a modesty panel, a drawer
    pedestal, a monitor on a stand and a keyboard (critic r3: an ABO 'desk' read as a low cabinet with a monitor on it)."""
    def __init__(self, seed):
        r = random.Random(seed)
        self.L = r.choice((1.4, 1.6, 1.8)); self.D = r.uniform(0.75, 0.85)
        self.top = r.choice(((0.88, 0.87, 0.84), (0.45, 0.32, 0.2), (0.62, 0.5, 0.36), (0.2, 0.2, 0.2)))
        self.dual = r.random() < 0.35

    def spawn_asset(self, i):
        L, D = self.L, self.D
        top = _flat(f"ir_desk_top_{int(self.top[0] * 100)}", self.top, 0.45); panel = _flat("ir_desk_panel", (0.3, 0.3, 0.31), 0.5, 0.2)
        ped = _flat("ir_pedestal", (0.5, 0.5, 0.52), 0.4, 0.3); black = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0)
        screen = _flat("ir_pos_screen", (0.02, 0.03, 0.05), 0.15)
        mons = [(-D / 2 + 0.15, 0, 0.82, 0.18, 0.22, 0.012), (-D / 2 + 0.17, 0, 0.92, 0.03, 0.05, 0.2)]
        scr = [(-D / 2 + 0.19, dy, 1.08, 0.02, 0.56, 0.33) for dy in ((-0.29, 0.29) if self.dual else (0.0,))]
        return _parts_object(f"OfficeDeskFactory({i}).spawn_asset({i})",
                             [(top, [(0, 0, 0.735, D, L, 0.03)]),
                              (panel, [(0, sy * (L / 2 - 0.02), 0.36, D - 0.04, 0.03, 0.72) for sy in (1, -1)] + [(-D / 2 + 0.06, 0, 0.45, 0.02, L - 0.08, 0.45)]),
                              (ped, [(0.0, L / 2 - 0.27, 0.32, 0.55, 0.42, 0.6)]),
                              (black, mons + [(0.08, 0, 0.755, 0.15, 0.44, 0.015)]), (screen, scr)])


class FilingCabinetFactory:
    """Steel office filing cabinet (front +X): a 2-4 drawer lateral or vertical filer with recessed pulls (critic r3-r5: ABO 'filing'
    pools kept returning wooden dressers and nightstands)."""
    def __init__(self, seed):
        r = random.Random(seed)
        self.lateral = r.random() < 0.5; self.n = r.choice((2, 3, 4)) if self.lateral else r.choice((3, 4))
        self.c = r.choice(((0.82, 0.82, 0.8), (0.55, 0.56, 0.57), (0.18, 0.18, 0.19)))

    def spawn_asset(self, i):
        W, D = (0.9, 0.5) if self.lateral else (0.47, 0.62)
        H = 0.36 * self.n + 0.05
        body = _flat(f"ir_filer_{int(self.c[0] * 100)}", self.c, 0.35, 0.6); pull = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0)
        gaps = [(D / 2 + 0.001, 0, 0.05 + k * 0.36, 0.002, W - 0.02, 0.006) for k in range(1, self.n)]
        pulls = [(D / 2 + 0.008, 0, 0.05 + (k + 0.75) * 0.36, 0.012, W * 0.45, 0.025) for k in range(self.n)]
        return _parts_object(f"FilingCabinetFactory({i}).spawn_asset({i})", [(body, [(0, 0, H / 2, D, W, H)]), (pull, gaps + pulls)])


# ---- clinics and shops (non-home 20, 2026-10-16) -----------------------------------------------------------------------------------
class ReceptionDeskFactory:
    """Reception / pharmacy desk (front +X = the visitor side): a work surface at 0.75 m behind a 1.1 m transaction ledge, a modesty
    front, a monitor on the staff side. 2.0-3.2 m long."""
    def __init__(self, seed):
        r = random.Random(seed)
        self.L = r.choice((2.0, 2.4, 2.8, 3.2)); self.front = r.choice(((0.9, 0.9, 0.88), (0.35, 0.45, 0.55)) if VENUE == "clinic-reception"
                                                                      else ((0.9, 0.9, 0.88), (0.62, 0.5, 0.36), (0.35, 0.45, 0.55)))   # no wood in a clinic (r23)

    def spawn_asset(self, i):
        L = self.L
        front = _flat(f"ir_reception_front_{int(self.front[2] * 100)}", self.front, 0.5); top = _flat("ir_counter_top_white_stone", (0.86, 0.85, 0.82), 0.25)
        work = _flat("ir_desk_top_88", (0.88, 0.87, 0.84), 0.45); black = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0)
        screen = _flat("ir_pos_screen", (0.02, 0.03, 0.05), 0.15)
        return _parts_object(f"ReceptionDeskFactory({i}).spawn_asset({i})",
                             [(front, [(0.33, 0, 0.55, 0.04, L, 1.1)] + [(0.0, sy * (L / 2 - 0.02), 0.37, 0.66, 0.04, 0.74) for sy in (1, -1)]),
                              (top, [(0.3, 0, 1.115, 0.3, L + 0.04, 0.03)]), (work, [(-0.05, 0, 0.745, 0.7, L - 0.04, 0.03)]),
                              (black, [(-0.2, -L / 4, 0.82, 0.2, 0.22, 0.012), (-0.2, -L / 4, 0.92, 0.03, 0.05, 0.2)]),
                              (screen, [(-0.18, -L / 4, 1.07, 0.02, 0.54, 0.32)])])


class WaitingBenchFactory:
    """Beam seating (front +X): 3-5 moulded seats on a steel beam with two legs -- waiting rooms line these up along walls."""
    def __init__(self, seed):
        r = random.Random(seed)
        self.n = r.choice((3, 4, 4, 5))   # one seat colour per room (clinic r27: 'teal and charcoal rows mixed', 2 of 3); no salmon (r16)
        self.c = _ROOM_PICK.setdefault("waiting_bench", r.choice(((0.15, 0.35, 0.55), (0.12, 0.12, 0.13), (0.2, 0.4, 0.42), (0.55, 0.25, 0.15))))   # no light grey: 'white benches, white desk, white walls' (floor D3 r11)

    def spawn_asset(self, i):
        n, w = self.n, 0.56
        L = n * w
        seat = _flat(f"ir_bench_seat_{int(self.c[2] * 100)}", self.c, 0.45); steel = _flat("ir_desk_frame", (0.75, 0.75, 0.76), 0.35, 0.8)
        seats = [(0.0, -L / 2 + (k + 0.5) * w, 0.45, 0.46, w - 0.06, 0.05) for k in range(n)]
        backs = [(-0.22, -L / 2 + (k + 0.5) * w, 0.68, 0.04, w - 0.08, 0.4) for k in range(n)]
        frame = [(-0.05, 0, 0.4, 0.06, L, 0.05)] + [(-0.05, sy * (L / 2 - 0.15), 0.2, 0.05, 0.05, 0.4) for sy in (1, -1)]
        frame += [(-0.05, sy * (L / 2 - 0.15), 0.01, 0.5, 0.06, 0.02) for sy in (1, -1)]
        return _parts_object(f"WaitingBenchFactory({i}).spawn_asset({i})", [(seat, seats + backs), (steel, frame)])


class WaterCoolerFactory:
    """A waiting-room water cooler (front +X): white cabinet, a blue bottle on top, two taps, a cup dispenser."""
    def __init__(self, seed):
        self.seed = seed

    def spawn_asset(self, i):
        body = _flat("ir_ac_white", (0.86, 0.86, 0.85), 0.4); bottle = _flat("ir_cooler_bottle", (0.35, 0.6, 0.85), 0.05, transmission=0.8)
        blk = _flat("ir_black_plastic", (0.04, 0.04, 0.045), 0.5)
        return _prims(f"WaterCoolerFactory({i}).spawn_asset({i})", [
            (body, [("box", (0, 0, 0.5), (0.32, 0.32, 1.0), (0, 0, 0)), ("cyl", (0.06, 0.2, 0.9), (0.035, 0.035, 0.25), (0, 0, 0))]),
            (bottle, [("cyl", (0, 0, 1.2), (0.13, 0.13, 0.38), (0, 0, 0))]),
            (blk, [("box", (0.17, sy * 0.05, 0.82), (0.03, 0.025, 0.03), (0, 0, 0)) for sy in (1, -1)])])


class OperatorStoolFactory:
    """Dentist's operator stool (front +X): a round upholstered saddle seat on a gas column and five-star base, a small back rest
    (dental r10: 'a black high-back office task chair for the clinician', 3 of 3)."""
    def __init__(self, seed):
        self.c = random.Random(seed).choice(((0.05, 0.25, 0.5), (0.03, 0.35, 0.38), (0.15, 0.15, 0.17)))

    def spawn_asset(self, i):
        fab = _flat(f"ir_stool_{int(self.c[1] * 100)}", self.c, 0.5); blk = _flat("ir_black_plastic", (0.04, 0.04, 0.045), 0.5)
        steel = _flat("ir_chrome", (0.8, 0.8, 0.82), 0.15, 1.0)
        spokes = [("box", (0.14 * math.cos(a), 0.14 * math.sin(a), 0.06), (0.28, 0.035, 0.03), (0, 0, a)) for a in [k * 2 * math.pi / 5 for k in range(5)]]
        return _prims(f"OperatorStoolFactory({i}).spawn_asset({i})", [(blk, spokes), (steel, [("cyl", (0, 0, 0.3), (0.025, 0.025, 0.46), (0, 0, 0)),
                      ("cyl", (-0.2, 0, 0.72), (0.012, 0.012, 0.22), (0, 0, 0))]),
                      (fab, [("cyl", (0, 0, 0.56), (0.22, 0.2, 0.08), (0, 0, 0)), ("rbox", (-0.22, 0, 0.84), (0.05, 0.3, 0.12), (0, 0, 0))])])


class ClinicLowTableFactory:
    """Waiting-room low table (front +X): white laminate top on a chrome frame (floor D3/F3 r8: 'a residential wooden coffee table')."""
    def __init__(self, seed):
        self.L = random.Random(seed).choice((1.0, 1.2))

    def spawn_asset(self, i):
        L, W, H = self.L, 0.55, 0.42
        top = _flat("ir_laminate_white", (0.88, 0.88, 0.86), 0.35); steel = _flat("ir_desk_frame", (0.75, 0.75, 0.76), 0.35, 0.8)
        legs = [("box", (sx * (W / 2 - 0.04), sy * (L / 2 - 0.04), H / 2 - 0.015), (0.03, 0.03, H - 0.03), (0, 0, 0)) for sx in (1, -1) for sy in (1, -1)]
        # magazines fanned on the top and a leaflet pile on the shelf: a book_stack read as 'a tall pile of hardbacks, residential'
        # (floor F3 r13, 3 of 3)
        r = random.Random(int(L * 1000) + i)
        mags = [(_flat(f"ir_magazine_{k}", c, 0.45), [("box", (r.uniform(-0.08, 0.08), y, H + 0.004 + 0.004 * k), (0.21, 0.28, 0.004), (0, 0, r.uniform(-0.5, 0.5)))])
                for k, (y, c) in enumerate(zip((-L / 4, -L / 4 + 0.12, L / 4, L / 4 + 0.1),
                                               ((0.75, 0.2, 0.2), (0.15, 0.4, 0.7), (0.9, 0.75, 0.2), (0.2, 0.55, 0.35))))]
        return _prims(f"ClinicLowTableFactory({i}).spawn_asset({i})", [(top, [("box", (0, 0, H - 0.015), (W, L, 0.03), (0, 0, 0))]),
                                                                      (steel, legs + [("box", (0, 0, 0.12), (W - 0.1, L - 0.1, 0.015), (0, 0, 0))]),
                                                                      (_flat("ir_leaflets", (0.92, 0.92, 0.9), 0.6), [("box", (0, 0.1, 0.15), (0.21, 0.3, 0.04), (0, 0, 0))])]
                      + mags)


class PrepTableFactory:
    """Café back-kitchen prep station (front +X): a stainless table with an upstand, a sink bowl and tap at one end, an undershelf of
    containers, a cutting board, gastronorm pans and a plate stack on top (floor H r19: 'an office tea point, no prep or wash-up', 3 of 3)."""
    def __init__(self, seed):
        self.L = random.Random(seed).choice((1.5, 1.8))

    def spawn_asset(self, i):
        L, W, H = self.L, 0.7, 0.9
        st = _flat("ir_stainless", (0.72, 0.73, 0.74), 0.3, 0.9); dark = _flat("ir_sink_gap", (0.08, 0.08, 0.09), 0.5)
        board = _flat("ir_cutting_board", (0.92, 0.9, 0.84), 0.6); tub = _flat("ir_food_tub", (0.94, 0.94, 0.92), 0.4)
        lid = _flat("ir_tub_lid", (0.2, 0.45, 0.75), 0.5); plate = _flat("ir_plate_white", (0.95, 0.95, 0.94), 0.25)
        sy = -L / 2 + 0.3                                        # sink end
        legs = [("box", (sx * (W / 2 - 0.04), sy_ * (L / 2 - 0.04), H / 2), (0.04, 0.04, H), (0, 0, 0)) for sx in (1, -1) for sy_ in (1, -1)]
        return _prims(f"PrepTableFactory({i}).spawn_asset({i})", [
            (st, legs + [("box", (0, 0, H - 0.02), (W, L, 0.04), (0, 0, 0)), ("box", (-W / 2 + 0.01, 0, H + 0.1), (0.02, L, 0.2), (0, 0, 0)),
                         ("box", (0, 0, 0.2), (W - 0.06, L - 0.06, 0.02), (0, 0, 0)),
                         ("box", (0, sy, H - 0.16), (0.46, 0.46, 0.3), (0, 0, 0)),                                    # bowl
                         ("box", (-W / 2 + 0.08, sy, H + 0.2), (0.04, 0.04, 0.4), (0, 0, 0)),                         # tap riser
                         ("box", (-W / 2 + 0.2, sy, H + 0.4), (0.26, 0.035, 0.035), (0, 0, 0)),                       # spout
                         ("box", (0.02, 0.35, H + 0.05), (0.32, 0.26, 0.1), (0, 0, 0)),                                # gastronorm pans
                         ("box", (0.02, 0.08, H + 0.05), (0.32, 0.26, 0.1), (0, 0, 0))]),
            (dark, [("box", (0, sy, H + 0.001), (0.4, 0.4, 0.004), (0, 0, 0)), ("box", (0.02, 0.35, H + 0.101), (0.28, 0.22, 0.002), (0, 0, 0))]),
            (board, [("box", (0.05, L / 2 - 0.3, H + 0.015), (0.35, 0.45, 0.025), (0, 0, 0.1))]),
            (plate, [("cyl", (-0.1, L / 2 - 0.12, H + 0.06), (0.24, 0.24, 0.12), (0, 0, 0))]),
            (tub, [("box", (0.0, y, 0.21 + 0.13), (0.4, 0.3, 0.26), (0, 0, 0)) for y in (-L / 4, L / 4)]),
            (lid, [("box", (0.0, y, 0.21 + 0.27), (0.42, 0.32, 0.02), (0, 0, 0)) for y in (-L / 4, L / 4)])])


class PalletRackFactory:
    """Heavy pallet racking, one 2.7 m bay (front +X): blue frames, orange beams at three levels, a pallet of cartons on every level
    (floor J r13-r15: 'only 2 m boltless shelving under a 5 m roof -- a big stockroom, not a warehouse', 3 of 3)."""
    def __init__(self, seed, H=4.0):                           # three levels, top load ~4.1 m: the hall walls are 4.8-5.4 m
        self.r = random.Random(seed); self.H = H

    def spawn_asset(self, i):
        r, H, L, D = self.r, self.H, 2.7, 1.1
        blue = _flat("ir_rack_blue", (0.05, 0.16, 0.42), 0.45, 0.6); orange = _flat("ir_rack_orange", (0.85, 0.32, 0.04), 0.45, 0.6)
        wood = _flat("ir_pallet_wood", (0.55, 0.42, 0.26), 0.8); card = _flat("ir_carton", (0.62, 0.46, 0.28), 0.85)
        wrap = _flat("ir_stretch_wrap", (0.8, 0.82, 0.84), 0.25, transmission=0.3)
        posts = [("box", (sx * (D / 2 - 0.04), sy * (L / 2 - 0.04), H / 2), (0.08, 0.08, H), (0, 0, 0)) for sx in (1, -1) for sy in (1, -1)]
        braces = [("box", (0, sy * (L / 2 - 0.04), z), (D - 0.1, 0.03, 0.03), (0, 0, 0)) for sy in (1, -1) for z in (0.4, 1.6, 2.8, 4.0) if z < H]
        levels = [0.0, 1.45, 2.9] + ([4.1] if H > 4.3 else [])
        beams = [("box", (sx * (D / 2 - 0.04), 0, z), (0.05, L - 0.1, 0.12), (0, 0, 0)) for sx in (1, -1) for z in levels[1:]]
        pal, box, wr = [], [], []
        for z in levels:
            z0 = z + (0.06 if z > 0 else 0.0)
            for y in (-0.62, 0.62):
                pal.append(("box", (0, y, z0 + 0.07), (1.0, 1.15, 0.14), (0, 0, 0)))
                h = r.uniform(0.5, 1.0) if z < levels[-1] else r.uniform(0.3, 0.6)
                if r.random() < 0.85:
                    box.append(("box", (0, y, z0 + 0.14 + h / 2), (0.95, 1.1, h), (0, 0, 0)))
                    if r.random() < 0.5:
                        wr.append(("box", (0, y, z0 + 0.14 + h / 2), (0.97, 1.12, h + 0.01), (0, 0, 0)))
        return _prims(f"PalletRackFactory({i}).spawn_asset({i})", [(blue, posts + braces), (orange, beams), (wood, pal), (card, box)] + ([(wrap, wr)] if wr else []))


class UrinalFactory:
    """Two wall-hung urinals with a privacy divider between them (front +X, back on the wall): the second restroom of a café floor
    becomes the gents' -- two identical single WCs with half the room bare read as 'oversized, unfinished copies' (floor H r31, 3 of 3)."""
    def __init__(self, seed):
        self.r = random.Random(seed)

    def spawn_asset(self, i):
        D = 0.42; xb = -D / 2
        cer = _flat("ir_ceramic_white", (0.93, 0.93, 0.92), 0.12); chrome = _flat("ir_chrome", (0.8, 0.8, 0.82), 0.15, 1.0)
        div = _flat("ir_urinal_divider", (0.62, 0.64, 0.66), 0.35)
        hole = _flat("ir_urinal_bowl", (0.55, 0.57, 0.58), 0.2)
        bowls, pipes, holes = [], [], []
        for y in (-0.38, 0.38):
            bowls += [("rbox", (xb + 0.17, y, 0.85), (0.32, 0.38, 0.66), (0, 0, 0))]
            holes += [("rbox", (xb + 0.31, y, 0.8), (0.05, 0.26, 0.42), (0, 0, 0))]   # the dark bowl opening: plain white boxes on a
            # steel sheet read as 'two dispensers on a floating panel' (floor J r22, 2 of 3)
            pipes += [("cyl", (xb + 0.05, y, 1.35), (0.016, 0.016, 0.34), (0, 0, 0)), ("box", (xb + 0.06, y, 1.53), (0.06, 0.08, 0.06), (0, 0, 0)),
                      ("cyl", (xb + 0.08, y, 0.26), (0.022, 0.022, 0.52), (0, 0, 0))]   # waste pipe to the floor: the placer sets the
            # lowest point on the floor, and without it the wall-hung bowls sank (floor H r32)
        panel = [("box", (xb + 0.21, 0.0, 1.0), (0.4, 0.025, 0.8), (0, 0, 0))]
        return _prims(f"UrinalFactory({i}).spawn_asset({i})", [(cer, bowls), (chrome, pipes), (div, panel), (hole, holes)])


class RollerShutterFactory:
    """A loading-dock roller shutter on a hall wall (front +X, back on the wall): grey steel slats in side guides under a coil box, a
    yellow-black hazard strip on the floor and two yellow bollards (floor J r18: 'no dock or roller door -- a big stockroom', 3 of 3)."""
    def __init__(self, seed):
        self.r = random.Random(seed)

    def spawn_asset(self, i):
        D, W, H = 0.5, 3.6, 4.0
        steel = _flat("ir_shutter_steel", (0.5, 0.52, 0.54), 0.4, 0.8); dark = _flat("ir_shutter_guide", (0.18, 0.19, 0.2), 0.45, 0.7)
        yel = _flat("ir_hazard_yellow", (0.85, 0.62, 0.02), 0.5); blk = _flat("ir_ink", (0.05, 0.05, 0.06), 0.6)
        xb = -D / 2
        slats = [("box", (xb + 0.03, 0, H / 2), (0.03, W, H), (0, 0, 0))] + \
                [("box", (xb + 0.05, 0, 0.1 + k * 0.13), (0.015, W, 0.035), (0, 0, 0)) for k in range(int((H - 0.2) / 0.13))]
        guides = [("box", (xb + 0.06, s * (W / 2 + 0.06), (H + 0.3) / 2), (0.12, 0.12, H + 0.3), (0, 0, 0)) for s in (1, -1)] + \
                 [("box", (xb + 0.18, 0, H + 0.3), (0.36, W + 0.3, 0.45), (0, 0, 0))]
        haz = [("box", (xb + 0.35, 0, 0.003), (0.3, W, 0.006), (0, 0, 0))]
        stripes = [("box", (xb + 0.35, -W / 2 + 0.15 + k * 0.3, 0.0065), (0.3, 0.12, 0.002), (0, 0, 0.6)) for k in range(int(W / 0.3))]
        bollards = [("cyl", (xb + 0.4, s * (W / 2 + 0.25), 0.55), (0.08, 0.08, 1.1), (0, 0, 0)) for s in (1, -1)]
        return _prims(f"RollerShutterFactory({i}).spawn_asset({i})", [(steel, slats), (dark, guides), (yel, haz + bollards), (blk, stripes)])


class ExamTableFactory:
    """Examination / treatment couch (front +X): padded top at 0.7 m with a raised head section, a cabinet base, a paper roll, a step."""
    def __init__(self, seed):
        r = random.Random(seed)
        self.c = r.choice(((0.03, 0.12, 0.2), (0.03, 0.03, 0.035), (0.02, 0.15, 0.16), (0.06, 0.08, 0.2)))  # deep vinyl: pale pads vanished (r5, r8)

    def spawn_asset(self, i):
        # a couch, not a cabinet (clinic r6: 'a white box with a grey slab'): a narrow inset plinth on a steel frame with open space
        # around it, a thick padded top overhanging it, the head section raised 30 deg, a paper roll and a step
        pad = _flat(f"ir_exam_pad_{int(self.c[2] * 100)}", self.c, 0.55); base = _flat("ir_pantry_cab_90", (0.9, 0.9, 0.88), 0.45)
        paper = _flat("ir_paper", (0.93, 0.93, 0.9), 0.7); steel = _flat("ir_desk_frame", (0.75, 0.75, 0.76), 0.35, 0.8)
        hy, hz = 0.45, 0.72                                      # head hinge (local y) and top height
        return _prims(f"ExamTableFactory({i}).spawn_asset({i})",
                      [(base, [("box", (0, -0.1, 0.33), (0.4, 0.9, 0.5), (0, 0, 0)), ("box", (0.45, -0.35, 0.11), (0.28, 0.42, 0.22), (0, 0, 0))]),
                       (steel, [("box", (0, -0.1, 0.03), (0.55, 1.3, 0.04), (0, 0, 0)), ("box", (0, -0.1, 0.62), (0.5, 1.2, 0.05), (0, 0, 0)),
                                ("cyl", (0, -0.98, 0.7), (0.05, 0.05, 0.56), (0, math.pi / 2, math.pi / 2))]),
                       (pad, [("box", (0, -0.2, hz), (0.68, 1.3, 0.12), (0, 0, 0)),
                              ("box", (0, hy + 0.3 * math.cos(0.52), hz + 0.3 * math.sin(0.52)), (0.68, 0.62, 0.12), (0.52, 0, 0))]),
                       (paper, [("box", (0, -0.35, hz + 0.062), (0.4, 0.9, 0.003), (0, 0, 0)),   # a strip: a full sheet read as a white desk
                                ("cyl", (0, -0.98, 0.7), (0.07, 0.07, 0.5), (0, math.pi / 2, math.pi / 2))])])


class PrivacyCurtainFactory:
    """Ceiling-hung privacy curtain (front +X): an L-shaped track at 2.3 m with a pleated fabric panel down to 0.3 m off the floor."""
    def __init__(self, seed, L=2.6, D=1.6):                       # longer than a 2.27 m couch: a 2.2 m run's return crossed its head end
        r = random.Random(seed)
        self.L, self.D = L, D; self.c = r.choice(((0.55, 0.7, 0.72), (0.7, 0.75, 0.82), (0.82, 0.82, 0.8)))

    def spawn_asset(self, i):
        L, D = self.L, self.D
        fab = _flat(f"ir_curtain_{int(self.c[1] * 100)}", self.c, 0.9); rail = _flat("ir_desk_frame", (0.75, 0.75, 0.76), 0.35, 0.8)
        drawn = random.Random(i).uniform(0.22, 0.38)          # bunched back (clinic r3: a closed curtain hid the couch; r5: still hid the beds)
        # fabric folds: thin panels zig-zagging +-40 deg; parallel 5 cm slabs read as a folding screen (clinic r5 critic)
        n1, n2 = int(L * drawn / 0.06), int(D * 0.4 / 0.06)
        folds = [("box", (0.0, L / 2 - (k + 0.5) * 0.06, 1.32), (0.006, 0.075, 1.98), (0, 0, 0.7 if k % 2 else -0.7)) for k in range(n1)]
        folds += [("box", (-D / 2 + (k + 0.5) * 0.06, L / 2, 1.32), (0.075, 0.006, 1.98), (0, 0, 0.7 if k % 2 else -0.7)) for k in range(n2)]
        hooks = [("box", (0, L / 2 - (k + 0.5) * 0.06, 2.31), (0.012, 0.012, 0.03), (0, 0, 0)) for k in range(n1)]
        hooks += [("box", (0, y_, 2.33 + 0.35), (0.012, 0.012, 0.7), (0, 0, 0)) for y_ in (-L / 2 + 0.05, 0.0, L / 2 - 0.05)]   # ceiling hangers:
        hooks += [("box", (-D / 2 + 0.05, L / 2, 2.33 + 0.35), (0.012, 0.012, 0.7), (0, 0, 0))]   # a hung track, not a screen (clinic r17)
        return _prims(f"PrivacyCurtainFactory({i}).spawn_asset({i})",
                      [(fab, folds), (rail, hooks + [("box", (0, 0, 2.33), (0.03, L, 0.03), (0, 0, 0)),
                                                     ("box", (-D / 4, L / 2, 2.33), (D / 2, 0.03, 0.03), (0, 0, 0))])])


class DentalChairFactory:
    """Dental treatment unit (front +X = the patient's feet). The upholstery is one chained shape: a level seat, a backrest whose lower
    edge sits on the seat's back edge (reclined 32 deg), a headrest continuing it, a leg rest dropping from the seat's front edge -- each
    part positioned from its joint, so nothing floats (clinic r2: 'the chair comes apart'). A base column, armrests, an operating lamp on a
    post arching over the headrest, an instrument tray on a swing arm, a spittoon, and a dentist's stool."""
    def __init__(self, seed):
        r = random.Random(seed)
        # coloured upholstery only (dental r20: a white chair among white cabinets lost the room its function, 4/10 in 3 of 3 calls)
        self.c = r.choice(((0.05, 0.25, 0.5), (0.03, 0.35, 0.38), (0.15, 0.4, 0.25), (0.35, 0.1, 0.25)))
        self.side = r.choice((1, -1))

    def spawn_asset(self, i):
        sd, W = self.side, 0.56
        up = _flat(f"ir_dental_{int(self.c[1] * 100)}_{int(self.c[2] * 100)}", self.c, 0.35); white = _flat("ir_ac_white", (0.86, 0.86, 0.85), 0.4)
        steel = _flat("ir_chrome", (0.8, 0.8, 0.82), 0.15, 1.0); lamp = _flat("ir_led_panel", (1.0, 1.0, 1.0), 0.3)
        zs, x0, x1, t = 0.6, -0.25, 0.3, 0.13                    # seat: x from x0 (back edge) to x1 (front edge) at height zs
        a, Lb = math.radians(32), 0.68                          # backrest: up from (x0, zs) at angle a
        bx, bz = x0 - math.cos(a) * Lb / 2, zs + math.sin(a) * Lb / 2
        hx, hz = x0 - math.cos(a) * (Lb + 0.13), zs + math.sin(a) * (Lb + 0.13)     # headrest continues the backrest
        c, Ll = math.radians(28), 0.62                          # leg rest: down from (x1, zs) at angle c
        lx, lz = x1 + math.cos(c) * Ll / 2, zs - math.sin(c) * Ll / 2
        tip_x, tip_z = hx - math.cos(a) * 0.16, hz + math.sin(a) * 0.16
        return _prims(f"DentalChairFactory({i}).spawn_asset({i})",
                      [(up, [("rbox", ((x0 + x1) / 2, 0, zs), (x1 - x0, W, t), (0, 0, 0)),
                             ("rbox", (bx, 0, bz), (Lb, W, t), (0, a, 0)),
                             ("rbox", (hx, 0, hz), (0.26, 0.3, 0.1), (0, a, 0)),
                             ("rbox", (lx, 0, lz), (Ll, W - 0.06, t), (0, c, 0)),
                             ("rbox", (0.02, W / 2 + 0.05, zs + 0.17), (0.42, 0.08, 0.07), (0, 0, 0)),
                             ("rbox", (0.02, -W / 2 - 0.05, zs + 0.17), (0.42, 0.08, 0.07), (0, 0, 0)),
                             ("cyl", (0.65, -sd * 0.68, 0.52), (0.2, 0.2, 0.08), (0, 0, 0))]),          # stool seat
                       (white, [("box", (0, 0, 0.02), (0.75, 0.6, 0.04), (0, 0, 0)), ("rbox", (0.0, 0, 0.3), (0.34, 0.36, 0.56), (0, 0, 0)),
                                ("cyl", (0.0, sd * 0.5, 0.72), (0.035, 0.035, 0.2), (0, 0, 0)),
                                ("cyl", (0.0, sd * 0.5, 0.85), (0.09, 0.09, 0.07), (0, 0, 0))]),     # cuspidor: a small bowl on the chair
                                # side, not a white cone on a floor post ('a lampshade', floor E3 r15, 2 of 3)
                       (steel, [("cyl", (x0 - 0.05, -sd * 0.32, 1.15), (0.03, 0.03, 0.9), (0, 0, 0)),     # a short lamp post on the chair: the
                                ("box", (x0 - 0.05, -sd * 0.16, 1.6), (0.05, 0.32, 0.04), (0, 0, 0)),     # 2.1 m one read as 'a floor-to-ceiling
                                ("box", ((x0 - 0.05 + tip_x + 0.15) / 2, 0, 1.6), (abs(tip_x + 0.2 - x0), 0.05, 0.04), (0, 0, 0)),   # pole' (E3 r10, 3/3)
                                ("rbox", (tip_x + 0.15, 0, tip_z + 0.42), (0.3, 0.2, 0.08), (0, 0.5, 0)),     # lamp head
                                ("cyl", (0.3, -sd * 0.75, 1.0), (0.02, 0.02, 0.5), (0, 0, 0)),             # monitor arm
                                ("cyl", (0.12, -sd * 0.6, 0.48), (0.025, 0.025, 0.96), (0, 0, 0)),
                                ("box", (0.12, -sd * 0.45, 0.98), (0.45, 0.32, 0.03), (0, 0, 0)),          # instrument tray
                                ("cyl", (0.65, -sd * 0.68, 0.24), (0.03, 0.03, 0.48), (0, 0, 0)),
                                ("box", (0.65, -sd * 0.68, 0.01), (0.45, 0.45, 0.02), (0, 0, 0.4))]),
                       (lamp, [("box", (tip_x + 0.15, 0, tip_z + 0.375), (0.24, 0.15, 0.005), (0, 0.5, 0))]),
                       # the patient monitor: a matte black body and a dark screen -- in chrome it mirrored the chair as 'a frosted
                       # panel with teal blobs floating beside it' (floor E3 r13, 3 of 3)
                       (_flat("ir_monitor_plastic", (0.03, 0.03, 0.035), 0.6), [("box", (0.3, -sd * 0.75, 1.32), (0.04, 0.42, 0.28), (0, 0, 0))]),
                       (_flat("ir_screen_dark", (0.01, 0.015, 0.02), 0.2), [("box", (0.3 + 0.021, -sd * 0.75, 1.32), (0.002, 0.38, 0.24), (0, 0, 0))])])


class WallBarsFactory:
    """Physio wall bars (front +X): two uprights, 10-14 round rungs, 0.9 m wide, 2.4 m tall; stands against a wall."""
    def __init__(self, seed):
        self.n = random.Random(seed).randint(10, 14)

    def spawn_asset(self, i):
        wood = _flat("ir_wallbars_wood", (0.72, 0.56, 0.36), 0.5)
        parts = [("box", (0, sy * 0.45, 1.2), (0.08, 0.05, 2.4), (0, 0, 0)) for sy in (1, -1)]
        parts += [("cyl", (0, 0, 0.2 + k * 2.1 / self.n), (0.017, 0.017, 0.9), (math.pi / 2, 0, 0)) for k in range(self.n)]
        return _prims(f"WallBarsFactory({i}).spawn_asset({i})", [(wood, parts)])


class ExerciseSetFactory:
    """Physio floor kit (front +X): a rolled-out mat, a gym ball, a couple of dumbbells on the mat."""
    def __init__(self, seed):
        r = random.Random(seed)
        self.mc = r.choice(((0.2, 0.45, 0.6), (0.3, 0.32, 0.35), (0.25, 0.55, 0.35)))   # clinical blues/greys/greens (clinic r16:
        self.bc = r.choice(((0.05, 0.2, 0.5), (0.1, 0.35, 0.15), (0.45, 0.3, 0.05)))       # 'pink/salmon poufs read as home decor';
        # grey read as a bin / pouf in r23 -- a saturated ball reads as a gym ball

    def spawn_asset(self, i):
        mat = _flat(f"ir_mat_{int(self.mc[0] * 100)}", self.mc, 0.8); ball = _flat(f"ir_gymball_{int(self.bc[0] * 100)}", self.bc, 0.35)
        black = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0)
        return _prims(f"ExerciseSetFactory({i}).spawn_asset({i})",
                      [(mat, [("box", (0, 0, 0.004), (0.6, 1.8, 0.008), (0, 0, 0))]),
                       (ball, [("sph", (0.05, 1.3, 0.32), (0.32, 0.32, 0.32), (0, 0, 0))]),   # a ball, not a drum (clinic r23, 3 of 3)
                       (black, [("cyl", (0.1, -0.5 + k * 0.25, 0.04), (0.04, 0.04, 0.3), (0, math.pi / 2, 0)) for k in range(2)])])


class ParallelBarsFactory:
    """Physio parallel walking bars (front +X): two 2.4-3.0 m steel handrails at 0.9 m on four posts, on a low platform."""
    def __init__(self, seed):
        self.L = random.Random(seed).choice((2.4, 3.0))

    def spawn_asset(self, i):
        L = self.L
        steel = _flat("ir_chrome", (0.8, 0.8, 0.82), 0.15, 1.0); base = _flat("ir_bars_platform", (0.06, 0.065, 0.07), 0.7)   # dark rubber, one piece with the bars
        # (clinic r25: the blue platform read as 'an exercise mat laid under the bars', 2 of 3)
        posts = [("cyl", (sx * 0.3, sy * (L / 2 - 0.1), 0.47), (0.02, 0.02, 0.9), (0, 0, 0)) for sx in (1, -1) for sy in (1, -1)]
        rails = [("cyl", (sx * 0.3, 0, 0.92), (0.02, 0.02, L), (math.pi / 2, 0, 0)) for sx in (1, -1)]
        return _prims(f"ParallelBarsFactory({i}).spawn_asset({i})", [(steel, posts + rails), (base, [("box", (0, 0, 0.02), (0.9, L + 0.1, 0.04), (0, 0, 0))])])


class ExerciseBikeFactory:
    """Upright exercise bike (front +X): a frame, a flywheel housing, a saddle, handlebars and a console."""
    def __init__(self, seed):
        self.c = random.Random(seed).choice(((0.1, 0.1, 0.1), (0.85, 0.85, 0.85), (0.6, 0.1, 0.1)))

    def spawn_asset(self, i):
        # stabiliser feet, a tube frame, a flywheel housing, saddle post, handlebar post with console, cranks; the old version stood a
        # 0.95 x 0.5 slab under tilted boxes and read as 'a tangle of black parts' (clinic r5 critic)
        body = _flat(f"ir_bike_{int(self.c[0] * 100)}", self.c, 0.4, 0.3); black = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0)
        tube = lambda p, q, r=0.025: ("cyl", tuple((a + b) / 2 for a, b in zip(p, q)), (r, r, math.dist(p, q)),
                                      (0, math.atan2(q[0] - p[0], q[2] - p[2]), 0))
        return _prims(f"ExerciseBikeFactory({i}).spawn_asset({i})",
                      [(body, [("cyl", (0.22, 0, 0.36), (0.26, 0.26, 0.1), (math.pi / 2, 0, 0)), tube((-0.4, 0, 0.06), (0.22, 0, 0.36), 0.035),
                               ("box", (0.36, 0, 1.06), (0.08, 0.26, 0.17), (0, -0.5, 0))]),
                       (black, [("box", (-0.42, 0, 0.03), (0.08, 0.5, 0.06), (0, 0, 0)), ("box", (0.42, 0, 0.03), (0.08, 0.5, 0.06), (0, 0, 0)),
                                tube((0.42, 0, 0.06), (0.22, 0, 0.36), 0.035), tube((-0.12, 0, 0.36), (-0.24, 0, 0.84)),
                                ("box", (-0.25, 0, 0.88), (0.26, 0.17, 0.06), (0, 0, 0)), tube((0.22, 0, 0.36), (0.33, 0, 1.0), 0.03),
                                ("cyl", (0.34, 0, 1.0), (0.016, 0.016, 0.48), (math.pi / 2, 0, 0)),
                                ("box", (0.05, 0.12, 0.28), (0.18, 0.02, 0.03), (0, 0.6, 0)), ("box", (0.05, -0.12, 0.28), (0.18, 0.02, 0.03), (0, -0.6, 0))])])


class ClothingRackFactory:
    """Boutique clothing rail (front +X): a 1.2-1.6 m chrome rail at 1.5 m on two feet, 10-16 garments on hangers in a palette."""
    def __init__(self, seed):
        r = random.Random(seed)
        self.L = r.choice((1.2, 1.4, 1.6)); self.n = r.randint(10, 16); self.r = r
        self.pal = r.choice((((0.85, 0.82, 0.75), (0.2, 0.25, 0.35), (0.6, 0.45, 0.3)), ((0.1, 0.1, 0.1), (0.8, 0.8, 0.78), (0.55, 0.15, 0.15)),
                             ((0.7, 0.75, 0.65), (0.85, 0.75, 0.7), (0.35, 0.4, 0.3))))

    def spawn_asset(self, i):
        L, r = self.L, self.r
        chrome = _flat("ir_chrome", (0.8, 0.8, 0.82), 0.15, 1.0)
        groups = [(chrome, [(0, 0, 1.5, 0.03, L, 0.03), (0, L / 2 - 0.02, 0.75, 0.03, 0.03, 1.5), (0, -L / 2 + 0.02, 0.75, 0.03, 0.03, 1.5),
                            (0, L / 2 - 0.02, 0.01, 0.45, 0.04, 0.02), (0, -L / 2 + 0.02, 0.01, 0.45, 0.04, 0.02)])]
        hanger = _flat("ir_hanger_wood", (0.55, 0.4, 0.25), 0.5)
        hang, by_col = [], {}
        for k in range(self.n):                                  # a garment: hanger, shoulders, a body, two sleeves (shop r1: 'flat slabs')
            y = -L / 2 + 0.08 + (k + 0.5) * (L - 0.16) / self.n
            c = r.choice(self.pal); h = r.uniform(0.55, 1.05); w = r.uniform(0.38, 0.46); t = r.uniform(0.04, 0.08)
            hang.append(("box", (0, y, 1.45), (0.4, 0.008, 0.02), (0.15, 0, 0)))
            g = by_col.setdefault(c, [])
            # straight hems: ellipsoid bodies read as 'socks' (shop r5), flat boxes as 'slabs' (r4): a box body with a soft shoulder line;
            # the two end garments hang face-out, showing the silhouette (shoulders, sleeves) the side-on ones cannot
            face = k in (0, self.n - 1)
            if face:
                g.append(("box", (0, y, 1.41 - h / 2), (t, w * 0.85, h), (0, 0, 0)))
                g.append(("sph", (0, y, 1.39), (t * 0.6, w * 0.47, 0.05), (0, 0, 0)))
                for sy in (1, -1):
                    g.append(("cyl", (0, y + sy * w * 0.47, 1.17), (0.035, 0.045, 0.44), (sy * 0.15, 0, 0)))
            else:
                g.append(("sph", (0, y, 1.39), (w * 0.47, t * 0.55, 0.05), (0, 0, 0)))
                g.append(("box", (0, y, 1.41 - h / 2), (w * 0.85, t, h), (0, r.uniform(-0.03, 0.03), 0)))
                g.append(("box", (0, y, 1.41 - h + 0.04), (w * 0.92, t * 1.1, 0.08), (0, 0, 0)))          # hem
        groups.append((hanger, hang))
        for c, parts in by_col.items():
            groups.append((_flat(f"ir_garment_{int(c[0] * 100)}_{int(c[1] * 100)}", c, 0.9), parts))
        return _prims(f"ClothingRackFactory({i}).spawn_asset({i})", [(m, [("box", (cx, cy, cz), (sx, sy, sz), (0, 0, 0)) for cx, cy, cz, sx, sy, sz in parts])
                                                                     if parts and len(parts[0]) == 6 else (m, parts) for m, parts in groups])


class DisplayTableFactory:
    """Boutique display table (front +X): a 1.2-1.6 m wood or white table with stacks of folded clothes and a pair of shoes."""
    def __init__(self, seed):
        r = random.Random(seed)
        self.L = r.choice((1.2, 1.4, 1.6)); self.top = r.choice(((0.62, 0.5, 0.36), (0.9, 0.9, 0.88), (0.15, 0.15, 0.15))); self.r = r

    def spawn_asset(self, i):
        L, r = self.L, self.r
        top = _flat(f"ir_disp_top_{int(self.top[0] * 100)}", self.top, 0.45); steel = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0)
        stacks = []
        for k in range(r.randint(3, 5)):                         # folded garments: 2-6 layers, rounded fold edge, mixed shades
            x0, y0 = r.uniform(-0.15, 0.15), -L / 2 + (k + 0.5) * L / 5.2
            base = r.choice(_BRIGHT + ((0.85, 0.82, 0.75), (0.2, 0.25, 0.35)))
            for j in range(r.randint(2, 6)):
                c = tuple(min(1.0, max(0.0, v * r.uniform(0.8, 1.15))) for v in base)
                stacks.append((_flat(f"ir_folded_{int(c[0] * 100)}_{int(c[1] * 100)}_{int(c[2] * 100)}", c, 0.9),
                               [(x0 + r.uniform(-0.01, 0.01), y0 + r.uniform(-0.01, 0.01), 0.775 + j * 0.032, 0.3, 0.25, 0.028)]))
        return _parts_object(f"DisplayTableFactory({i}).spawn_asset({i})",
                             [(top, [(0, 0, 0.74, 0.8, L, 0.04)]), (steel, [(0, sy * (L / 2 - 0.05), 0.36, 0.7, 0.04, 0.72) for sy in (1, -1)])] + stacks)


class MirrorFactory:
    """Free-standing full-length mirror (front +X), 0.6 x 1.8 m, black or brass frame, leaning slightly."""
    def __init__(self, seed):
        self.f = random.Random(seed).choice(((0.03, 0.03, 0.03), (0.7, 0.55, 0.3)))

    def spawn_asset(self, i):
        frame = _flat(f"ir_mirror_frame_{int(self.f[0] * 100)}", self.f, 0.3, 1.0); glass = _flat("ir_mirror", (0.95, 0.95, 0.95), 0.02, 1.0)
        return _prims(f"MirrorFactory({i}).spawn_asset({i})",
                      [(frame, [("box", (0, 0, 0.92), (0.04, 0.64, 1.84), (0, -0.08, 0))]), (glass, [("box", (0.021, 0, 0.92), (0.005, 0.56, 1.76), (0, -0.08, 0))])])


class FittingRoomFactory:
    """Fitting room cubicle (front +X): two side panels and a back panel 1.0 x 1.2 m, 2.2 m high, a curtain across the front, a hook."""
    def __init__(self, seed):
        r = random.Random(seed)
        self.c = r.choice(((0.85, 0.8, 0.72), (0.3, 0.3, 0.32), (0.55, 0.15, 0.15)))

    def spawn_asset(self, i):
        wall = _flat("ir_fitting_wall", (0.9, 0.9, 0.88), 0.5); fab = _flat(f"ir_curtain_{int(self.c[0] * 100)}", self.c, 0.85)
        rail = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0)
        # zig-zag fabric folds over 40-70% of the opening (shop r2: parallel slabs read as an unfinished partition)
        n = int(1.0 * random.Random(i).uniform(0.4, 0.7) / 0.06)
        folds = [("box", (0.6, 0.48 - (k + 0.5) * 0.06, 1.15), (0.006, 0.075, 1.95), (0, 0, 0.7 if k % 2 else -0.7)) for k in range(n)]
        return _prims(f"FittingRoomFactory({i}).spawn_asset({i})",
                      [(wall, [("box", (0, -0.52, 1.1), (1.2, 0.04, 2.2), (0, 0, 0)), ("box", (0, 0.52, 1.1), (1.2, 0.04, 2.2), (0, 0, 0)),
                               ("box", (-0.58, 0, 1.1), (0.04, 1.08, 2.2), (0, 0, 0))]),
                       (fab, folds), (rail, [("box", (0.6, 0, 2.15), (0.02, 1.0, 0.02), (0, 0, 0)),
                                             ("box", (-0.55, 0.3, 1.7), (0.06, 0.02, 0.02), (0, 0, 0))])])


class MenuBoardFactory:
    """Café menu board (front +X): a 1.2-1.8 m black chalkboard or light board in a wood/black frame with rows of chalk 'text' lines
    and price columns; hung on the wall above the bar (cafe r2: no café had one)."""
    def __init__(self, seed):
        r = random.Random(seed)
        self.W = r.choice((1.2, 1.5, 1.8)); self.dark = r.random() < 0.7; self.r = r

    def spawn_asset(self, i):
        W, H, r = self.W, 0.8, self.r
        board = _flat("ir_chalkboard" if self.dark else "ir_menu_light", (0.04, 0.05, 0.05) if self.dark else (0.9, 0.88, 0.82), 0.8)
        frame = _flat("ir_menu_frame", (0.35, 0.24, 0.15) if self.dark else (0.05, 0.05, 0.05), 0.5)
        ink = _flat("ir_chalk" if self.dark else "ir_menu_ink", (0.85, 0.85, 0.8) if self.dark else (0.08, 0.08, 0.08), 0.9)
        lines = []
        for col in (-1, 1):
            for k in range(6):
                z = H - 0.14 - k * 0.1
                lines.append((0.012, col * W / 4 - 0.04, z, 0.002, W * r.uniform(0.18, 0.3), 0.022))
                lines.append((0.012, col * W / 4 + W / 6, z, 0.002, 0.07, 0.022))
        lines.append((0.012, 0, H - 0.06, 0.002, W * 0.35, 0.04))          # heading
        return _parts_object(f"MenuBoardFactory({i}).spawn_asset({i})",
                             [(frame, [(0, 0, H / 2, 0.025, W + 0.06, H + 0.06)]), (board, [(0.008, 0, H / 2, 0.01, W, H)]), (ink, lines)])


class BanquetteFactory:
    """Fixed café banquette (front +X): an upholstered bench at 0.46 m with a tall back, 2.0-3.6 m long, on a plinth."""
    def __init__(self, seed, L=None):
        r = random.Random(seed)
        self.L = L or r.choice((2.0, 2.4, 3.0, 3.6))
        self.c = r.choice(((0.45, 0.12, 0.1), (0.12, 0.3, 0.25), (0.55, 0.42, 0.25), (0.15, 0.15, 0.17), (0.7, 0.55, 0.2)))
        if STYLE.get("upholstery_rgb"):                          # the reference's leather / velvet (style eval chain G: random colour)
            self.c = tuple(STYLE["upholstery_rgb"])

    def spawn_asset(self, i):
        L = self.L
        up = _flat(f"ir_banquette_{int(self.c[0] * 100)}_{int(self.c[1] * 100)}", self.c, 0.75); plinth = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0)
        n = max(2, int(L / 0.6))
        backs = [(-0.2, -L / 2 + (k + 0.5) * L / n, 0.75, 0.12, L / n - 0.02, 0.55) for k in range(n)]      # tufted back panels
        return _parts_object(f"BanquetteFactory({i}).spawn_asset({i})",
                             [(up, [(0.02, 0, 0.4, 0.5, L, 0.12)] + backs), (plinth, [(0, 0, 0.17, 0.5, L - 0.04, 0.34)])])


class CounterStoolFactory:
    """Commercial counter stool (front +X): a 0.62 m seat (round or square, polypropylene or upholstered) on a four-leg steel frame with
    a foot ring and a low back (pantry r8: ABO wooden saddle stools read as a farmhouse)."""
    def __init__(self, seed):
        r = random.Random(seed)
        if "stool" not in _ROOM_PICK:                            # one stool model per scene (pantry r16/r17: 'white high-backed stools
            _ROOM_PICK["stool"] = (r.choice(((0.1, 0.1, 0.1), (0.85, 0.85, 0.83), (0.2, 0.4, 0.55), (0.75, 0.45, 0.15), (0.55, 0.57, 0.58))),
                                   r.choice(((0.03, 0.03, 0.03), (0.75, 0.75, 0.76))))   # mixed with black backless ones at one table')
        self.c, self.frame = _ROOM_PICK["stool"]
        cs = STYLE.get("chair_style")                            # styled cafés: stools of the chair family (style eval: cream stools)
        if cs == "bentwood":
            self.c, self.frame = (0.035, 0.02, 0.012), (0.035, 0.02, 0.012)
        elif cs == "light_wood":
            self.c, self.frame = (0.62, 0.46, 0.3), (0.62, 0.46, 0.3)
        elif cs == "metal_bistro":
            self.c, self.frame = (0.04, 0.04, 0.045), (0.04, 0.04, 0.045)
        if STYLE.get("metal_finish") == "brass" and cs:
            self.frame = (0.55, 0.38, 0.12)

    def spawn_asset(self, i):
        seat = _flat(f"ir_stool_seat_{int(self.c[0] * 100)}_{int(self.c[2] * 100)}", self.c, 0.45)
        steel = _flat(f"ir_stool_frame_{int(self.frame[0] * 100)}", self.frame, 0.35, 1.0)
        legs = [("box", (sx * 0.15, sy * 0.15, 0.31), (0.025, 0.025, 0.62), (sy * 0.08, -sx * 0.08, 0)) for sx in (1, -1) for sy in (1, -1)]
        ring = [("box", (0, sy * 0.165, 0.25), (0.34, 0.02, 0.02), (0, 0, 0)) for sy in (1, -1)] + \
               [("box", (sx * 0.165, 0, 0.25), (0.02, 0.34, 0.02), (0, 0, 0)) for sx in (1, -1)]
        return _prims(f"CounterStoolFactory({i}).spawn_asset({i})",
                      [(steel, legs + ring), (seat, [("box", (0, 0, 0.635), (0.38, 0.38, 0.04), (0, 0, 0)), ("box", (-0.18, 0, 0.78), (0.03, 0.34, 0.2), (0, -0.15, 0))])])


class DrinkCansFactory:
    """Drink cans stacked on a counter (user 2026-10-16: 'cans of drinks piled up in the pantry'): a 2-layer block of 6-12 cans per
    layer in 1-3 brand colours, sometimes a cardboard tray under them."""
    def __init__(self, seed):
        r = random.Random(seed)
        self.nx, self.ny, self.layers = r.choice((2, 3)), r.choice((3, 4)), r.choice((1, 2, 2))
        self.cols = r.sample(_BRIGHT + ((0.75, 0.75, 0.78), (0.05, 0.05, 0.05)), r.randint(1, 3)); self.tray = r.random() < 0.5; self.r = r

    def spawn_asset(self, i):
        d, h, r = 0.067, 0.122, self.r
        rim = _flat("ir_chrome", (0.8, 0.8, 0.82), 0.15, 1.0)
        groups, by = [], {}
        for lz in range(self.layers):
            for ix in range(self.nx):
                for iy in range(self.ny):
                    if lz and r.random() < 0.25:
                        continue                                # an upper layer with gaps: some already taken
                    c = r.choice(self.cols)
                    by.setdefault(c, []).append(("cyl", ((ix - (self.nx - 1) / 2) * d, (iy - (self.ny - 1) / 2) * d, 0.01 + h / 2 + lz * h),
                                                 (d / 2, d / 2 - 0.002, h), (0, 0, 0)))
        for c, parts in by.items():
            groups.append((_flat(f"ir_can_{int(c[0] * 100)}_{int(c[1] * 100)}_{int(c[2] * 100)}", c, 0.25, 0.6), parts))
        if self.tray:
            groups.append((_flat("ir_cardboard_tray", (0.55, 0.42, 0.28), 0.8), [("box", (0, 0, 0.012), (self.nx * d + 0.01, self.ny * d + 0.01, 0.024), (0, 0, 0))]))
        groups.append((rim, [("cyl", (0, 0, 0.001), (0.001, 0.001, 0.001), (0, 0, 0))]))
        return _prims(f"DrinkCansFactory({i}).spawn_asset({i})", groups)


class SnackBasketFactory:
    """A wire / wicker basket of snack bags and bars on the pantry counter (user 2026-10-16: 'some snack bags')."""
    def __init__(self, seed):
        r = random.Random(seed)
        self.r = r; self.wire = r.random() < 0.5

    def spawn_asset(self, i):
        r = self.r
        basket = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0) if self.wire else _flat("ir_wicker", (0.6, 0.45, 0.28), 0.8)
        W, D, H = 0.36, 0.26, 0.12
        groups = [(basket, [("box", (0, 0, 0.005), (D, W, 0.01), (0, 0, 0)), ("box", (D / 2, 0, H / 2), (0.01, W, H), (0, 0, 0)),
                            ("box", (-D / 2, 0, H / 2), (0.01, W, H), (0, 0, 0)), ("box", (0, W / 2, H / 2), (D, 0.01, H), (0, 0, 0)),
                            ("box", (0, -W / 2, H / 2), (D, 0.01, H), (0, 0, 0))])]
        for k in range(r.randint(4, 7)):
            c = r.choice(_BRIGHT)
            groups.append((_flat(f"ir_snack_{int(c[0] * 100)}_{int(c[2] * 100)}", c, 0.3, 0.4),
                           [("box", (r.uniform(-0.07, 0.07), -W / 2 + 0.05 + k * (W - 0.1) / 6, 0.09 + r.uniform(0, 0.04)),
                             (0.04, 0.14, 0.2), (r.uniform(-0.5, 0.5), r.uniform(-0.3, 0.3), r.uniform(-0.3, 0.3)))]))
        return _prims(f"SnackBasketFactory({i}).spawn_asset({i})", groups)


class ProductBoxFactory:
    """A retail product (front +X): a cereal / cracker / tea / detergent box with a coloured body and a contrasting label band, or a
    bottle; sizes and colours vary per facing (shop r1: 'the same few primitives in a row')."""
    def __init__(self, seed):
        r = random.Random(seed); self.r = r
        self.kind = r.choice(("cereal", "cracker", "tea", "detergent", "bottle"))
        self.c1, self.c2 = r.sample(_BRIGHT + ((0.9, 0.85, 0.6), (0.2, 0.15, 0.1), (0.85, 0.85, 0.85)), 2)

    def spawn_asset(self, i):
        body = _flat(f"ir_prod_{int(self.c1[0] * 100)}_{int(self.c1[1] * 100)}_{int(self.c1[2] * 100)}", self.c1, 0.4)
        band = _flat(f"ir_prod_{int(self.c2[0] * 100)}_{int(self.c2[1] * 100)}_{int(self.c2[2] * 100)}", self.c2, 0.4)
        if self.kind == "bottle":
            h = self.r.uniform(0.2, 0.3)
            return _prims(f"ProductBoxFactory({i}).spawn_asset({i})", [(body, [("cyl", (0, 0, h * 0.4), (0.035, 0.035, h * 0.8), (0, 0, 0)),
                                                                              ("cyl", (0, 0, h * 0.9), (0.015, 0.012, h * 0.2), (0, 0, 0))]),
                                                                      (band, [("cyl", (0, 0, h * 0.45), (0.036, 0.036, h * 0.25), (0, 0, 0))])])
        d, w, h = {"cereal": (0.07, 0.19, 0.28), "cracker": (0.06, 0.2, 0.12), "tea": (0.07, 0.13, 0.08), "detergent": (0.12, 0.2, 0.25)}[self.kind]
        return _parts_object(f"ProductBoxFactory({i}).spawn_asset({i})", [(body, [(0, 0, h / 2, d, w, h)]),
                                                                          (band, [(d / 2 + 0.001, 0, h * 0.55, 0.002, w * 0.9, h * 0.3)])])


class PantryRunFactory:
    """Office pantry run (front +X): base cabinets + worktop, upper cabinets at 1.45-2.15 m, an inset sink under a tall gooseneck tap, an
    under-counter glass-door drinks fridge stocked with rows of cans, and a full-height stainless fridge column closing one end. The
    fridge is part of the run (pantry r9: a separate fridge stood in the middle of the floor; the 5 mm sink did not read)."""
    def __init__(self, seed, L=None):
        r = random.Random(seed)
        self.L = L or r.choice((2.4, 3.0, 3.6)); self.c = r.choice(((0.9, 0.9, 0.88), (0.35, 0.38, 0.4), (0.6, 0.48, 0.34)))
        self.r = r; self.fridge = True

    def spawn_asset(self, i):
        L, r = self.L, self.r
        Lc = L - 0.7 if self.fridge else L                       # cabinets; the last 0.7 m is the fridge column
        y0 = -L / 2                                             # cabinet run from y0 to y0 + Lc, fridge column after it
        cab = _flat(f"ir_pantry_cab_{int(self.c[0] * 100)}", self.c, 0.45); top = _flat("ir_counter_top_white_stone", (0.86, 0.85, 0.82), 0.25)
        steel = _flat("ir_steel", (0.62, 0.62, 0.64), 0.2, 1.0); gap = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0)
        glass = _flat("ir_fridge_glass", (0.85, 0.9, 0.92), 0.05, transmission=0.85)
        base = [(0, y0 + Lc / 2, 0.45, 0.6, Lc, 0.9)]
        doors = [(0.301, y0 + k * 0.6, 0.45, 0.002, 0.004, 0.8) for k in range(1, int(Lc / 0.6))]
        nu = max(1, int(Lc / 0.5))                               # upper doors: seams and pulls (clinic r14 / pantry r20: 'one blank,
        doors += [(0.041, y0 + k * Lc / nu, 1.8, 0.002, 0.004, 0.66) for k in range(1, nu)]          # doorless box')
        doors += [(0.048, y0 + (k + 0.5) * Lc / nu, 1.5, 0.012, 0.14, 0.012) for k in range(nu)]
        upper = [(-0.13, y0 + Lc / 2, 1.8, 0.34, Lc, 0.7)]
        sink_y = y0 + 0.75
        fz = y0 + Lc + 0.35                                      # fridge column centre
        bev_y = y0 + Lc - 0.35                                   # under-counter drinks fridge: last 0.6 m of the base run
        cans = []
        for row, zc in enumerate((0.18, 0.42, 0.66)):            # three shelves of cans seen through the glass door
            for k in range(7):
                cans.append((0.18, bev_y - 0.24 + k * 0.08, zc + 0.06, 0.066, 0.066, 0.12))
        can_cols = [(0.75, 0.12, 0.1), (0.1, 0.35, 0.7), (0.15, 0.55, 0.25), (0.95, 0.7, 0.1)]
        can_groups = []
        for j, c in enumerate(can_cols):
            part = cans[j::len(can_cols)]
            can_groups.append((_flat(f"ir_can_{int(c[0] * 100)}_{int(c[1] * 100)}_{int(c[2] * 100)}", c, 0.25, 0.6), part))
        if not self.fridge:                                      # clinic cabinets: base + uppers + sink only
            return _parts_object(f"{type(self).__name__}({i}).spawn_asset({i})",
                                 [(cab, base + upper), (top, [(0.01, y0 + Lc / 2, 0.92, 0.62, Lc + 0.02, 0.04)]), (gap, doors),
                                  (steel, [(0.02, sink_y, 0.945, 0.44, 0.56, 0.012), (-0.22, sink_y, 1.17, 0.04, 0.04, 0.46),
                                           (-0.08, sink_y, 1.39, 0.3, 0.035, 0.035), (0.06, sink_y, 1.32, 0.035, 0.035, 0.14)]),
                                  (gap, [(0.02, sink_y, 0.95, 0.36, 0.48, 0.006)])])
        return _parts_object(f"PantryRunFactory({i}).spawn_asset({i})",
                             [(cab, base + upper), (top, [(0.01, y0 + Lc / 2, 0.92, 0.62, Lc + 0.02, 0.04)]), (gap, doors),
                              (steel, [(0.02, sink_y, 0.945, 0.44, 0.56, 0.012),                                 # sink rim
                                       (-0.22, sink_y, 1.17, 0.04, 0.04, 0.46),                                  # gooseneck: riser
                                       (-0.08, sink_y, 1.39, 0.3, 0.035, 0.035),                                 # arch over the bowl
                                       (0.06, sink_y, 1.32, 0.035, 0.035, 0.14),                                 # spout down
                                       (0.0, fz, 1.0, 0.66, 0.68, 2.0),                                          # fridge column
                                       (0.31, bev_y, 0.43, 0.02, 0.58, 0.84)]),                                  # drinks fridge frame
                              (gap, [(0.02, sink_y, 0.95, 0.36, 0.48, 0.006),                                    # dark basin
                                     (0.335, fz - 0.28, 1.15, 0.03, 0.03, 0.9), (0.331, fz, 1.32, 0.002, 0.66, 0.004),   # fridge handle, door split
                                     (0.335, fz - 0.28, 1.62, 0.03, 0.03, 0.42), (0.331, fz + 0.12, 1.12, 0.004, 0.22, 0.3),   # freezer handle,
                                     (0.331, fz - 0.333, 1.0, 0.004, 0.006, 2.0), (0.331, fz + 0.333, 1.0, 0.004, 0.006, 2.0),  # dispenser, gaskets

                                     (0.0, bev_y, 0.43, 0.5, 0.54, 0.8)]),                                       # dark fridge interior
                              (glass, [(0.322, bev_y, 0.43, 0.006, 0.54, 0.78)])] + can_groups)


class ConferenceTableFactory:
    """Conference table (front +X): a 2.4-3.6 x 1.1-1.3 m top on two pedestal bases with a cable box in the middle. L/W fixed by the
    caller when the room decides (meeting_set sizes it so both long sides seat)."""
    def __init__(self, seed, L=None, W=None):
        r = random.Random(seed)
        self.L = L or r.choice((2.4, 3.0, 3.6)); self.W = W or r.uniform(1.1, 1.3)
        self.top = r.choice(((0.88, 0.87, 0.84), (0.45, 0.32, 0.2), (0.15, 0.15, 0.15)))

    def spawn_asset(self, i):
        L, W, H = self.L, self.W, getattr(self, "H", 0.75)
        top = _flat(f"ir_conf_top_{int(self.top[0] * 100)}", self.top, 0.35); base = _flat("ir_desk_frame", (0.75, 0.75, 0.76), 0.35, 0.8)
        black = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0)
        return _parts_object(f"{type(self).__name__}({i}).spawn_asset({i})",
                             [(top, [(0, 0, H - 0.015, W, L, 0.035)]),
                              (base, [(0, sy * L * 0.28, (H - 0.03) / 2, W * 0.35, 0.12, H - 0.03) for sy in (1, -1)]),
                              (black, [(0, 0, H + 0.005, 0.22, 0.12, 0.012)])])


class BreakTableFactory(ConferenceTableFactory):
    """Office break-room table (user critique 2026-10-16: a wooden dining table reads as a home): laminate top on pedestal bases;
    a 1.05 m high table for bar stools."""
    def __init__(self, seed):
        r = random.Random(seed)
        self.L = r.choice((1.4, 1.6, 1.8)); self.W = 0.8; self.H = 0.92   # counter height: matches counter stools (r5: 1.06 table vs 0.94 stools)
        self.top = r.choice(((0.92, 0.92, 0.9), (0.15, 0.15, 0.15), (0.62, 0.5, 0.36)))
        if STYLE.get("table_top") in COUNTER_TOPS:               # a styled café's communal table shares the kit's top (style eval: white laminate)
            self.top = COUNTER_TOPS[STYLE["table_top"]][0]


class GlassPartitionFactory:
    """A full-height glass partition (front +X, length along local y): panes ~1.1 m between black steel mullions, base and head rails.
    door_at: offset along y of a 0.95 m glass door (or None). Origin at the bottom centre."""
    def __init__(self, seed, L=3.6, H=2.8, door_at=None):
        self.L, self.H, self.door_at = L, H, door_at

    def spawn_asset(self, i):
        L, H = self.L, self.H
        glass = _flat("ir_partition_glass", (0.95, 0.96, 0.96), 0.02, transmission=1.0); steel = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0)
        frames = [(0, 0, 0.025, 0.06, L, 0.05), (0, 0, H - 0.03, 0.06, L, 0.06)]
        n = max(1, round(L / 1.1))
        for k in range(n + 1):
            frames.append((0, -L / 2 + k * L / n, H / 2, 0.05, 0.04, H))
        panes = [(0, -L / 2 + (k + 0.5) * L / n, H / 2, 0.012, L / n - 0.05, H - 0.1) for k in range(n)]
        if self.door_at is not None:                              # a glass door leaf in its own frame
            y = self.door_at
            panes = [p for p in panes if abs(p[1] - y) > 0.6]
            frames += [(0, y - 0.48, 1.05, 0.05, 0.04, 2.1), (0, y + 0.48, 1.05, 0.05, 0.04, 2.1), (0, y, 2.12, 0.05, 1.0, 0.05),
                       (0.03, y + 0.3, 1.05, 0.03, 0.02, 0.5)]   # pull handle
            panes.append((0, y, 1.06, 0.012, 0.9, 2.04))
        return _parts_object(f"GlassPartitionFactory({i}).spawn_asset({i})", [(glass, panes), (steel, frames)])


class MedicalCabinetFactory(PantryRunFactory):
    """Clinic cabinet run (base + upper, sink): the pantry run in white laminate."""
    def __init__(self, seed, L=None):
        super().__init__(seed, L)
        self.c = (0.9, 0.9, 0.88); self.fridge = False


class ClinicDeskFactory(OfficeDeskFactory):
    """A small single-monitor clinic desk (clinic r1: the dual-monitor office desk was the hero of the exam and dental rooms)."""
    def __init__(self, seed):
        super().__init__(seed)
        self.L, self.D, self.dual = 1.2, 0.65, False

"""Simple procedural warehouse assets the realizer can spawn (factory-shaped like Infinigen's: Cls(seed).spawn_asset(i)).

Cardboard boxes (one size per seed, per-box brown via Object Info random), wooden pallets (EUR 1.2 x 0.8 m: top boards, blocks,
bottom boards) and box piles (a few boxes stacked on a pallet footprint). Materials are plain Principled BSDFs, so the GT AOVs
(albedo / roughness / metallic) read straight from their inputs.
"""
from __future__ import annotations

import math
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
    return m


def cardboard():
    return _material("ir_cardboard", ((0.36, 0.22, 0.11), (0.52, 0.36, 0.2)), 0.85)


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
        return _boxes(f"PalletFactory({self.seed}).spawn_asset({i})", parts, pallet_wood())


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
def _flat(name, rgb, rough, metallic=0.0, transmission=0.0):
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    if transmission:
        b.inputs["Transmission Weight"].default_value = transmission
    return m


STYLE = {}                                                       # set by realize from the plan's venue style
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
    return o


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
                                                                             metallic=1.0 if self.top == "steel" else 0.0)
        body = [(0, 0, (H - 0.04) / 2, D, L, H - 0.04)]
        if self.slats:                                           # vertical slats proud of the front face (+x)
            n = int(L / 0.06)
            body += [(D / 2 + 0.008, -L / 2 + (k + 0.5) * L / n, (H - 0.04) / 2, 0.016, L / n * 0.6, H - 0.1) for k in range(n)]
        return _parts_object(f"CafeCounterFactory({i}).spawn_asset({i})",
                             [(front, body), (top, [(0.03, 0, H - 0.02, D + 0.06, L + 0.04, 0.04)])])


class CafeTableFactory:
    """Bistro table: round-ish (octagonal) or square top on a pedestal, 0.6-0.8 m, 0.75 m high."""
    def __init__(self, seed):
        r = random.Random(seed)
        self.w = r.uniform(0.6, 0.8); self.top = r.choice(("white_stone", "black_stone", "butcher_block"))

    def spawn_asset(self, i):
        w = self.w
        top = _flat(f"ir_counter_top_{self.top}", *COUNTER_TOPS[self.top]); metal = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0)
        return _parts_object(f"CafeTableFactory({i}).spawn_asset({i})",
                             [(top, [(0, 0, 0.74, w, w, 0.03)]),
                              (metal, [(0, 0, 0.37, 0.06, 0.06, 0.70), (0, 0, 0.01, 0.45, 0.06, 0.02), (0, 0, 0.01, 0.06, 0.45, 0.02)])])


class EspressoMachineFactory:
    """Two-group espresso machine (front +X): steel body, black top tray, two group heads, steam wand."""
    def __init__(self, seed):
        self.seed = seed

    def spawn_asset(self, i):
        steel = _flat("ir_steel", (0.62, 0.62, 0.64), 0.2, 1.0); black = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0)
        return _parts_object(f"EspressoMachineFactory({i}).spawn_asset({i})",
                             [(steel, [(0, 0, 0.21, 0.5, 0.7, 0.42), (0.27, -0.15, 0.22, 0.06, 0.08, 0.06), (0.27, 0.15, 0.22, 0.06, 0.08, 0.06)]),
                              (black, [(0, 0, 0.43, 0.48, 0.66, 0.02), (0.22, 0, 0.03, 0.08, 0.66, 0.06), (0.27, 0.3, 0.3, 0.02, 0.02, 0.2)])])


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
        return _parts_object(f"BackBarShelfFactory({i}).spawn_asset({i})",
                             [(wood, [(0, 0, z, D, L, 0.03) for z in zs]),
                              (metal, [(-D / 2 + 0.01, sx * (L / 2 - 0.03), 1.1, 0.02, 0.02, 2.2) for sx in (-1, 1)])])


class WindowBarFactory:
    """A ledge along shop-front glass (front +X): 0.4 m deep wooden top at 1.05 m on two steel legs, 1.6-3.0 m long."""
    def __init__(self, seed):
        self.L = random.Random(seed).uniform(1.6, 3.0)

    def spawn_asset(self, i):
        L = self.L
        wood = _flat("ir_counter_top_butcher_block", *COUNTER_TOPS["butcher_block"]); metal = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0)
        return _parts_object(f"WindowBarFactory({i}).spawn_asset({i})",
                             [(wood, [(0, 0, 1.03, 0.4, L, 0.04)]),
                              (metal, [(0, sx * (L / 2 - 0.15), 0.5, 0.04, 0.04, 1.0) for sx in (-1, 1)])])


# ---- retail -------------------------------------------------------------------------------------------------------------------------
HEADER_COLOURS = [(0.75, 0.08, 0.06), (0.05, 0.3, 0.6), (0.08, 0.45, 0.2), (0.85, 0.55, 0.05), (0.45, 0.1, 0.45)]


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
        parts += [(0, sy * (L / 2 - 0.02), H / 2, D, 0.04, H) for sy in (1, -1)]         # end uprights
        for sx in sides:
            x_mid = sx * D / 4 if self.double else 0.0
            depth = D / 2 - 0.03 if self.double else D - 0.05
            parts.append((x_mid, 0, 0.06, depth, L - 0.04, 0.12))                       # base deck
            for k in range(1, 5):
                z = 0.12 + k * (H - 0.2) / 4.6
                parts.append((x_mid, 0, z, depth, L - 0.04, 0.02))
                strips.append((x_mid + sx * depth / 2, 0, z - 0.01, 0.01, L - 0.06, 0.035))
        o = _parts_object(f"{type(self).__name__}({i}).spawn_asset({i})",
                          [(body, parts), (strip, strips), (head, [(0, L / 2 + 0.01, H + 0.14, D * 0.9, 0.02, 0.26)])])
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
        items = [(r.uniform(-0.12, 0.12), -0.3 + k * 0.12, z + 0.035, 0.09, 0.08, 0.05) for z in (0.03, 0.22) for k in range(6)]
        return _parts_object(f"PastryCaseFactory({i}).spawn_asset({i})",
                             [(base, [(0, 0, 0.015, 0.42, 0.78, 0.03), (0, 0, 0.21, 0.4, 0.76, 0.01)]), (pastry, items),
                              (glass, [(0.2, 0, 0.21, 0.01, 0.78, 0.4), (-0.2, 0, 0.21, 0.01, 0.78, 0.4), (0, 0.39, 0.21, 0.42, 0.01, 0.4),
                                       (0, -0.39, 0.21, 0.42, 0.01, 0.4), (0, 0, 0.41, 0.42, 0.78, 0.01)])])


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
    ("cyl", (cx, cy, cz), (r_bottom, r_top, h), (rx, ry, rz)); rotations in radians about the part's centre."""
    import bmesh
    from mathutils import Euler
    bm = bmesh.new()
    for slot, (mat, parts) in enumerate(groups):
        for kind, c, size, rot in parts:
            if kind == "box":
                r = bmesh.ops.create_cube(bm, size=1.0)
                bmesh.ops.scale(bm, vec=size, verts=r["verts"])
            else:
                r = bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=size[0], radius2=size[1], depth=size[2])
            bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Euler(rot).to_matrix(), verts=r["verts"])
            bmesh.ops.translate(bm, vec=c, verts=r["verts"])
            for f in {f for v in r["verts"] for f in v.link_faces}:
                f.material_index = slot
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for mat, _ in groups:
        me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


# ---- desk clutter (user 2026-10-16: 'the office is too clean, nobody's hands on it -- leftover snacks, books, pencils, cups') ------
_BRIGHT = ((0.75, 0.12, 0.1), (0.95, 0.65, 0.1), (0.1, 0.35, 0.7), (0.15, 0.55, 0.25), (0.85, 0.85, 0.82), (0.55, 0.15, 0.5))


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


class PantryRunFactory:
    """Office pantry (front +X): base cabinets + worktop with an inset sink and tap, upper cabinets at 1.45-2.15 m; 2.4-3.6 m long."""
    def __init__(self, seed):
        r = random.Random(seed)
        self.L = r.choice((2.4, 3.0, 3.6)); self.c = r.choice(((0.9, 0.9, 0.88), (0.35, 0.38, 0.4), (0.6, 0.48, 0.34)))

    def spawn_asset(self, i):
        L = self.L
        cab = _flat(f"ir_pantry_cab_{int(self.c[0] * 100)}", self.c, 0.45); top = _flat("ir_counter_top_white_stone", (0.86, 0.85, 0.82), 0.25)
        steel = _flat("ir_steel", (0.62, 0.62, 0.64), 0.2, 1.0); gap = _flat("ir_black_metal", (0.03, 0.03, 0.03), 0.4, 1.0)
        base = [(0, 0, 0.45, 0.6, L, 0.9)]
        doors = [(0.301, -L / 2 + (k + 0.5) * 0.6, 0.45, 0.002, 0.004, 0.8) for k in range(1, int(L / 0.6))]
        upper = [(-0.13, 0, 1.8, 0.34, L, 0.7)]
        sink_y = -L / 2 + 0.9
        return _parts_object(f"PantryRunFactory({i}).spawn_asset({i})",
                             [(cab, base + upper), (top, [(0.01, 0, 0.92, 0.62, L + 0.02, 0.04)]), (gap, doors),
                              (steel, [(0.02, sink_y, 0.945, 0.44, 0.56, 0.012), (-0.2, sink_y, 1.1, 0.04, 0.04, 0.32),
                                       (-0.1, sink_y, 1.25, 0.22, 0.035, 0.035)]),
                              (gap, [(0.02, sink_y, 0.95, 0.36, 0.48, 0.006)])])   # dark basin inside a raised rim: the sink reads (critic r2)


class ConferenceTableFactory:
    """Conference table (front +X): a 2.4-3.6 x 1.1-1.3 m top on two pedestal bases with a cable box in the middle."""
    def __init__(self, seed):
        r = random.Random(seed)
        self.L = r.choice((2.4, 3.0, 3.6)); self.W = r.uniform(1.1, 1.3)
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
        self.L = r.choice((1.4, 1.6, 1.8)); self.W = 0.8; self.H = 1.05   # high table for bar stools (critic r1+r2)
        self.top = r.choice(((0.92, 0.92, 0.9), (0.15, 0.15, 0.15), (0.62, 0.5, 0.36)))


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

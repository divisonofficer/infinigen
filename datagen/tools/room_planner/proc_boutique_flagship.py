"""Props for the large flagship boutique (reference set boutique_large_flagship_01, 2026-10-17). Factory-shaped like proc_assets:
Cls(seed).spawn_asset(i), front +X, origin at the bottom centre (wall items: back at x = 0, origin at the bottom, mount z by the caller).

  StoneSlabTableFactory     tables built from stacked rough-cut limestone slabs (hero object of the reference): 3 blocks x ~12 layers
  WallRailFlatFactory       wall-mounted flat-bar garment rail on brackets (mount at ~1.65 m)
  SteelLatticeScreenFactory a free-standing rusted steel grid with dark shaggy fabric swatches

Poly budget: table ~0.4k tris, rail ~0.1k, screen ~5.5k (3 layers per swatch). `mesh_object` builds one mesh per object (boxes and cylinders in one pass).
`stone` is a scan kind the library lacks: concrete scans stand in for it until a stone scan exists (registered on proc_assets.SCANS).
"""
from __future__ import annotations

import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector


def _pa():
    from room_planner import proc_assets
    return proc_assets


def mesh_object(name, groups, bevel=True):
    """One object, one slot per group: groups = [(material, [prim, ...])], prim = ("box", cx, cy, cz, sx, sy, sz[, yaw]) or
    ("cyl", (x0, y0, z0), (x1, y1, z1), radius, segments)."""
    pa = _pa()
    bm = bmesh.new(); bm.loops.layers.uv.verify()
    for slot, (mat, prims) in enumerate(groups):
        for p in prims:
            if p[0] == "box":
                _, cx, cy, cz, sx, sy, sz, *yaw = p
                r = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)
                bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=r["verts"]); pa._face_uvs(bm, r["verts"])
                if yaw and yaw[0]:
                    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(yaw[0], 3, "Z"), verts=r["verts"])
                mid = (cx, cy, cz)
            elif p[0] == "jbox":                                   # a rough-cut block: every corner moved a little, sometimes a chipped top corner
                _, cx, cy, cz, sx, sy, sz, jit, chip, seed = p
                jr = random.Random(seed)
                r = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)
                bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=r["verts"]); pa._face_uvs(bm, r["verts"])
                top = [v for v in r["verts"] if v.co.z > 0]
                for v in r["verts"]:
                    v.co.x += jr.uniform(-jit, jit); v.co.y += jr.uniform(-jit, jit); v.co.z += jr.uniform(-jit, jit) * 0.15
                if jr.random() < chip and top:                     # bevel chip: one top corner knocked down and in
                    v = jr.choice(top); v.co.z -= jr.uniform(0.012, 0.032); v.co.x -= math.copysign(jr.uniform(0.008, 0.02), v.co.x); v.co.y -= math.copysign(jr.uniform(0.008, 0.02), v.co.y)
                mid = (cx, cy, cz)
            else:
                _, p0, p1, rad, n = p
                v = Vector(p1) - Vector(p0)
                r = bmesh.ops.create_cone(bm, cap_ends=True, segments=n, radius1=rad, radius2=rad, depth=v.length, calc_uvs=True)
                bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Vector((0, 0, 1)).rotation_difference(v.normalized()).to_matrix(), verts=r["verts"])
                mid = (Vector(p0) + Vector(p1)) / 2
            bmesh.ops.translate(bm, vec=tuple(mid), verts=r["verts"])
            for f in {f for vv in r["verts"] for f in vv.link_faces}:
                f.material_index = slot
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for mat, _ in groups:
        me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    if bevel:
        pa._bevel(o)
    return o


def _flat(name, rgb, rough, metallic=0.0, kind=None):
    """proc_assets._flat; `kind` is passed only where _flat takes it (material_spec wired), else the legacy name rules apply."""
    pa = _pa()
    pa.SCANS.setdefault("stone", (pa._TC + "concrete_0003", pa._TC + "concrete_0004"))
    pa.SCAN_TILE.setdefault("stone", 0.6)
    if kind:
        try:
            return pa._flat(name, rgb, rough, metallic, 0.0, False, kind=kind)
        except TypeError:
            pass
    return pa._flat(name, rgb, rough, metallic)


class StoneSlabTableFactory:
    """Display table of stacked rough-cut slabs (front +X): L x D x H = 1.8-2.6 x 1.0-1.2 x 0.75-0.8 m, split into 2-3 blocks 1 cm
    apart, ~12 layers per block, each layer jittered a little in plan and thickness; a lighter dressed top."""
    def __init__(self, seed):
        r = random.Random(seed)
        self.L = r.choice((1.8, 2.2, 2.6)); self.D = r.choice((1.0, 1.2)); self.H = r.choice((0.75, 0.8))
        self.blocks = r.choice((2, 3)); self.seed = seed

    def spawn_asset(self, i):
        r = random.Random(self.seed * 7 + i)
        side = _flat("ir_slab_stone", (0.15, 0.16, 0.18), 0.8, kind="stone")
        top = _flat("ir_slab_top", (0.3, 0.31, 0.32), 0.55, kind="stone")
        n = max(8, int(self.H / 0.064)); t = (self.H - 0.04) / n
        bl = (self.L - 0.01 * (self.blocks - 1)) / self.blocks
        sides, tops = [], []
        for b in range(self.blocks):
            cy = -self.L / 2 + bl / 2 + b * (bl + 0.01)
            for k in range(n):
                tk = t * r.uniform(0.88, 1.08)
                sides.append(("jbox", r.uniform(-0.02, 0.02), cy + r.uniform(-0.015, 0.015), 0.02 + k * t + tk / 2,
                              self.D - r.uniform(0, 0.05), bl - r.uniform(0, 0.04), tk, 0.012, 0.18, r.randrange(1 << 30)))
            tops.append(("jbox", 0, cy, self.H - 0.02, self.D + 0.02, bl + 0.01, 0.04, 0.006, 0.35, r.randrange(1 << 30)))
        return mesh_object(f"StoneSlabTableFactory({self.seed}).spawn_asset({i})", [(side, sides), (top, tops)])


class WallRailFlatFactory:
    """Wall garment rail (front +X, back at x = 0, origin at the bottom of the bar; mount ~1.65 m): a 40 mm flat bar 0.16 m off the wall
    on brackets every ~1.2 m, blackened steel."""
    def __init__(self, seed):
        self.L = random.Random(seed).choice((2.4, 3.0, 3.6)); self.seed = seed

    def spawn_asset(self, i):
        steel = _flat("ir_rail_steel", (0.11, 0.1, 0.09), 0.5, 0.9)
        L, off = self.L, 0.16
        nb = max(2, round(L / 1.2) + 1)
        prims = [("box", off, 0, 0.02, 0.008, L, 0.04)]
        for k in range(nb):
            y = -L / 2 + 0.05 + k * (L - 0.1) / (nb - 1)
            prims += [("box", 0.004, y, 0.02, 0.008, 0.05, 0.1), ("box", off / 2, y, 0.012, off, 0.018, 0.024)]
        return mesh_object(f"WallRailFlatFactory({self.seed}).spawn_asset({i})", [(steel, prims)])


class SteelLatticeScreenFactory:
    """Free-standing rusted steel grid screen (front +X, thin in x): 1.6-2.2 m wide x 2.6 m tall, 0.2 m pitch, a dark shaggy fabric swatch
    hung in most cells, two floor feet."""
    def __init__(self, seed):
        self.W = random.Random(seed).choice((1.6, 1.9, 2.2)); self.H = 2.6; self.seed = seed

    def spawn_asset(self, i):
        r = random.Random(self.seed * 11 + i)
        rust = _flat("ir_lattice_rust", (0.27, 0.13, 0.07), 0.65, 0.8)
        fabs = [_flat(f"ir_lattice_fabric_{k}", c, 0.95) for k, c in enumerate(((0.07, 0.06, 0.055), (0.12, 0.095, 0.075), (0.045, 0.045, 0.05)))]
        W, H, bar = self.W, self.H, 0.03
        nx, nz = max(4, round(W / 0.2)), round(H / 0.2)
        px, pz = W / nx, H / nz
        bars = [("box", 0, 0, 0.03 + H / 2, bar, bar, H + 0.04)] * 0 + \
               [("box", 0, -W / 2 + k * px, 0.05 + H / 2, bar, bar, H) for k in range(nx + 1)] + \
               [("box", 0.012, 0, 0.05 + k * pz, bar, W + bar, bar) for k in range(nz + 1)]
        bars += [("box", 0, s * (W / 2 - 0.05), 0.02, 0.05, 0.05, 0.04) for s in (1, -1)]
        feet = [("box", 0, s * (W / 2 - 0.05), 0.02, 0.45, 0.04, 0.04) for s in (1, -1)]
        swatches = [[], [], []]                                    # three dark browns / blacks; each swatch is 3 slightly rotated layers (ragged, fibrous edge)
        for a in range(nx):
            for b in range(nz):
                g = r.randrange(3)
                for layer in range(3):
                    swatches[g].append(("box", 0.02 + 0.004 * layer, -W / 2 + (a + 0.5) * px + r.uniform(-0.006, 0.006),
                                        0.05 + (b + 0.5) * pz + r.uniform(-0.006, 0.006), 0.012, px * r.uniform(0.66, 0.86),
                                        pz * r.uniform(0.66, 0.9), r.uniform(-0.18, 0.18)))
        return mesh_object(f"SteelLatticeScreenFactory({self.seed}).spawn_asset({i})", [(rust, bars + feet)] + [(f, sw) for f, sw in zip(fabs, swatches)], bevel=False)

"""Octagonal domed rotunda shell for the science-museum scene (docs/space_museum_design_proposal.md). Infinigen rooms are rectangles, so the rotunda is built INSIDE the
room as new meshes and the room's own ceiling is removed:

    shell_services(L, S, zc, at, name, rng, stats, room=None)      called by architecture_pass.build() when the archetype has museum=1

  * 8 travertine wall panels (octagon, circumradius R = min(L, S) / 2 - 0.35) up to z_cornice = 0.62 zc, each with a hexagonal dark grille window, pilasters at the
    8 corners and a gilt cornice ring
  * a frieze band (8 panels, generated abstract art frieze_0..7.png) from z_cornice to 0.8 zc
  * a dome: 8 sectors x 12 rings rising from 0.8 zc to zc, textured with the generated fresco (fresco_dome.png), with a central oculus (circle hole, a brass ring) and
    an emissive warm cove ring at the base of the dome
  * a circular floor opening: the floor is NOT cut (it is the room floor); a RotundaRail ring is placed by the layout around the opening position at the centre
The room's `.ceiling` object is removed; the museum art images come from data/venue_refs/museum_art (gen_museum_art.py).
"""
from __future__ import annotations

import math
from pathlib import Path

import bmesh
import bpy

from room_planner import proc_boutique_flagship as fl

ART = Path("/jarvis/project/robomituba/data/venue_refs/museum_art")


def _img_mat(name, file, rough=0.7, emit=0.0):
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(str(ART / file), check_existing=True)
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = rough
    if emit:
        nt.links.new(t.outputs["Color"], b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = emit
    return m


def _travertine():
    """Pale travertine: the name carries 'travertine', so proc_assets maps it to the 'stone' scan (marble_0011 / rock_0005 / granite)."""
    return fl._flat("ir_mu_travertine", (0.82, 0.76, 0.63), 0.35)


def _mesh(name, bm, mats):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    return o


def _quad(bm, uv, pts, uvs, mat_index=0):
    f = bm.faces.new([bm.verts.new(p) for p in pts]); f.material_index = mat_index
    for lp, c in zip(f.loops, uvs):
        lp[uv].uv = c
    return f


def shell_services(L, S, zc, at, name, rng, stats, room=None):
    cv = S / 2
    from room_planner.museum_layout import rotunda_radius
    R = rotunda_radius(L, S)
    cu = R + 0.35                                                                  # the rotunda sits at the entrance end; cv stays mid-width
    zc_ = max(zc, 4.0)
    zc1, zf0, zf1, zd = 0.62 * zc_, 0.62 * zc_, 0.8 * zc_, zc_
    ang = [math.pi / 8 + k * math.pi / 4 for k in range(8)]                          # 8 corners of the octagon (flat faces toward the axes)
    P = [(cu + R * math.cos(a), cv + R * math.sin(a)) for a in ang]
    W = lambda u, v, z: (*at(u, v), z)
    if room:
        ce = bpy.data.objects.get(f"{room}.ceiling")
        if ce is not None:
            bpy.data.objects.remove(ce, do_unlink=True)
    trav, gilt = _travertine(), fl._flat("ir_mu_gilt_cornice", (0.8, 0.62, 0.25), 0.3, 1.0)
    grille = fl._flat("ir_mu_grille", (0.07, 0.05, 0.04), 0.5, 0.6)
    # ---- walls + pilasters + cornice ----
    bm = bmesh.new(); uv = bm.loops.layers.uv.verify()
    for k in range(8):
        (u0, v0), (u1, v1) = P[k], P[(k + 1) % 8]
        _quad(bm, uv, (W(u0, v0, 0), W(u1, v1, 0), W(u1, v1, zc1), W(u0, v0, zc1)), ((0, 0), (1, 0), (1, 1), (0, 1)))
        for (ua, va) in ((u0, v0),):                                                    # pilaster at each corner: a slim box
            pass
    fl_parts = []
    for k in range(8):
        u, v = P[k]
        fl_parts.append(("box", *at(u, v), zc1 / 2, 0.5, 0.5, zc1))
    wall = _mesh(name("RotundaWalls"), bm, [trav])
    fl.mesh_object(name("RotundaPilasters"), [(trav, fl_parts)], bevel=False)
    # cornice ring (gilt) and grille windows
    ring, win = [], []
    for k in range(8):
        (u0, v0), (u1, v1) = P[k], P[(k + 1) % 8]
        um, vm = (u0 + u1) / 2, (v0 + v1) / 2; yaw = math.atan2(v1 - v0, u1 - u0)
        ring.append(("cyl", W(u0, v0, zc1 + 0.04), W(u1, v1, zc1 + 0.04), 0.06, 8))
        ring.append(("cyl", W(u0, v0, zf1 + 0.04), W(u1, v1, zf1 + 0.04), 0.07, 8))
        wx, wy = at(um + (cu - um) * 0.03, vm + (cv - vm) * 0.03)
        win.append(("box", wx, wy, 0.58 * zc1, 0.05, 0.55, 0.9, yaw + math.pi / 2))
    fl.mesh_object(name("RotundaCornice"), [(gilt, ring)], bevel=False)
    fl.mesh_object(name("RotundaGrilles"), [(grille, win)], bevel=False)
    # ---- frieze band: 8 panels, one generated image each ----
    for k in range(8):
        (u0, v0), (u1, v1) = P[k], P[(k + 1) % 8]
        bm = bmesh.new(); uv = bm.loops.layers.uv.verify()
        _quad(bm, uv, (W(u0, v0, zf0 + 0.08), W(u1, v1, zf0 + 0.08), W(u1, v1, zf1), W(u0, v0, zf1)), ((0, 0), (1, 0), (1, 1), (0, 1)))
        _mesh(name("FriezePanel"), bm, [_img_mat(f"ir_mu_frieze_{k % 8}", f"frieze_{k % 8}.png", 0.6)])
    # ---- dome: 8 sectors x 12 rings between the frieze top and the crown, textured with the fresco ----
    rings = 12; R0 = R * 0.97
    bm = bmesh.new(); uv = bm.loops.layers.uv.verify()
    def pt(k, j):
        t = j / rings; z = zf1 + (zd - zf1) * math.sin(t * math.pi / 2 * 0.98)
        r = R0 * math.cos(t * math.pi / 2 * 0.98) * (1 - 0.0) + 0.001
        a = k * math.pi / 4 * 1.0 + math.pi / 8
        return (cu + r * math.cos(a), cv + r * math.sin(a), z), (k / 8 * 8, 1 - t)
    seg = 32; a_of = lambda s: 2 * math.pi * s / seg
    for s in range(seg):
        for j in range(rings):
            def vtx(ss, jj):
                t = jj / rings; r = R0 * math.cos(t * math.pi / 2 * 0.97) + 0.45 * (jj == rings) ; z = zf1 + (zd - zf1) * math.sin(t * math.pi / 2 * 0.97)
                return (*at(cu + max(r, 0.45) * math.cos(a_of(ss)), cv + max(r, 0.45) * math.sin(a_of(ss))), z)
            _quad(bm, uv, (vtx(s, j), vtx(s + 1, j), vtx(s + 1, j + 1), vtx(s, j + 1)), ((s / seg, j / rings), ((s + 1) / seg, j / rings), ((s + 1) / seg, (j + 1) / rings), (s / seg, (j + 1) / rings)))
    for f in bm.faces:
        f.normal_flip()                                                                  # faces point inward (down into the hall)
    _mesh(name("RotundaDome"), bm, [_img_mat("ir_mu_fresco", "fresco_dome.png", 0.75, 0.35)])
    # ---- warm cove ring at the dome base and a brass oculus ring ----
    glow = bpy.data.materials.get("ir_mu_cove_glow") or bpy.data.materials.new("ir_mu_cove_glow")
    glow.use_nodes = True; b = glow.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (1.0, 0.8, 0.5, 1); b.inputs["Emission Color"].default_value = (1.0, 0.78, 0.45, 1); b.inputs["Emission Strength"].default_value = 7.0
    cov = [("cyl", W(P[k][0] + (cu - P[k][0]) * 0.015, P[k][1] + (cv - P[k][1]) * 0.015, zf1 + 0.1), W(P[(k + 1) % 8][0] + (cu - P[(k + 1) % 8][0]) * 0.015, P[(k + 1) % 8][1] + (cv - P[(k + 1) % 8][1]) * 0.015, zf1 + 0.1), 0.05, 8) for k in range(8)]
    fl.mesh_object(name("DomeCove"), [(glow, cov)], bevel=False)
    for k in range(6):                                                                   # soft lights up in the dome: the fresco is lit by its cove
        a = k * math.pi / 3; x, y = at(cu + 0.7 * R * math.cos(a), cv + 0.7 * R * math.sin(a))
        ld = bpy.data.lights.new(f"ir_mu_dome_{k}", "AREA"); ld.shape = "RECTANGLE"; ld.size = 1.6; ld.size_y = 1.6; ld.energy = 45.0; ld.color = (1.0, 0.82, 0.6)
        lo = bpy.data.objects.new(f"PointLampFactory(dome).spawn_asset(mu_{k})", ld); bpy.context.scene.collection.objects.link(lo)
        lo.location = (x, y, zf1 + 0.5); lo.rotation_euler = (0, 0, 0)
    # soft lights over the exhibit / video strip beyond the rotunda (the room's own ceiling light is gone with the ceiling)
    n_u = max(2, int((L - 2 * R - 0.7) // 3.5))
    for iu in range(n_u):
        for iv in range(2):
            u = 2 * R + 0.7 + (iu + 0.5) * (L - 2 * R - 0.7) / n_u; v = S * (0.3 + 0.4 * iv)
            x, y = at(u, v)
            ld = bpy.data.lights.new(f"ir_mu_strip_{iu}_{iv}", "AREA"); ld.shape = "RECTANGLE"; ld.size = 2.0; ld.size_y = 2.0; ld.energy = 700.0; ld.color = (1.0, 0.88, 0.7)
            lo = bpy.data.objects.new(f"PointLampFactory(strip).spawn_asset(mu_{iu}_{iv})", ld); bpy.context.scene.collection.objects.link(lo)
            lo.location = (x, y, 3.8)
    # exhibit / video strip walls: gilt cornice, painted frieze (the rotunda's frieze art), pilasters every 4 m; side walls v = 0 and v = S, end wall u = L
    u0 = 2 * R + 0.4; zc0, zf = 3.3, 4.5
    walls = [((u0, 0.03), (L - 0.03, 0.03)), ((u0, S - 0.03), (L - 0.03, S - 0.03)), ((L - 0.03, 0.03), (L - 0.03, S - 0.03))]
    cor, pil = [], []
    for wi, ((ua, va), (ub, vb)) in enumerate(walls):
        cor += [("cyl", W(ua, va, zc0), W(ub, vb, zc0), 0.06, 8), ("cyl", W(ua, va, zf), W(ub, vb, zf), 0.05, 8)]
        n = max(1, int(math.hypot(ub - ua, vb - va) // 2.5))
        for k in range(n):                                               # one frieze panel per ~2.5 m
            t0, t1 = k / n, (k + 1) / n
            p0, p1 = (ua + (ub - ua) * t0, va + (vb - va) * t0), (ua + (ub - ua) * t1, va + (vb - va) * t1)
            bm = bmesh.new(); uv = bm.loops.layers.uv.verify()
            _quad(bm, uv, (W(*p0, zc0 + 0.08), W(*p1, zc0 + 0.08), W(*p1, zf - 0.07), W(*p0, zf - 0.07)), ((0, 0), (1, 0), (1, 1), (0, 1)))
            _mesh(name("StripFrieze"), bm, [_img_mat(f"ir_mu_frieze_{(wi * 3 + k) % 8}", f"frieze_{(wi * 3 + k) % 8}.png", 0.6)])
        for k in range(int(math.hypot(ub - ua, vb - va) // 4) + 1):
            t = min(1.0, k * 4.0 / max(1e-6, math.hypot(ub - ua, vb - va)))
            pu, pv = ua + (ub - ua) * t, va + (vb - va) * t
            pil.append(("box", *at(pu, pv), (1.95 + zf) / 2, 0.4, 0.4, zf - 1.95))      # starts above 1.95 m: furnish_rooms.obstacles() ignores anything that high, so wall pieces still fit under them
    fl.mesh_object(name("StripCornice"), [(gilt, cor)], bevel=False)
    fl.mesh_object(name("StripPilasters"), [(trav, pil)], bevel=False)
    stats["museum_shell"] = {"R": round(R, 2), "z": round(zc_, 1), "center": [round(cu, 2), round(cv, 2)]}

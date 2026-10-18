"""Post-realize wall finishing (hooked from kit_lighting, before architecture_textures):

    import late_walls; stats["late_walls"] = late_walls.apply(plans)

  * ROOM_BIGGLASS set: room_planner.big_glass.sweep(): wall-mounted items placed after the architecture pass that float in the glass opening are deleted
  * ROOM_TILE_WALL=<object prefix> (e.g. BackBarShelfFactory, which stands flush on its wall; CafeCounterFactory also works when the counter is near its back wall): white square tile on the wall behind it; ROOM_SMOOTH_FLOOR=1: one smooth light floor finish from the kit's floor_rgb;
    ROOM_WHITE_CEILING=1: grid removed + white ceiling; ROOM_FLAT_WALLS=1: every wall slot one plain paint from style_spec.wall_rgb (35% toward white)
  * ROOM_FEATURE_WALL=1 and style_spec['feature_rgb'] (linear): paint the wall BEHIND the exam table (the room wall plane facing the table on the side its back points to,
    nearest to it, >= 3 m2) in that colour -- exam-room S18's pale-blue accent wall. Plain Principled paint, so albedo/roughness GT read normally.
"""
from __future__ import annotations

import os

import bpy
from mathutils import Vector


def _room_of(o):
    return o.name.rsplit(".", 1)[0]


def paint_behind(prefix, mat):
    """Paint the room-wall plane behind the first object named <prefix>* in each room (its back = -front, front = +X) with `mat`; returns faces painted."""
    done = 0
    walls = [o for o in bpy.data.objects if o.type == "MESH" and o.name.endswith(".wall") and o.parent is None]
    for w in walls:
        pts = [w.matrix_world @ Vector(c) for c in w.bound_box]
        lo = Vector((min(p.x for p in pts), min(p.y for p in pts), 0)); hi = Vector((max(p.x for p in pts), max(p.y for p in pts), 0))
        tab = next((o for o in bpy.data.objects if o.name.startswith(prefix) and lo.x - 0.3 < o.matrix_world.translation.x < hi.x + 0.3
                    and lo.y - 0.3 < o.matrix_world.translation.y < hi.y + 0.3), None)
        if tab is None:
            continue
        T = tab.matrix_world.translation.copy(); T.z = 0
        back = -(tab.matrix_world.to_3x3() @ Vector((1, 0, 0))); back.z = 0; back.normalize()          # the factory's front is +X, the head end/back is -X
        mw3 = w.matrix_world.to_3x3(); groups = {}
        for p in w.data.polygons:
            n = (mw3 @ p.normal).normalized()
            if abs(n.z) > 0.2 or n.dot(back) > -0.7:                                                     # a vertical face looking back toward the table
                continue
            c = w.matrix_world @ p.center; dist = (c - T).dot(back)
            if dist < 0.05:
                continue
            groups.setdefault((round(n.x, 1), round(n.y, 1), round(c.dot(n), 1)), []).append((p.index, p.area, dist))
        cand = [(sum(d for _, _, d in g) / len(g), g) for g in groups.values() if sum(a for _, a, _ in g) >= 3.0]
        if not cand:
            continue
        faces = min(cand, key=lambda t: t[0])[1]
        if mat.name not in [m.name for m in w.data.materials if m]:
            w.data.materials.append(mat)
        idx = [m.name if m else "" for m in w.data.materials].index(mat.name)
        for i, _, _ in faces:
            w.data.polygons[i].material_index = idx
        done += len(faces)
    return done


def _paint_mat(rgb):
    mat = bpy.data.materials.get("ir_late_feature_wall") or bpy.data.materials.new("ir_late_feature_wall")
    mat.use_nodes = True; b = mat.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = 0.8
    b["weathered"] = True
    return mat


def _tile_mat(tile=0.125):
    """White square wall tile: a brick texture with square cells on (distance along the wall, z), grey grout."""
    mat = bpy.data.materials.get("ir_late_white_tile")
    if mat is not None:
        return mat
    mat = bpy.data.materials.new("ir_late_white_tile"); mat.use_nodes = True; N, L = mat.node_tree.nodes, mat.node_tree.links; b = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
    s1 = N.new("ShaderNodeMath"); s1.operation = "ADD"; L.new(sep.outputs["X"], s1.inputs[0]); L.new(sep.outputs["Y"], s1.inputs[1])   # x + y: a vertical wall varies along only one of them
    cb = N.new("ShaderNodeCombineXYZ"); L.new(s1.outputs["Value"], cb.inputs["X"]); L.new(sep.outputs["Z"], cb.inputs["Y"])
    br = N.new("ShaderNodeTexBrick"); br.offset = 0.0; br.squash = 1.0
    br.inputs["Scale"].default_value = 1.0 / tile; br.inputs["Mortar Size"].default_value = 0.012; br.inputs["Brick Width"].default_value = 1.0; br.inputs["Row Height"].default_value = 1.0
    br.inputs["Color1"].default_value = (0.93, 0.93, 0.91, 1); br.inputs["Color2"].default_value = (0.9, 0.9, 0.88, 1); br.inputs["Mortar"].default_value = (0.62, 0.62, 0.6, 1)
    L.new(cb.outputs["Vector"], br.inputs["Vector"]); L.new(br.outputs["Color"], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.25
    b["weathered"] = True
    return mat


def smooth_floor(rgb, rough=0.3):
    """Replace every room floor's materials with one plain, smooth, light Principled finish (not weathered): the pale seamless vinyl / polished concrete of the refs."""
    mat = bpy.data.materials.get("ir_late_floor_smooth") or bpy.data.materials.new("ir_late_floor_smooth")
    mat.use_nodes = True; b = mat.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough; b["weathered"] = True
    n = 0
    for o in bpy.data.objects:
        if o.type == "MESH" and o.name.endswith(".floor") and o.parent is None:
            for sl in o.material_slots:
                sl.material = mat
            n += 1
    return n


def white_ceiling(rgb=(0.9, 0.9, 0.88)):
    """Light ceiling grid and tiles: the dark grey T-bars (0.62 metallic) and the dim plaster read as a dark ceiling in a bright daylit clinic."""
    n = 0
    for o in list(bpy.data.objects):                                        # the raised 2 cm T-bars read as an exposed grid in a clinic: plain flat tiles instead
        if o.name.startswith("CeilingGridFactory"):
            bpy.data.objects.remove(o, do_unlink=True); n += 1
    for m in bpy.data.materials:
        if m.use_nodes and m.name in ("ir_tbar",) and "Principled BSDF" in m.node_tree.nodes:
            b = m.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Metallic"].default_value = 0.0; n += 1
    for o in bpy.data.objects:
        if o.type == "MESH" and o.name.endswith(".ceiling"):
            mat = bpy.data.materials.get("ir_late_ceiling") or bpy.data.materials.new("ir_late_ceiling"); mat.use_nodes = True
            b = mat.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = 0.7; b["weathered"] = True
            for sl in o.material_slots:
                sl.material = mat
            n += 1
    return n


def flat_walls(rgb):
    """Every room wall slot -> one plain paint (no scan mottling); the painted accent faces of this module keep their own material."""
    mat = bpy.data.materials.get("ir_late_wall_flat") or bpy.data.materials.new("ir_late_wall_flat")
    mat.use_nodes = True; b = mat.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = 0.75; b["weathered"] = True
    n = 0
    for o in bpy.data.objects:
        if o.type == "MESH" and o.name.endswith(".wall") and o.parent is None:
            for sl in o.material_slots:
                if sl.material and not sl.material.name.startswith("ir_late_"):
                    sl.material = mat; n += 1
    return n


def dental_light():
    """A ceiling-mounted operatory light (generated prop DentalCeilingLight) over every DentalChairFactory: the head hangs 0.9 m along the arm direction, so the plate sits
    0.9 m to the chair's -local-Y side at the ceiling and the lamp ends over the chair."""
    from room_planner import proc_generated
    n = 0
    for ch in [o for o in bpy.data.objects if o.name.startswith("DentalChairFactory") and o.parent is None]:
        walls = [w for w in bpy.data.objects if w.type == "MESH" and w.name.endswith(".wall") and w.parent is None]
        zc = max((max((w.matrix_world @ Vector(c)).z for c in w.bound_box) for w in walls), default=2.7)
        side = ch.matrix_world.to_3x3() @ Vector((0, 1, 0)); side.z = 0; side.normalize()
        lamp = proc_generated.DentalCeilingLightFactory(1).spawn_asset(0)
        lamp.rotation_mode = "XYZ"; lamp.rotation_euler = (0, 0, ch.matrix_world.to_euler().z)         # the arm runs along the chair's +Y
        c = ch.matrix_world.translation
        lamp.location = (c.x - side.x * 0.9, c.y - side.y * 0.9, zc); n += 1
    return n


def apply(plans):
    out = {}
    if os.environ.get("ROOM_BIGGLASS"):
        from room_planner import big_glass
        out["bigglass_swept"] = big_glass.sweep()
    rgb = (plans.get("style_spec") or {}).get("feature_rgb")
    if os.environ.get("ROOM_FEATURE_WALL") == "1" and rgb:
        out["feature_wall_faces"] = paint_behind("ExamTableFactory", _paint_mat(rgb))
    if os.environ.get("ROOM_TILE_WALL"):                                    # e.g. CafeCounterFactory: white square tile on the wall behind the counter
        out["tile_wall_faces"] = paint_behind(os.environ["ROOM_TILE_WALL"], _tile_mat())
    st = plans.get("style_spec") or {}
    if os.environ.get("ROOM_SMOOTH_FLOOR") == "1" and st.get("floor_rgb"):
        out["smooth_floor"] = smooth_floor([min(1.0, c * 1.1) for c in st["floor_rgb"]])
    if os.environ.get("ROOM_FLAT_WALLS") == "1" and st.get("wall_rgb"):
        out["flat_walls"] = flat_walls([min(1.0, c + (1.0 - c) * 0.35) for c in st["wall_rgb"]])
    if os.environ.get("ROOM_DENTAL_LIGHT") == "1":
        out["dental_lights"] = dental_light()
    if os.environ.get("ROOM_WHITE_CEILING") == "1":
        out["white_ceiling"] = white_ceiling()
    return out

"""Scanned texturecan PBR on the big surfaces (user 2026-10-17: 'for walls, don't weather the smooth material -- use the high-resolution
texture library, or Infinigen 2.0 with a light weathering mixed in').

Infinigen 2.0's `paint` group is a flat constant (bump 0.001-0.004 m): every wall and many floors rendered as one smooth value. For each
room shell `<room>.wall` / `<room>.floor` whose slot uses a `paint` group this builds a material from a 2k texturecan set (base colour,
roughness, GL normal; box-projected in object space at the set's physical size):
  walls   the set's luminance variation (55 %) multiplies the paint's own colour, so the style's palette survives; roughness keeps the
          paint's mean; normal map on
  floors  the set's own colour and maps, picked by venue (carpet / polished concrete in offices, light vinyl-look tile in clinics, wood in
          cafés, tile or concrete in shops, concrete in warehouses)
Materials that are not `paint` (restroom tile, brick, wood-plank feature walls) stay Infinigen 2.0's. Ceilings and restrooms are untouched.
The new materials are flagged `ir_arch`: weather_pass applies only a light (30 %) wear to them.

    from architecture_textures import apply; apply(room_venues, style_venue)
"""
import json
import re
import zlib
from pathlib import Path

import bpy

CAT = Path("/jarvis/project/robomituba/data/venue_refs/arch_textures/catalog.json")
WALL = ("concrete_0016", "concrete_0017", "concrete_0019", "concrete_0032", "concrete_0018")   # plain plaster-like sets only: 0009 / 0008 carry formwork
# panel seams and tie holes (a clinic hallway wall in D3 r24 test), 0028 white speckles, 0023 horizontal brushing
FLOOR_POOLS = {"carpet": ("fabrics_0076", "fabric_0022"), "polished": ("concrete_0019", "concrete_0032", "concrete_0018"),
               "clinic": ("tiles_0086", "tiles_0042", "concrete_0016"), "shop": ("tiles_0121", "tiles_0086", "concrete_0032"),
               "work": ("concrete_0018", "concrete_0010", "concrete_0023")}
CLINIC = {"clinic-reception", "exam-room", "dental-room", "physio-room", "pharmacy"}
SHOP = {"convenience", "grocery", "boutique"}
WORKROOMS = {"warehouse", "garage", "utility"}
SKIP_ROOMS = {"restroom", "bathroom"}
_cat = None


def catalog():
    global _cat
    if _cat is None:
        _cat = {("texturecan_" + x["id"].replace("texturecan_", "")): x for x in json.loads(CAT.read_text())}
    return _cat


def tex(short):
    return catalog().get("texturecan_" + short)


def wood_floors():
    return sorted(k for k, x in catalog().items() if x["category"] == "wood" and "floor" in x["roles"] and 0.2 < x["lum"] < 0.6 and x["sat"] < 0.6)


def _h(*parts):
    return zlib.crc32("|".join(map(str, parts)).encode())


def make_material(name, t, tint=None, rough0=0.5, contrast=0.55):
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N, L = nt.nodes, nt.links; b = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping"); s = 1.0 / max(t["size_m"], 0.2)
    mp.inputs["Scale"].default_value = (s, s, s); L.new(tc.outputs["Object"], mp.inputs["Vector"])

    def img(key, color):
        n = N.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(t["maps"][key], check_existing=True)
        n.image.colorspace_settings.name = "sRGB" if color else "Non-Color"
        n.projection = "BOX"; n.projection_blend = 0.25; L.new(mp.outputs["Vector"], n.inputs["Vector"]); return n
    bc = img("base_color", True)
    if tint is None:
        L.new(bc.outputs["Color"], b.inputs["Base Color"])
    else:                                                       # the paint's colour carries the hue, the scan its variation (mean 1)
        bw = N.new("ShaderNodeRGBToBW"); L.new(bc.outputs["Color"], bw.inputs["Color"])
        k = N.new("ShaderNodeMath"); k.operation = "MULTIPLY_ADD"; k.inputs[1].default_value = contrast / max(t["lum"], 1e-3)
        k.inputs[2].default_value = 1.0 - contrast; L.new(bw.outputs["Val"], k.inputs[0])
        cc = N.new("ShaderNodeCombineColor"); [L.new(k.outputs["Value"], cc.inputs[i]) for i in range(3)]
        mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"; mix.inputs["Factor"].default_value = 1.0
        mix.inputs[6].default_value = (*tint[:3], 1.0); L.new(cc.outputs["Color"], mix.inputs[7]); L.new(mix.outputs[2], b.inputs["Base Color"])
    rt = img("roughness", False)
    r = N.new("ShaderNodeMath"); r.operation = "MULTIPLY"; r.use_clamp = True
    r.inputs[1].default_value = max(0.5, min(1.7, rough0 / max(t["rough"], 0.05))); L.new(rt.outputs["Color"], r.inputs[0]); L.new(r.outputs["Value"], b.inputs["Roughness"])
    nm = img("normal_gl", False); nn = N.new("ShaderNodeNormalMap"); nn.inputs["Strength"].default_value = 0.8
    L.new(nm.outputs["Color"], nn.inputs["Color"]); L.new(nn.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Specular IOR Level"].default_value = 0.4
    b["ir_arch"] = True
    return m


def _paint_group(m):
    return next((x for x in m.node_tree.nodes if x.type == "GROUP" and x.node_tree and x.node_tree.name.startswith("paint")), None) if m and m.use_nodes else None


def floor_pool(room_type, venue):
    if venue in CLINIC:
        return FLOOR_POOLS["clinic"]
    if venue in SHOP:
        return FLOOR_POOLS["shop"]
    if venue in WORKROOMS or room_type in WORKROOMS:
        return FLOOR_POOLS["work"]
    if venue == "cafe":
        return tuple(k.replace("texturecan_", "") for k in wood_floors()) or FLOOR_POOLS["polished"]
    return None                                                 # office-like: carpet / polished concrete by room hash


def apply(room_venues=None, style_venue=None):
    room_venues = room_venues or {}
    done = {"wall": 0, "floor": 0}
    for o in list(bpy.data.objects):
        mt = re.match(r"^(.+)\.(wall|floor)$", o.name)
        if not mt or o.type != "MESH" or o.parent is not None:
            continue
        room, part = mt.groups(); rtype = room.split("_")[0]
        if rtype in SKIP_ROOMS:
            continue
        venue = room_venues.get(room) or room_venues.get(room.replace("/", "-")) or style_venue
        for slot in o.material_slots:
            g = _paint_group(slot.material)
            if g is None:
                continue
            col = tuple(g.inputs["color"].default_value[:3]) if "color" in g.inputs else (0.8, 0.8, 0.78)
            rough0 = g.inputs["roughness"].default_value if "roughness" in g.inputs else 0.5
            if part == "wall":
                t = tex(WALL[_h(room, "wall") % len(WALL)])
                if t is None:
                    continue
                name = f"ir_arch_{t['id']}_wall_{'%02x%02x%02x' % tuple(int(c * 255) for c in col)}"
                slot.material = make_material(name, t, tint=col, rough0=rough0)
            else:
                pool = floor_pool(rtype, venue)
                if pool is None:
                    pool = FLOOR_POOLS["carpet"] if _h(room, "floor") % 10 < 7 else FLOOR_POOLS["polished"]
                t = tex(pool[_h(room, "floor") % len(pool)])
                if t is None:
                    continue
                slot.material = make_material(f"ir_arch_{t['id']}_floor", t, tint=None, rough0=rough0)
            done[part] += 1
    print(f"ARCHTEX walls {done['wall']} floors {done['floor']}", flush=True)
    return done

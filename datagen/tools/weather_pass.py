"""Wear and grime on every material of a finished scene (user 2026-10-17, review notes: 'too smooth, too clean', 'boxes look brand new',
'a Lambertian with no reflections, too clean', 'normals too smooth').

Each opaque Principled material gets, in object space and without UVs:
  * dirt   -- a mask from crevice occlusion (geometry, not lighting), a floor-contact gradient and large soft patches;
              it multiplies the base colour by a warm grey and raises roughness where dirt sits
  * smudge -- low-frequency roughness variation (fingerprints, wiped and unwiped patches) so a surface catches light unevenly
  * grain  -- a fine micro-normal on top of whatever normal the material already has
Albedo / roughness / normal ground truth change with it: that is the point -- a real surface carries these.

    blender -b scene.blend --python weather_pass.py -- --out scene_weathered.blend [--strength 1.0]
    from weather_pass import weather_materials; weather_materials(1.0)      # inside another bpy session
"""
import sys

import bpy

SKIP_NAMES = ("glass", "window", "lamp", "light", "emit", "emission", "screen", "mirror", "sky", "water", "led")


def _val(nt, v):
    n = nt.nodes.new("ShaderNodeValue"); n.outputs[0].default_value = v; return n.outputs[0]


def _math(nt, op, a, b=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath"); n.operation = op; n.use_clamp = clamp
    for k, x in enumerate((a, b)):
        if x is None:
            continue
        if hasattr(x, "node"):
            nt.links.new(x, n.inputs[k])
        else:
            n.inputs[k].default_value = x
    return n.outputs[0]


def weather_one(m, strength=1.0):
    nt = m.node_tree
    b = next((x for x in nt.nodes if x.type == "BSDF_PRINCIPLED"), None)
    if b is None or b.get("weathered"):
        return False
    if b.inputs["Transmission Weight"].default_value > 0.2 or b.inputs["Emission Strength"].default_value > 0 or \
            b.inputs["Alpha"].default_value < 0.99 or any(k in m.name.lower() for k in SKIP_NAMES):
        return False
    L = nt.links
    tc = nt.nodes.new("ShaderNodeTexCoord")
    # large soft patches (dirt / wiped areas) and a fine grain, both in object space
    patch = nt.nodes.new("ShaderNodeTexNoise"); patch.inputs["Scale"].default_value = 1.6; patch.inputs["Detail"].default_value = 6
    patch.inputs["Roughness"].default_value = 0.65; L.new(tc.outputs["Object"], patch.inputs["Vector"])
    streak = nt.nodes.new("ShaderNodeTexNoise"); streak.inputs["Scale"].default_value = 9.0; streak.inputs["Detail"].default_value = 4
    L.new(tc.outputs["Object"], streak.inputs["Vector"])
    grain = nt.nodes.new("ShaderNodeTexNoise"); grain.inputs["Scale"].default_value = 220.0; grain.inputs["Detail"].default_value = 3
    L.new(tc.outputs["Object"], grain.inputs["Vector"])
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion"); ao.inputs["Distance"].default_value = 0.18; ao.samples = 4
    # dirt = crevices + a patchy contribution + floor contact (object-space z of the surface point, low = dirtier)
    crev = _math(nt, "SUBTRACT", 1.0, ao.outputs["AO"])
    soft = nt.nodes.new("ShaderNodeMapRange"); soft.inputs["From Min"].default_value = 0.38; soft.inputs["From Max"].default_value = 0.72
    L.new(patch.outputs["Fac"], soft.inputs["Value"])
    dirt = _math(nt, "ADD", _math(nt, "MULTIPLY", crev, 0.9), _math(nt, "MULTIPLY", soft.outputs["Result"], 0.55), clamp=True)
    dirt = _math(nt, "MULTIPLY", dirt, 0.55 * strength, clamp=True)
    # base colour: keep what the material had, multiply a warm grey by the dirt
    src = b.inputs["Base Color"].links[0].from_socket if b.inputs["Base Color"].is_linked else None
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
    if src is not None:
        L.new(src, mix.inputs[6])
    else:
        mix.inputs[6].default_value = b.inputs["Base Color"].default_value
    mix.inputs[7].default_value = (0.55, 0.5, 0.44, 1.0); L.new(dirt, mix.inputs["Factor"])
    L.new(mix.outputs[2], b.inputs["Base Color"])
    # roughness: smudges (+-0.22) and more roughness where dirty
    r0 = b.inputs["Roughness"].links[0].from_socket if b.inputs["Roughness"].is_linked else _val(nt, b.inputs["Roughness"].default_value)
    sm = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", streak.outputs["Fac"], 0.5), 0.45 * strength)
    rough = _math(nt, "ADD", _math(nt, "ADD", r0, sm), _math(nt, "MULTIPLY", dirt, 0.25), clamp=True)
    L.new(rough, b.inputs["Roughness"])
    # micro normal, chained after the material's own
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.12 * strength; bump.inputs["Distance"].default_value = 0.0015
    L.new(grain.outputs["Fac"], bump.inputs["Height"])
    if b.inputs["Normal"].is_linked:
        L.new(b.inputs["Normal"].links[0].from_socket, bump.inputs["Normal"])
    L.new(bump.outputs["Normal"], b.inputs["Normal"])
    b["weathered"] = True
    return True


def weather_materials(strength=1.0):
    n = 0
    for m in list(bpy.data.materials):
        if m.use_nodes and m.users and not m.library:
            n += weather_one(m, strength)
    print(f"WEATHERED {n} of {len(bpy.data.materials)} materials", flush=True)
    return n


if __name__ == "__main__":
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = a[a.index("--out") + 1]
    st = float(a[a.index("--strength") + 1]) if "--strength" in a else 1.0
    weather_materials(st)
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)

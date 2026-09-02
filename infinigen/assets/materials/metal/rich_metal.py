# Copyright (C) 2026, Robomituba contributors.
# SPDX-License-Identifier: BSD-3-Clause
"""Physically constrained metal generators for IR dataset scenes.

These materials deliberately keep the Principled metalness model physical:
conductors are one, dielectrics are zero, and painted/worn metal uses one
near-binary coverage signal for every affected Principled input.
"""

from __future__ import annotations

import hashlib
import json

import numpy as np

from infinigen.assets.materials.utils import common
from infinigen.core import surface
from infinigen.core.nodes.node_wrangler import Nodes, NodeWrangler

CONTRACT_SCHEMA = "robomituba.metallic_contract.v2"
PROFILE = "principled_rich_v1"


def _seed(value=None) -> int:
    return int(np.random.randint(0, 2**31 - 1) if value is None else value)


def _contract(generator_id: str, seed: int, family: str) -> dict:
    payload = {
        "schema": CONTRACT_SCHEMA,
        "profile": PROFILE,
        "family": family,
        "representation": "spatial_texture" if family == "coverage_mixed" else "scalar",
        "encoding": "linear_scalar",
        "color_space": "non_color",
        "source": "generated",
        "approximation": "principled_coverage" if family == "coverage_mixed" else "none",
        "generator_id": generator_id,
        "seed": int(seed),
        "projection": "world_meter",
        "anisotropy_approximation": "roughness_normal_directional_microstructure",
    }
    payload["parameter_digest"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return payload


def _world_vector(nw: NodeWrangler, physical_size_m: float, brushed: bool = False):
    position = nw.new_node(Nodes.NewGeometry).outputs["Position"]
    inv = 1.0 / max(float(physical_size_m), 1e-4)
    scale = (inv, inv, inv * (12.0 if brushed else 1.0))
    return nw.new_node(Nodes.Mapping, input_kwargs={"Vector": position, "Scale": scale})


def _mix(nw: NodeWrangler, fac, color1, color2):
    return nw.new_node(
        Nodes.MixRGB,
        input_kwargs={"Fac": fac, "Color1": color1, "Color2": color2},
    )


def _bump(nw: NodeWrangler, height, strength: float, distance: float):
    return nw.new_node(
        Nodes.Bump,
        input_kwargs={"Height": height, "Strength": strength, "Distance": distance},
        strict=False,
    ).outputs["Normal"]


def _conductor_shader(
    nw: NodeWrangler,
    *,
    seed: int,
    physical_size_m: float,
    brushed: bool,
    rough_base: float,
):
    vector = _world_vector(nw, physical_size_m, brushed=brushed)
    noise = nw.new_node(
        Nodes.NoiseTexture,
        input_kwargs={
            "Vector": vector,
            "W": float(seed % 100003),
            "Scale": 7.0 if brushed else 4.0,
            "Detail": 8.0,
            "Roughness": 0.65,
        },
        attrs={"noise_dimensions": "4D"},
    )
    scratches = nw.new_node(
        Nodes.NoiseTexture,
        input_kwargs={
            "Vector": vector,
            "W": float((seed + 101) % 100003),
            "Scale": 55.0 if brushed else 18.0,
            "Detail": 3.0,
            "Roughness": 0.8,
        },
        attrs={"noise_dimensions": "4D"},
    )
    metal_dark = (0.18, 0.20, 0.23, 1.0) if brushed else (0.24, 0.20, 0.16, 1.0)
    metal_light = (0.58, 0.62, 0.67, 1.0) if brushed else (0.47, 0.42, 0.34, 1.0)
    base_color = _mix(nw, noise.outputs["Fac"], metal_dark, metal_light)
    roughness = nw.new_node(
        Nodes.MapRange,
        input_kwargs={
            "Value": noise.outputs["Fac"],
            1: 0.0,
            2: 1.0,
            3: max(0.05, rough_base - 0.12),
            4: min(0.9, rough_base + 0.18),
        },
    ).outputs["Result"]
    normal = _bump(nw, scratches.outputs["Fac"], 0.18 if brushed else 0.28, 0.035)
    return nw.new_node(
        Nodes.PrincipledBSDF,
        input_kwargs={
            "Base Color": base_color,
            "Metallic": 1.0,
            "Roughness": roughness,
            "Normal": normal,
            "Specular IOR Level": 0.5,
        },
    )


def shader_clean_brushed_conductor(nw: NodeWrangler, seed=0, physical_size_m=0.12, **_):
    return _conductor_shader(
        nw, seed=int(seed), physical_size_m=physical_size_m, brushed=True, rough_base=0.27
    )


def shader_rough_grained_conductor(nw: NodeWrangler, seed=0, physical_size_m=0.18, **_):
    return _conductor_shader(
        nw, seed=int(seed), physical_size_m=physical_size_m, brushed=False, rough_base=0.48
    )


def _coverage_shader(
    nw: NodeWrangler,
    *,
    seed: int,
    physical_size_m: float,
    worn: bool,
):
    vector = _world_vector(nw, physical_size_m, brushed=False)
    noise = nw.new_node(
        Nodes.NoiseTexture,
        input_kwargs={
            "Vector": vector,
            "W": float(seed % 100003),
            "Scale": 5.0 if worn else 3.0,
            "Detail": 10.0,
            "Roughness": 0.72,
            "Distortion": 0.12,
        },
        attrs={"noise_dimensions": "4D"},
    )
    coverage = nw.new_node(Nodes.ColorRamp, input_kwargs={"Fac": noise.outputs["Fac"]})
    coverage.color_ramp.interpolation = "CONSTANT"
    threshold = 0.58 if worn else 0.69
    coverage.color_ramp.elements[0].position = threshold
    coverage.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    coverage.color_ramp.elements[1].position = min(1.0, threshold + 0.002)
    coverage.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    exposed = coverage.outputs["Color"]
    paint = (0.055, 0.12, 0.18, 1.0) if worn else (0.42, 0.055, 0.035, 1.0)
    metal = (0.43, 0.47, 0.51, 1.0)
    base_color = _mix(nw, exposed, paint, metal)
    roughness = _mix(nw, exposed, (0.54, 0.54, 0.54, 1.0), (0.24, 0.24, 0.24, 1.0))
    micro = nw.new_node(
        Nodes.NoiseTexture,
        input_kwargs={"Vector": vector, "Scale": 42.0, "Detail": 4.0, "Roughness": 0.7},
    )
    height = nw.new_node(
        Nodes.MixRGB,
        input_kwargs={"Fac": exposed, "Color1": micro.outputs["Fac"], "Color2": exposed},
    )
    normal = _bump(nw, height, 0.24, 0.04)
    return nw.new_node(
        Nodes.PrincipledBSDF,
        input_kwargs={
            "Base Color": base_color,
            "Metallic": exposed,
            "Roughness": roughness,
            "Normal": normal,
            "Specular IOR Level": 0.5,
        },
    )


def shader_painted_metal_coverage(nw: NodeWrangler, seed=0, physical_size_m=0.22, **_):
    return _coverage_shader(nw, seed=int(seed), physical_size_m=physical_size_m, worn=False)


def shader_worn_metal_coverage(nw: NodeWrangler, seed=0, physical_size_m=0.16, **_):
    return _coverage_shader(nw, seed=int(seed), physical_size_m=physical_size_m, worn=True)


class _RichMetal:
    shader = None
    generator_id = ""
    family = "conductor"
    physical_size_m = 0.15

    def generate(self, seed=None, **kwargs):
        material_seed = _seed(seed)
        material = surface.shaderfunc_to_material(
            self.shader,
            seed=material_seed,
            physical_size_m=float(kwargs.pop("physical_size_m", self.physical_size_m)),
            name=self.generator_id,
            **kwargs,
        )
        material["robomituba_metallic_contract"] = json.dumps(
            _contract(self.generator_id, material_seed, self.family), sort_keys=True
        )
        material["robomituba_ir_material_profile"] = PROFILE
        return material

    def apply(self, obj, selection=None, seed=None, **kwargs):
        material = self.generate(seed=seed, **kwargs)
        common.apply(obj, material, selection)
        targets = obj if isinstance(obj, (list, tuple)) else [obj]
        for target in targets:
            target["robomituba_material_part_semantic"] = "metal_capable"

    __call__ = generate


class CleanBrushedConductor(_RichMetal):
    shader = staticmethod(shader_clean_brushed_conductor)
    generator_id = "clean_brushed_conductor_v1"
    family = "conductor"
    physical_size_m = 0.12


class RoughGrainedConductor(_RichMetal):
    shader = staticmethod(shader_rough_grained_conductor)
    generator_id = "rough_grained_conductor_v1"
    family = "conductor"
    physical_size_m = 0.18


class PaintedMetalCoverage(_RichMetal):
    shader = staticmethod(shader_painted_metal_coverage)
    generator_id = "painted_metal_coverage_v1"
    family = "coverage_mixed"
    physical_size_m = 0.22


class WornMetalCoverage(_RichMetal):
    shader = staticmethod(shader_worn_metal_coverage)
    generator_id = "worn_metal_coverage_v1"
    family = "coverage_mixed"
    physical_size_m = 0.16

"""Probe cameras for a finished scene: wide shots from room corners + close-ups of placed objects (line of sight checked)."""
import json, math, random, sys
sys.path.insert(0, "/jarvis/project/robomituba/tools/infinigen")
import bpy
from mathutils import Vector
import furnish_rooms as fr, room_dressing as rd
blend, out, n_close = sys.argv[-3], sys.argv[-2], int(sys.argv[-1])
bpy.ops.wm.open_mainfile(filepath=blend)
sc, deps = bpy.context.scene, bpy.context.evaluated_depsgraph_get()
views, rng = [], random.Random(0)
import os
HFOV = float(os.environ.get("PROBE_HFOV", "85"))             # style QA (non-home 20): 60-65 deg, like the reference photos
LABEL = os.environ.get("PROBE_LABEL")                         # e.g. 'cafe' instead of the borrowed layout's 'break-room'
REFVIEWS = os.environ.get("PROBE_REFVIEWS") == "1"
for name, parts in rd._rooms().items():
    if "floor" not in parts: continue
    room = fr.Room(name, parts, sc, deps); x0, x1, y0, y1 = room.box; c = Vector(((x0 + x1) / 2, (y0 + y1) / 2, room.z))
    for k, (px, py) in enumerate(((x0 + 0.6, y0 + 0.6), (x1 - 0.6, y1 - 0.6), (x0 + 0.6, y1 - 0.6), (x1 - 0.6, y0 + 0.6))):
        if room.on_floor(px, py):
            views.append({"name": f"{LABEL or name.split('_')[0]}_wide{k}", "location": [px, py, room.z + 1.7], "target": [c.x, c.y, room.z + (1.6 if k % 2 else 1.25)], "hfov": HFOV, "res": [512, 384]})
    if REFVIEWS:                                              # framed like the reference views: entrance -> counter wall, and the seating
        lab = LABEL or name.split('_')[0]
        views.insert(0, {"name": f"{lab}_ref_entrance", "location": [c.x, y0 + 0.7, room.z + 1.5], "target": [c.x, y1, room.z + 1.3], "hfov": HFOV, "res": [512, 384]})
        views.insert(1, {"name": f"{lab}_ref_seating", "location": [x0 + 0.7, y0 + 0.9, room.z + 1.45], "target": [x1, (y0 + y1) / 2, room.z + 0.9], "hfov": HFOV, "res": [512, 384]})
objs = [o for o in rd._tops() if rd._factory(o.name) not in ("CeilingLightFactory",) and "Door" not in o.name and "Window" not in o.name]
big = [o for o in objs if max(o.dimensions) >= 0.5 and not any(k in o.name for k in ("Curtain", "Pilaster", "WallArt", "Lamp", "Light"))]  # these fill the frame or hang from the ceiling (clinic r5, cafe kits)          # close-ups on furniture/equipment, not desk clutter (clinic r1 critic)
small = [o for o in objs if o not in big]
rng.shuffle(big); rng.shuffle(small)
# each venue's defining piece gets the first close-up (chain H: the banquette was placed but never framed; 'no banquette' twice)
HERO = ("Banquette", "DentalChair", "ExamTable", "ReceptionDesk", "PantryRun", "Workbench", "StorageRack", "DisplayCooler",
        "ClothingRack", "CafeCounter", "MedicalCabinet", "ParallelBars")
first = {}                                                    # one close-up per hero type, then the shuffled rest
for o in big:
    h = next((i for i, h in enumerate(HERO) if h in o.name), None)
    if h is not None and h not in first:
        first[h] = o
big = [first[k] for k in sorted(first)] + [o for o in big if o not in first.values()]
objs = big + small
for o in objs:
    if sum(v["name"].startswith("c") for v in views) >= n_close: break
    f = fr.footprint(o); t = Vector(((f[0] + f[1]) / 2, (f[2] + f[3]) / 2, (f[4] + f[5]) / 2))
    for a in [math.radians(x) for x in range(0, 360, 30)]:
        cam = t + Vector((math.cos(a) * 2.2, math.sin(a) * 2.2, 0)); cam.z = f[4] + 1.5
        down = sc.ray_cast(deps, cam, Vector((0, 0, -1)), distance=3.0); d = t - cam
        hit = sc.ray_cast(deps, cam, d.normalized(), distance=d.length + 0.3)
        if down[0] and down[4].name.endswith(".floor") and hit[0] and (hit[4] == o or hit[4] in o.children_recursive):
            views.append({"name": f"c{len(views):02d}_{o.name.split('(')[0][:20]}", "location": list(cam), "target": list(t), "hfov": 70.0, "res": [512, 384]}); break
open(out, "w").write(json.dumps(views, indent=1)); print("VIEWS", len(views), flush=True)

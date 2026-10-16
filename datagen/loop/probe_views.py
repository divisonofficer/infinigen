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
def over_floor(cam, r=0.3):                                   # bare floor below the lens and around it (clinic r19: a close-up from
    return all((h := sc.ray_cast(deps, cam + Vector((dx, dy, 0)), Vector((0, 0, -1)), distance=3.0))[0] and h[4].name.endswith(".floor")
               for dx, dy in ((0, 0), (r, 0), (-r, 0), (0, r), (0, -r)))   # right over a chair seat)
import os
HFOV = float(os.environ.get("PROBE_HFOV", "85"))             # style QA (non-home 20): 60-65 deg, like the reference photos
LABEL = os.environ.get("PROBE_LABEL")                         # e.g. 'cafe' instead of the borrowed layout's 'break-room'
REFVIEWS = os.environ.get("PROBE_REFVIEWS") == "1"
_rooms_all = {n: pa for n, pa in rd._rooms().items() if "floor" in pa}
_multi = len(_rooms_all) > 1                                  # a floor scene: label by the full room id (floor E: reception and three
for name, parts in rd._rooms().items():                       # dental rooms are all 'office_0/x' and their views collided)
    if "floor" not in parts: continue
    room = fr.Room(name, parts, sc, deps); x0, x1, y0, y1 = room.box; c = Vector(((x0 + x1) / 2, (y0 + y1) / 2, room.z))
    for k, (px, py) in enumerate(((x0 + 0.6, y0 + 0.6), (x1 - 0.6, y1 - 0.6), (x0 + 0.6, y1 - 0.6), (x1 - 0.6, y0 + 0.6))):
        if room.on_floor(px, py):
            tgt = Vector((c.x, c.y, room.z + (1.65 if k % 2 else 1.5)))   # near level: in a 16 m2 room a 1.25 m aim tilted the ceiling
                                                              # out of frame (clinic r21: exam/dental ceiling+light 4, 'never shown')
            cam = Vector((px, py, room.z + 1.7))
            for _ in range(5):                                # step toward the centre while something sits within 1 m of the lens
                d = tgt - cam                                 # (clinic r12: wide shots from inside a privacy curtain or a rack)
                hit = sc.ray_cast(deps, cam, d.normalized(), distance=1.0)
                low = sc.ray_cast(deps, cam, (d - Vector((0, 0, 1.2))).normalized(), distance=1.0)   # the lower frame too (wh r19:
                if not hit[0] and not low[0] and over_floor(cam):                                   # a box pile filled wide1's bottom half)            # or under it (clinic r19: a wide shot from above the reception desk)
                    break
                cam = cam + Vector((d.x, d.y, 0)).normalized() * 0.4
            views.append({"name": f"{LABEL or (name.replace('/', '-') if _multi else name.split('_')[0])}_wide{k}", "location": list(cam), "target": list(tgt), "hfov": HFOV, "res": [512, 384]})
    if REFVIEWS:                                              # framed like the reference views: entrance -> counter wall, and the seating
        lab = LABEL or name.split('_')[0]
        views.insert(0, {"name": f"{lab}_ref_entrance", "location": [c.x, y0 + 0.7, room.z + 1.5], "target": [c.x, y1, room.z + 1.3], "hfov": HFOV, "res": [512, 384]})
        views.insert(1, {"name": f"{lab}_ref_seating", "location": [x0 + 0.7, y0 + 0.9, room.z + 1.45], "target": [x1, (y0 + y1) / 2, room.z + 0.9], "hfov": HFOV, "res": [512, 384]})
objs = [o for o in rd._tops() if rd._factory(o.name) not in ("CeilingLightFactory",) and "Door" not in o.name and "Window" not in o.name]
big = [o for o in objs if max(o.dimensions) >= 0.5 and not any(k in o.name for k in ("Curtain", "Pilaster", "WallArt", "Lamp", "Light", "Plant", "OliveTree"))]  # these fill the frame or hang from the ceiling (clinic r5, cafe kits)          # close-ups on furniture/equipment, not desk clutter (clinic r1 critic)
small = [o for o in objs if o not in big]
rng.shuffle(big); rng.shuffle(small)
# each venue's defining piece gets the first close-up (chain H: the banquette was placed but never framed; 'no banquette' twice;
# packing r18: pallets were close-ups 4-5, off the 3-close-up sheet, and 3 of 3 calls said 'no pallets')
HERO = ("Banquette", "DentalChair", "ExamTable", "ReceptionDesk", "PantryRun", "Workbench", "Pallet", "StorageRack", "DisplayCooler",
        "ClothingRack", "CafeCounter", "MedicalCabinet", "ParallelBars")
hero = lambda o: next((i for i, h in enumerate(HERO) if h in o.name), None)
# one close-up per hero type -- every object of the type is tried until one frames (packing r19: the first pallet had no clear
# sightline and the type got no close-up) -- then the shuffled rest
heroes = sorted((o for o in big if hero(o) is not None), key=hero)
objs = heroes + [o for o in big if hero(o) is None] + small
got = set()
for o in objs:
    if sum(v["name"].startswith("c") for v in views) >= n_close: break
    if o in heroes and hero(o) in got: continue
    f = fr.footprint(o); t = Vector(((f[0] + f[1]) / 2, (f[2] + f[3]) / 2, (f[4] + f[5]) / 2))
    fwd = o.matrix_world.to_3x3() @ Vector((1, 0, 0))          # proc assets face local +X: try angles in front of the object first
    angs = sorted(range(0, 360, 30), key=lambda x: -(math.cos(math.radians(x)) * fwd.x + math.sin(math.radians(x)) * fwd.y))
    # three distances: a hero piece in a 17 m2 room found no 2.2 m spot over bare floor (dental r20: the chair got no close-up, 4/10)
    for a, r in [(math.radians(x), r) for r in (2.2, 1.8, 2.6) for x in angs]:   # (pantry r13-r21: the run's close-up was taken
        cam = t + Vector((math.cos(a) * r, math.sin(a) * r, 0)); cam.z = f[4] + 1.5   # from behind its wall)
        if not over_floor(cam):
            continue
        # aim at a height where the object has substance: a dental chair's bbox centre is air under its lamp boom (dental r21: every
        # big piece missed its close-up, the sightline passed through to the far wall)
        aim = next((p for p in (t, Vector((t.x, t.y, f[4] + 0.5)), Vector((t.x, t.y, f[4] + 0.9)))
                    if (h := sc.ray_cast(deps, cam, (p - cam).normalized(), distance=(p - cam).length + 0.3))[0]
                    and (h[4] == o or h[4] in o.children_recursive)), None)
        if aim is not None:
            views.append({"name": f"c{len(views):02d}_{o.name.split('(')[0][:20]}", "location": list(cam), "target": list(aim), "hfov": 70.0, "res": [512, 384]})
            got.add(hero(o)); break
open(out, "w").write(json.dumps(views, indent=1)); print("VIEWS", len(views), flush=True)

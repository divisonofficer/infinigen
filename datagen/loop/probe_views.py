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
_leaves = []                                                  # open door leaves: a lens beside one sees half a frame of door (floor C r5:
for o in bpy.data.objects:                                    # office_0-1 3 of 4 wides, 3 of 3 calls)
    f = o.name.split("(")[0]
    if o.type == "MESH" and "Door" in f and "Casing" not in f:   # not curtains: their 2.6 x 1.6 m box left one wide per
                                                                  # treatment room (floor F3 r8)
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        _leaves.append((min(p.x for p in pts), max(p.x for p in pts), min(p.y for p in pts), max(p.y for p in pts)))
def near_door(cam, r=0.7):
    return any(b[0] - r < cam.x < b[1] + r and b[2] - r < cam.y < b[3] + r for b in _leaves)
import os
HFOV = float(os.environ.get("PROBE_HFOV", "85"))             # style QA (non-home 20): 60-65 deg, like the reference photos
LABEL = os.environ.get("PROBE_LABEL")                         # e.g. 'cafe' instead of the borrowed layout's 'break-room'
REFVIEWS = os.environ.get("PROBE_REFVIEWS") == "1"
_rooms_all = {n: pa for n, pa in rd._rooms().items() if "floor" in pa}
def _area(pa):
    pts = [pa["floor"].matrix_world @ Vector(c) for c in pa["floor"].bound_box]
    return (max(p.x for p in pts) - min(p.x for p in pts)) * (max(p.y for p in pts) - min(p.y for p in pts))
_hub = max(_rooms_all, key=lambda n: _area(_rooms_all[n])) if _rooms_all else None
_multi = len(_rooms_all) > 1                                  # a floor scene: label by the full room id (floor E: reception and three
for name, parts in rd._rooms().items():                       # dental rooms are all 'office_0/x' and their views collided)
    if "floor" not in parts: continue
    room = fr.Room(name, parts, sc, deps); x0, x1, y0, y1 = room.box; c = Vector(((x0 + x1) / 2, (y0 + y1) / 2, room.z))
    for k, (px, py) in enumerate(((x0 + 0.6, y0 + 0.6), (x1 - 0.6, y1 - 0.6), (x0 + 0.6, y1 - 0.6), (x1 - 0.6, y0 + 0.6))):
        if room.on_floor(px, py):
            tgt = Vector((c.x, c.y, room.z + (1.65 if k % 2 else 1.5)))   # near level: in a 16 m2 room a 1.25 m aim tilted the ceiling
            wc = [o.matrix_world.translation for o in bpy.data.objects if o.parent is None and ("ToiletFactory" in o.name or "ToiletStall" in o.name)
                  and x0 <= o.matrix_world.translation.x <= x1 and y0 <= o.matrix_world.translation.y <= y1]
            if wc and k % 2 and (Vector((px, py, 0)) - Vector((wc[0].x, wc[0].y, 0))).length >= 1.6:   # not from right over the bowl (floor J r9)                                  # a restroom's odd wides frame the WC (floor F3 r4: the pan only a sliver at the
                tgt = Vector((wc[0].x, wc[0].y, room.z + 0.9))   # frame edge, function 5, 3 of 3)
                                                              # out of frame (clinic r21: exam/dental ceiling+light 4, 'never shown')
            def clearance(p):                                 # free distance toward the aim, upper and lower frame (cap 3 m)
                d = tgt - p
                return min((h[1] - p).length if (h := sc.ray_cast(deps, p, v.normalized(), distance=3.0))[0] else 3.0
                           for v in (d, d - Vector((0, 0, 1.2))))
            for door_rule in (True, False):                   # the door-leaf rule gives way when nothing else frames (floors G/H r12-r14:
              cam = corner = Vector((px, py, room.z + 1.7)); best = (-1.0, corner)   # stockrooms lost 2 of 4 wides)
              for _ in range(6):                              # step toward the centre while something sits within 1 m of the lens
                d = tgt - cam                                 # (clinic r12: wide shots from inside a privacy curtain or a rack)
                ok = over_floor(cam) and not (door_rule and near_door(cam))   # bare floor below (clinic r19: a wide shot from above the reception desk)
                cl = clearance(cam) if ok else -1.0
                if cl >= 1.0:
                    break
                best = max(best, (cl, cam), key=lambda b: b[0])
                if Vector((d.x, d.y)).length < 0.7:           # (1.4 dropped most wides of 9-11 m2 rooms, floor F3 r4; a spot needs
                                                              # bare floor below it now, so no top-down table)  within 1 m of the centre a small room's table fills the frame from
                    cam = best[1]; break                      # above (floor A r2); otherwise the most open spot seen -- not a stall's
                cam = cam + Vector((d.x, d.y, 0)).normalized() * 0.4   # inside, which has bare floor too (floor H r4: four restroom
              else:                                                     # wides of partition panels)
                cam = best[1]
              if best[0] >= 0 or cam is not corner:
                break
            if best[0] < 0 and cam is corner and not over_floor(corner):   # no spot with bare floor under it: the lens would sit inside a
                continue                                                    # rack or stall (floor H r5: an all-black stockroom wide)
            views.append({"name": f"{LABEL or (name.replace('/', '-') if _multi else name.split('_')[0])}_wide{k}", "location": list(cam), "target": list(tgt), "hfov": HFOV, "res": [512, 384]})
    if _multi and name == _hub:                              # the hub's entrance view: from inside its doors toward the room (floor I r13:
        for o in bpy.data.objects:                            # 'no checkout or entrance in any wide', 3 of 3 -- the corners face away)
            if "DoorCasing" not in o.name:
                continue
            p_ = o.matrix_world.translation
            n_ = o.matrix_world.to_3x3() @ Vector((0, 1, 0)); n_.z = 0
            if n_.length < 1e-6 or not (x0 - 0.4 <= p_.x <= x1 + 0.4 and y0 - 0.4 <= p_.y <= y1 + 0.4):
                continue
            n_.normalize()
            if not room.on_floor((p_ + n_ * 1.2).x, (p_ + n_ * 1.2).y):
                n_ = -n_
            cam_ = p_ + n_ * 1.2; cam_.z = room.z + 1.6
            if room.on_floor(cam_.x, cam_.y) and over_floor(cam_):
                views.append({"name": f"{name.replace('/', '-')}_wide4", "location": list(cam_), "target": [c.x, c.y, room.z + 1.2], "hfov": HFOV,
                              "res": [512, 384]})
                break
        # the hub's front piece seen from across the room (floor I r14: the till stood by the door, behind the entrance view and away
        # from every corner wide -- 'no checkout in any wide', 3 of 3)
        fronts = [o for o in bpy.data.objects if o.parent is None and any(k in o.name for k in ("CheckoutCounter", "CafeCounter", "ReceptionDesk"))
                  and x0 <= o.matrix_world.translation.x <= x1 and y0 <= o.matrix_world.translation.y <= y1]
        if fronts:
            # from in front of the counter, fanned +-60 deg off its front, the first spot with a clear sightline to it: from across the
            # room the view was 'head-on to a gondola' (floor I r15, 3 of 3: 'checkout only in close-ups')
            F_ = fronts[0]; t = F_.matrix_world.translation.copy(); tz = Vector((t.x, t.y, room.z + 1.0))
            fw = F_.matrix_world.to_3x3() @ Vector((1, 0, 0)); fw.z = 0
            base = math.atan2(fw.y, fw.x) if fw.length > 1e-6 else math.atan2(c.y - t.y, c.x - t.x)
            done_ = False
            for dist in (3.5, 3.0, 4.5, 2.5):
                for da in (0, 25, -25, 45, -45, 60, -60):
                    a_ = base + math.radians(da)
                    cam_ = Vector((t.x + math.cos(a_) * dist, t.y + math.sin(a_) * dist, room.z + 1.65))
                    if not (x0 + 0.4 < cam_.x < x1 - 0.4 and y0 + 0.4 < cam_.y < y1 - 0.4) or not room.on_floor(cam_.x, cam_.y) or not over_floor(cam_):
                        continue
                    h = sc.ray_cast(deps, cam_, (tz - cam_).normalized(), distance=(tz - cam_).length + 0.5)
                    if h[0] and (h[4] == F_ or h[4] in F_.children_recursive):
                        views.append({"name": f"{name.replace('/', '-')}_wide5", "location": list(cam_), "target": list(tz), "hfov": HFOV, "res": [512, 384]})
                        done_ = True; break
                if done_:
                    break
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
HERO = ("CheckoutCounter", "Banquette", "DentalChair", "ExamTable", "ReceptionDesk", "PantryRun", "Workbench", "Pallet", "StorageRack", "DisplayCooler",
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

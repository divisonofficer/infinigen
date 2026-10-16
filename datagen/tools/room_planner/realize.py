"""Turn room plans (plan_scene.py: Claude) into placed objects, inside the activity pass (Blender).

Every furniture item resolves its relation to a list of candidate (x, y, yaw) spots, tried in order through furnish_rooms._place:
standing on the room's own floor, clear of every footprint (and door zone) by 5 cm. An item whose target is placed later in the plan is
retried after the rest; one with no valid spot is dropped and counted (stats["plan_dropped"]). Lived-in items go on their host's
support surfaces through the activity pass's put(), or on free floor.

Room frame -> world: + room["_origin"]. Existing objects are found by name (extract_rooms "_name").
"""
from __future__ import annotations

import importlib
import json
import math
import time
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

import furnish_rooms as fr
import room_dressing as rd
from room_planner import catalog
from room_planner.extract_rooms import inside

INF = {"OfficeChairFactory": "seating.chairs.office_chair", "ChairFactory": "seating.chairs.chair", "SimpleDeskFactory": "shelves.simple_desk",
       "SimpleBookcaseFactory": "shelves.simple_bookcase", "TVStandFactory": "shelves.cell_shelf",
       "LargePlantContainerFactory": "tableware.plant_container", "BlanketFactory": "clothes.blanket", "PillowFactory": "seating.pillow",
       "BookStackFactory": "table_decorations.book", "CupFactory": "tableware.cup", "FruitContainerFactory": "tableware.fruit_container",
       "ShirtFactory": "clothes.shirt", "BasketBaseFactory": "organizer.basket", "PantsFactory": "clothes.pants", "TowelFactory": "clothes.towel",
       "BookFactory": "table_decorations.book", "LargeShelfFactory": "shelves.large_shelf", "BottleFactory": "tableware.bottle",
       "CanFactory": "tableware.can", "FoodBoxFactory": "tableware.food_box", "JarFactory": "tableware.jar",
       "MonitorFactory": "appliances.tv", "TableDiningFactory": "tables.dining_table", "PlateFactory": "tableware.plate",
       "WineglassFactory": "tableware.wineglass", "BeverageFridgeFactory": "appliances.beverage_fridge", "CupFactory": "tableware.cup",
       "BowlFactory": "tableware.bowl", "MicrowaveFactory": "appliances.microwave"}
#: spacing between items of a `row`: _place keeps 5 cm between footprints, so a 3 cm gap made every second rack / gondola / stool
#: in a row collide with the first (warehouse: 7 racks dropped; grocery aisles; window-bar stools -- 2026-10-16)
ROW_GAP = 0.07
SHRINKABLE = ("counter", "backbar_shelf", "window_bar", "pantry_unit")
SEATS = ("desk_chair", "conference_chair", "cafe_chair", "break_chair", "bar_stool", "dining_chair")
TABLES = ("break_table", "meeting_table", "dining_table", "cafe_table", "workbench")
SHELVES = ("SimpleBookcaseFactory", "LargeShelfFactory", "CellShelfFactory", "TVStandFactory", "AboRackFactory", "AboBookcaseFactory",
           "BackBarShelfFactory", "GondolaFactory", "WallGondolaFactory")
#: hosts with soft, curved tops: the surface grid finds no flat level there, so things are dropped on them with physics instead
SOFT = ("SofaFactory", "BedFactory", "ArmChairFactory", "ChairFactory", "OfficeChairFactory", "BarChairFactory", "AboSofaFactory",
        "AboArmchairFactory")


T0 = time.time()


def _log(msg):
    print(f"[realize {time.time() - T0:7.1f}s] {msg}", flush=True)


def _cls(src):
    kind, name = src.split(":")
    if kind == "proc":
        from room_planner import proc_assets
        return getattr(proc_assets, name)
    if kind == "abo":
        import abo_assets as abo
        return getattr(abo, name)
    return getattr(importlib.import_module("infinigen.assets.objects." + INF[name]), name)


def _frame(o, front):
    """(centre, unit front, width, depth) of o in world xy."""
    f = fr.footprint(o)
    fwd = o.matrix_world.to_3x3() @ Vector((*front, 0)); fwd.z = 0; fwd.normalize()
    lx, ly = (o.dimensions[1], o.dimensions[0]) if abs(front[0]) > 0.5 else (o.dimensions[0], o.dimensions[1])   # (width, depth)
    return Vector(((f[0] + f[1]) / 2, (f[2] + f[3]) / 2, 0)), fwd, lx, ly


def _yaw(v):
    return math.atan2(v.y, v.x)


def _left(v):
    return Vector((-v.y, v.x, 0))


class RoomRealizer:
    def __init__(self, room_doc, room, rng, stats, spawn, act, obstacles, rugzones, t, revise=None):
        self.doc, self.room, self.rng, self.stats, self.spawn, self.act, self.t = room_doc, room, rng, stats, spawn, act, t
        self.revise = revise                                     # (plan, report) -> revised plan | None
        self.obstacles, self.rugzones = obstacles, rugzones
        ox, oy = room_doc["_origin"]
        self.poly = [(x + ox, y + oy) for x, y in room_doc["outline"]]
        self.centre = Vector((sum(x for x, _ in self.poly) / len(self.poly), sum(y for _, y in self.poly) / len(self.poly), 0))
        self.walls = {}
        for w in room_doc["walls"]:
            a, b = Vector((w["p0"][0] + ox, w["p0"][1] + oy, 0)), Vector((w["p1"][0] + ox, w["p1"][1] + oy, 0))
            t_ = (b - a).normalized(); n = _left(t_)
            mid = (a + b) / 2
            if not inside((mid + n * 0.2)[:2], self.poly):
                n = -n
            self.walls[w["id"]] = (a, t_, n, w["length"])
        self.ids = {}                                            # plan id / existing id -> (object, front axis)
        for e in room_doc["existing"]:
            o = bpy.data.objects.get(e.get("_name", ""))
            if o is not None:
                self.ids[e["id"]] = (o, fr.INF_FRONT)

    # ---- spawning -----------------------------------------------------------------------------------------------------------------
    def _make(self, cat):
        spare = getattr(self, "spare", {}).get(cat)
        if spare:                                                # spawned for an item that found no spot: reuse, do not regrow
            return spare.pop()
        src = catalog.FURNITURE[cat]["src"]
        kind, key = src.split(":")
        if kind == "abo":
            if not fr.pool(key):                                 # no ABO model passes this pool's filter: drop the item, keep the scene
                self.stats.setdefault("empty_pool", {})[key] = self.stats.get("empty_pool", {}).get(key, 0) + 1
                return None, fr.ABO_FRONT
            return fr.AboPick(key, self.rng).spawn(self.stats["furniture_added"]), fr.ABO_FRONT
        if kind == "proc":
            o = _cls(src)(self.rng.randrange(1 << 24)).spawn_asset(self.stats["furniture_added"])
            bpy.context.view_layer.update()
            return o, fr.INF_FRONT
        if kind == "copy":                                       # the room's own chair model, so a set matches
            protos = [o for o, _ in self.ids.values() if rd._factory(o.name) in ("ChairFactory", "BarChairFactory")]
            if protos:
                c = protos[0].copy(); c.data = protos[0].data; bpy.context.scene.collection.objects.link(c)
                c.name = f"{rd._factory(protos[0].name)}(plan).spawn_asset({self.stats['furniture_added']})"
                return c, fr.INF_FRONT
            key = "ChairFactory"
        return self.spawn(_cls("inf:" + key)), fr.INF_FRONT

    # ---- candidate spots per relation ---------------------------------------------------------------------------------------------
    def _along_wall(self, wid, w, d, starts=None):
        a, t_, n, length = self.walls[wid]
        ss = starts or [length / 2]
        out = []
        for s0 in ss:
            for k in range(0, 30):                               # slide out from the preferred spot in 15 cm steps
                s = s0 + (k + 1) // 2 * 0.15 * (1 if k % 2 else -1)
                if w / 2 + 0.05 <= s <= length - w / 2 - 0.05:
                    p = a + t_ * s + n * (d / 2 + 0.03)
                    out.append((p.x, p.y, _yaw(n)))
        return out

    def spots(self, it, w, d):
        rel, tgt = it["relation"], it.get("target")
        gap = it.get("gap_m")
        # a target-less relation other than corner/center means the wall (center fell in here too until office r2: every
        # 'center' meeting table and REQUIRED_ZONE pod was stood against a wall)
        if rel in ("against_wall", "near_window") or (rel not in ("corner", "center") and tgt not in self.ids and tgt != "room"):
            wid = it.get("wall")
            walls = [wid] if wid in self.walls else sorted(self.walls, key=lambda k: -self.walls[k][3])
            if rel == "near_window" and self.doc["windows"]:
                win = self.rng.choice(self.doc["windows"])
                return self._along_wall(win["wall"], w, d, [win["at_m"]])
            return [s for k in walls for s in self._along_wall(k, w, d + 2 * (gap or 0))]   # gap_m: clearance kept from the wall
        if rel == "row" and it.get("wall") in self.walls:
            a, t_, n, length = self.walls[it["wall"]]
            k = self.row_k.get(it["id"], 0)                      # this copy's slot in the row
            cnt = max(1, it.get("count", 1))
            run = cnt * w + (cnt - 1) * ROW_GAP
            g = max(0.0, it.get("gap_m") or 0.0)
            face = -n if it.get("facing") == "toward" else n
            out = []
            for shift in [0.0] + [d_ * sg for d_ in (0.3, 0.6, 1.0, 1.5, 2.0, 3.0) for sg in (1, -1)]:
                s = (length - run) / 2 + shift + k * (w + ROW_GAP) + w / 2
                if w / 2 <= s <= length - w / 2:
                    p = a + t_ * s + n * (g + d / 2 + 0.03)
                    out.append((p.x, p.y, _yaw(face)))
            return out
        if rel == "center":                                     # a meeting table, an island: the middle of the room
            # the long side (local y, front +X) along the room's long axis first (critic r1: a table across the room reads as dining)
            x0, x1, y0, y1 = self.room.box
            yaws = (math.pi / 2, 0.0) if (x1 - x0) > (y1 - y0) else (0.0, math.pi / 2)
            return [(self.centre.x + dx, self.centre.y + dy, yaw) for yaw in yaws for dx in (0, 0.4, -0.4, 0.8, -0.8)
                    for dy in (0, 0.4, -0.4)]
        if rel == "corner" or tgt == "room":
            out = []
            n = len(self.poly)
            for i in self.rng.sample(range(n), n):
                v = Vector((*self.poly[i], 0))
                a, b = (Vector((*self.poly[i - 1], 0)) - v).normalized(), (Vector((*self.poly[(i + 1) % n], 0)) - v).normalized()
                bis = (a + b)
                if bis.length < 1e-3 or not inside((v + bis.normalized() * 0.3)[:2], self.poly):
                    continue                                     # a reflex corner: the bisector points out of the room
                for p in (v + a * (d / 2 + 0.08) + b * (w / 2 + 0.08), v + b * (d / 2 + 0.08) + a * (w / 2 + 0.08)):
                    out.append((p.x, p.y, _yaw(self.centre - p)))   # facing into the room
            return out
        o, front = self.ids[tgt]
        c, f, tw, td = _frame(o, front)
        if rel == "in_front_of":
            g = max(0.07, 0.45 if gap is None else gap)
            base = c + f * (td / 2 + g + d / 2)
            return [((base + _left(f) * j).x, (base + _left(f) * j).y, _yaw(-f)) for j in (0, 0.15, -0.15, 0.3, -0.3)]
        if rel == "beside":
            g = max(0.07, gap or 0)                              # _place keeps 5 cm between footprints
            sides = {"left": [1], "right": [-1]}.get(it.get("side"), [1, -1])
            out = []
            for sg in sides:
                for back in (-(td / 2) + d / 2, 0.0):            # backs aligned (a nightstand by a bed head), else centred
                    p = c + _left(f) * sg * (tw / 2 + g + w / 2) + f * back
                    out.append((p.x, p.y, _yaw(f)))
            return out
        if rel == "under":
            return [((c + f * (td * k)).x, (c + f * (td * k)).y, _yaw(f) + r) for k in (0.25, 0.0, 0.4) for r in (0, math.pi / 2)]
        if rel == "facing":
            out = []
            for dist in (1.6, 2.0, 2.5, 3.0):
                for ang in (0, 25, -25, 50, -50, 75, -75):
                    v = Vector((math.cos(_yaw(f) + math.radians(ang)), math.sin(_yaw(f) + math.radians(ang)), 0))
                    p = c + v * dist
                    out.append((p.x, p.y, _yaw(-v)))
            return out
        if rel == "around":
            n = max(1, it.get("count", 4))
            long_f = td >= tw                                    # chairs go on the long sides
            ax, side = (f, _left(f)) if long_f else (_left(f), f)
            half_l, half_s = (td if long_f else tw) / 2, (tw if long_f else td) / 2
            # every seat the side holds (count is how many to add), a seat pitch of at least the chair + ROW_GAP: a 0.6 m pitch for
            # 0.6 m office chairs made every second one collide (critic r1: 'few chairs, placed at random')
            pitch = max(w, d) + 0.1                              # orientation-proof: w/d of an ABO chair may be swapped vs its pose
            per = max(1, int((2 * half_l + 0.1) / pitch))
            out = []
            for k in range(per):
                off = (k - (per - 1) / 2) * max(pitch, min(0.8, 2 * half_l / per))
                for sg in (1, -1):
                    p = c + ax * off + side * sg * (half_s + d / 2 + 0.07)
                    out.append((p.x, p.y, _yaw(-side * sg)))
            return out
        return []

    # ---- placing --------------------------------------------------------------------------------------------------------------------
    def _wall_mount(self, cat, z_bottom, avoid=None) -> bool:
        """A wall-mounted piece (display, whiteboard): stood against the longest free wall run (another wall than `avoid`), then lifted."""
        o, front = self._make(cat)
        if o is None:
            return False
        w, d = o.dimensions[1], o.dimensions[0]
        walls = sorted((k for k in self.walls if k != avoid), key=lambda k: -self.walls[k][3])
        for k in walls:
            if any(fr._place(o, x, y, yaw, self.room, self.obstacles, front) for x, y, yaw in self._along_wall(k, w, d)):
                o.location.z += z_bottom
                bpy.context.view_layer.update()
                self.stats["furniture_added"] += 1
                return k
        bpy.data.objects.remove(o, do_unlink=True)
        return False

    def zone_workstation_pod(self, it) -> bool:
        """Bench workstations (user 2026-10-16 'an office is pods, not desks'): pods (identical) per the plan relation, a task chair at
        every seat (one chair model for the whole room), a mug or papers on some desks."""
        pod = {**it, "id": it["id"] + ":pod", "category": "pod_unit"}
        if pod.get("relation") in ("against_wall", "near_window", "row"):   # a pod seats both sides: the wall side keeps a chair + aisle
            pod["gap_m"] = max(pod.get("gap_m") or 0, 1.0)                 # (critic r1: half the bench seats had no chair)
        if not self.furniture(pod):
            return False
        for P, _ in self.copies.get(pod["id"], []):
            self._pod_chairs(P)
        self.ids.setdefault(it["id"], self.ids[pod["id"]])
        for P, _ in self.copies.get(pod["id"], []):
            for _ in range(self.rng.randint(1, 3)):
                self.lived_in({"category": self.rng.choice(("mug", "paper_stack", "small_plant")), "on": it["id"]})
        return True

    def _pod_chairs(self, P):
        """A task chair at every seat of pod P, one chair model for the whole room."""
        if getattr(self, "task_chair", None) is None:
            self.task_chair = self._make("desk_chair")
        chair0, cfront = self.task_chair
        if chair0 is None:
            return
        if True:
            for sx, sy, syaw in P.get("seats", []):
                p = P.matrix_world @ Vector((sx, sy, 0))
                c = chair0.copy(); c.data = chair0.data; bpy.context.scene.collection.objects.link(c)
                c.name = f"{rd._factory(chair0.name)}(pod).spawn_asset({self.stats['furniture_added']})"
                yaw = P.matrix_world.to_euler().z + syaw
                if fr._place(c, p.x, p.y, yaw, self.room, self.obstacles, cfront):
                    self._unsquare(c, cfront)
                    self.stats["furniture_added"] += 1
                else:
                    bpy.data.objects.remove(c, do_unlink=True)
        chair0.location = (1e4, 1e4, 0)

    def zone_meeting_set(self, it) -> bool:
        """A meeting room as a set: conference table in the middle, identical chairs around, a display on one wall, a whiteboard on
        another, a speakerphone on the table."""
        tid = it["id"] + ":table"
        if not self.furniture({"id": tid, "category": "meeting_table", "relation": "center"}):
            return False
        o, front = self.ids[tid]
        c, f, tw, td = _frame(o, front)
        seats = max(4, min(12, int(2 * max(tw, td) / 0.65)))
        self.pending_ids = set()
        self.furniture({"id": it["id"] + ":chairs", "category": "conference_chair", "relation": "around", "target": tid, "count": seats})
        wall = self._wall_mount("wall_display", 0.9)
        self._wall_mount("whiteboard", 0.9, avoid=wall)
        self.lived_in({"category": "speakerphone", "on": tid})
        for _ in range(self.rng.randint(1, 3)):
            self.lived_in({"category": self.rng.choice(("mug", "paper_stack")), "on": tid})
        self.ids.setdefault(it["id"], (o, front))
        return True

    def zone_glass_meeting_room(self, it) -> bool:
        """A glass-walled meeting room in the open office (reference: black-framed glass box with a long table, user 2026-10-16):
        two full-height glass partitions close off the corner farthest from the door, a glass door in one; the meeting set inside;
        then the box is an obstacle for everything outside."""
        from room_planner import proc_assets as pa
        x0, x1, y0, y1 = self.room.box
        doors = [self.walls[d["wall"]][0] + self.walls[d["wall"]][1] * d["at_m"] for d in self.doc.get("doors", []) if d["wall"] in self.walls]
        corners = [(x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)]
        cx, cy, ux, uy = max(corners, key=lambda c: min(((Vector((c[0], c[1], 0)) - d).length for d in doors), default=0))
        Wb = min(4.2, (x1 - x0) * 0.4); Db = min(3.2, (y1 - y0) * 0.5)   # ~13 m2: 4.6 x 3.6 took a quarter of a 70 m2 floor (r3)
        if Wb < 3.0 or Db < 2.6:
            return False
        H = max((self.room.wall.matrix_world @ Vector(c)).z for c in self.room.wall.bound_box) - self.room.z if self.room.wall else 2.8
        # partition A runs along x at y = cy + uy*Db (door in it), partition B along y at x = cx + ux*Wb
        a = pa.GlassPartitionFactory(0, L=Wb, H=H, door_at=(Wb / 2 - 0.7) * ux * -1).spawn_asset(self.stats["furniture_added"])
        a.rotation_euler = (0, 0, math.pi / 2); a.location = (cx + ux * Wb / 2, cy + uy * Db, self.room.z)
        b = pa.GlassPartitionFactory(1, L=Db, H=H).spawn_asset(self.stats["furniture_added"] + 1)
        b.location = (cx + ux * Wb, cy + uy * Db / 2, self.room.z)
        bpy.context.view_layer.update()
        self.stats["furniture_added"] += 2
        bx = sorted((cx, cx + ux * Wb)); by = sorted((cy, cy + uy * Db))
        tid = it["id"] + ":table"
        t = self._make("meeting_table")[0]
        if t is not None:
            t.scale.y = min(1.0, (Wb - 1.6) / max(t.dimensions[1], 0.1))
            if fr._place(t, (bx[0] + bx[1]) / 2, (by[0] + by[1]) / 2, 0.0, self.room, self.obstacles, fr.INF_FRONT):
                self.ids[tid] = (t, fr.INF_FRONT); self.stats["furniture_added"] += 1
                self.pending_ids = set()
                self.furniture({"id": it["id"] + ":chairs", "category": "conference_chair", "relation": "around", "target": tid,
                                "count": max(4, min(10, int(2 * t.dimensions[1] / 0.65)))})
                self.lived_in({"category": "speakerphone", "on": tid})
            else:
                bpy.data.objects.remove(t, do_unlink=True)
        # the glass room and its walls are now off limits for the open floor
        self.obstacles.append((bx[0], bx[1], by[0], by[1], 0, 0))
        self.ids.setdefault(it["id"], (a, fr.INF_FRONT))
        self.stats["glass_rooms"] = self.stats.get("glass_rooms", 0) + 1
        return True

    def zone_pantry_run(self, it) -> bool:
        """Office pantry: a run of base + upper cabinets with sink against a wall, a microwave and coffee machine on it, a fridge beside."""
        run = {**it, "id": it["id"] + ":run", "category": "pantry_unit", "relation": it.get("relation", "against_wall")}
        if not self.furniture(run):
            return False
        self.pending_ids = set()
        self.furniture({"id": it["id"] + ":fridge", "category": "beverage_fridge", "relation": "beside", "target": run["id"]})
        # appliances stand on the worktop at known slots: the generic top finder only sees the upper cabinets' top over a worktop
        # (critic r1: 'no sink, fridge or microwave visible'; both had logged 'no fit')
        R = self.ids[run["id"]][0]
        L = R.dimensions[1]
        for cat, y in (("microwave", L / 2 - 0.4), ("espresso_machine", L / 2 - 1.0)):
            y /= R.scale.y                                       # local units: a shrunk run is scaled along y
            o = self.spawn(_cls(catalog.LIVED_IN[cat]["src"]))
            if o is None:
                continue
            o.rotation_euler = R.rotation_euler.copy()           # both face local +X
            bpy.context.view_layer.update()
            f = fr.footprint(o); p = R.matrix_world @ Vector((0.0, y, 0.94))
            o.location += Vector((p.x - (f[0] + f[1]) / 2, p.y - (f[2] + f[3]) / 2, p.z - f[4]))
            bpy.context.view_layer.update()
            self.stats["lived_in_added"] = self.stats.get("lived_in_added", 0) + 1
        self.ids.setdefault(it["id"], self.ids[run["id"]])
        return True

    def coffee_bar(self, it) -> bool:
        """The service zone as one cluster (user 2026-10-16 'semantic islands'): a back-bar shelf against the wall, the counter 0.95 m in
        front of it on the same centre, an espresso machine and cake domes on the counter, the shelf stocked. Wall: it['wall'] or the
        longest free one."""
        sub = {"relation": "against_wall", "wall": it.get("wall")}
        back = {**sub, "id": it["id"] + ":backbar", "category": "backbar_shelf"}
        if not self.furniture(back):
            return False
        bo, bfront = self.ids[back["id"]]
        c, f, bw, bd = _frame(bo, bfront)
        ctr = {"id": it["id"] + ":counter", "category": "counter", "relation": "in_front_of", "target": back["id"], "gap_m": 0.95}
        self.pending_ids.discard(back["id"])
        if not self.furniture(ctr):
            return False
        self.fill({"on": back["id"], "category": "backbar_stock"}, _cls(catalog.LIVED_IN["backbar_stock"]["src"]))
        # bar cues (user 2026-10-16): the espresso machine always, then 4-6 of grinder / cup stacks / POS / pastry case / syrups / cakes
        bar = [("espresso_machine", 1)] + self.rng.sample([("grinder", self.rng.randint(1, 2)), ("cup_stack", 2), ("register", 1),
                                                           ("pastry_case", 1), ("syrup_rack", 1), ("cake_dome", 2)], self.rng.randint(4, 6))
        for cat, n in bar:
            self.lived_in({"category": cat, "on": ctr["id"], "count": n})
        self.ids.setdefault(it["id"], self.ids[ctr["id"]])
        return True

    def furniture(self, it) -> bool | None:
        _log(f"furniture {it.get('id')} {it['category']} {it['relation']}")
        src = catalog.FURNITURE[it["category"]]["src"]
        if src == "zone:coffee_bar":
            return self.coffee_bar(it)
        if src.startswith("zone:"):
            return getattr(self, "zone_" + src[5:])(it)
        """True placed, False no spot, None target not placed yet."""
        tgt = it.get("target")
        if it["relation"] in ("in_front_of", "beside", "under", "facing", "around") and tgt and tgt not in self.ids \
                and tgt != "room" and tgt in self.pending_ids:
            return None
        n = 2 if it.get("side") == "both" else max(1, it.get("count", 1))
        placed = 0
        self.row_k = getattr(self, "row_k", {})
        model = None                                             # copies of one item share one model (matching chairs, one rack type)
        for k in range(n):
            self.row_k[it["id"]] = k
            if model is not None and not model[0].children:
                o = model[0].copy(); o.data = model[0].data; bpy.context.scene.collection.objects.link(o)
                o.name = f"{rd._factory(model[0].name)}(copy{k}).spawn_asset({self.stats['furniture_added']})"; front = model[1]
                bpy.context.view_layer.update()
            else:
                o, front = self._make(it["category"])
            if o is None:
                return False
            w, d = (o.dimensions[1], o.dimensions[0]) if abs(front[0]) > 0.5 else (o.dimensions[0], o.dimensions[1])
            zone = self.rugzones if it["category"] == "rug" else self.obstacles
            spots = self.spots(it, w, d)
            pose = it.get("pose", "aligned")
            if pose == "aligned" and it["category"] in SEATS:
                pose = "natural"                                 # user 2026-10-16: chairs in neat rows look staged
            if pose == "pulled_out" and it["relation"] not in ("around", "in_front_of"):
                pose = "angled"                                  # pulled out from a wall = into it
            # the neat spot is the fallback; a seat tries 4 random natural poses per spot first (one try per spot left most chairs
            # neat: a turned chair's box hit its neighbour and the neat spot won)
            natural = pose == "natural"
            spots = spots if natural else [self._posed(x, y, yaw, pose) for x, y, yaw in spots] + spots
            if any(fr._place(o, x, y, yaw, self.room, zone, front) for x, y, yaw in spots):
                if natural:
                    self._unsquare(o, front)
                model = model or (o, front)
                placed += 1
                self.stats["furniture_added"] += 1
                self.ids.setdefault(it["id"], (o, front))
                self.copies = getattr(self, "copies", {})
                self.copies.setdefault(it["id"], []).append((o, front))   # a `row` of racks is one id: fill must reach every copy
            elif (it["category"] in SHRINKABLE and self._shrink_place(o, front, it, zone)) or (
                    # a free-standing table whose planned relation fits nowhere goes to the middle of the room (office r2: the break
                    # table 'in_front_of' the pantry run failed twice and the pantry had no table)
                    it["category"] in TABLES and it["relation"] != "center" and any(
                        fr._place(o, x, y, yaw, self.room, zone, front) for x, y, yaw in self.spots({**it, "relation": "center"}, w, d))):
                placed += 1
                self.stats["furniture_added"] += 1
                self.ids.setdefault(it["id"], (o, front))
                self.copies = getattr(self, "copies", {})
                self.copies.setdefault(it["id"], []).append((o, front))
            else:
                # Keep it for the next item of this category: an Infinigen plant takes 4-5 min to grow (2026-10-15). Leftovers go at
                # the end of the room (drop_spares).
                o.location = (1e4, 1e4, 0)
                self.spare = getattr(self, "spare", {})
                self.spare.setdefault(it["category"], []).append((o, front))
                break
        return placed > 0

    def _shrink_place(self, o, front, it, zone) -> bool:
        """A long counter / shelf that fits nowhere is shortened (x0.75 along its length, down to 1.4 m) and tried again: a 3.2 m
        counter on a 3.8 m wall with a door zone failed in 3 of 5 cafes (2026-10-16), and the spare reuse kept retrying it unchanged."""
        while o.dimensions[1] * 0.75 >= 1.4:
            o.scale.y *= 0.75
            bpy.context.view_layer.update()
            w, d = (o.dimensions[1], o.dimensions[0]) if abs(front[0]) > 0.5 else (o.dimensions[0], o.dimensions[1])
            if any(fr._place(o, x, y, yaw, self.room, zone, front) for x, y, yaw in self.spots(it, w, d)):
                self.stats["shrunk"] = self.stats.get("shrunk", 0) + 1
                return True
        return False

    def drop_spares(self):
        for objs in getattr(self, "spare", {}).values():
            for o, _ in objs:
                self.act.tidy.delete(o)
        self.spare = {}

    def _posed(self, x, y, yaw, pose):
        """(x, y, yaw) moved out of square: angled turns it, pulled_out also moves it back along its facing (away from its target)."""
        sgn = self.rng.choice((-1, 1))
        if pose == "angled":
            return x, y, yaw + sgn * math.radians(self.rng.uniform(8, 20))
        if pose == "pulled_out":
            d = self.rng.uniform(0.15, 0.35)
            return x - math.cos(yaw) * d, y - math.sin(yaw) * d, yaw + sgn * math.radians(self.rng.uniform(10, 25))
        if pose == "natural":                                    # a used seat: turned either way, often pulled back (user 2026-10-16:
            k = self.rng.random()                                # 'chairs all facing one way look awkward, rotate them randomly')
            ang = self.rng.uniform(15, 60) if k < 0.7 else self.rng.uniform(60, 150) if k < 0.8 else self.rng.uniform(5, 15)
            d = self.rng.uniform(0.1, 0.45) if self.rng.random() < 0.6 else 0.0
            return x - math.cos(yaw) * d, y - math.sin(yaw) * d, yaw + sgn * math.radians(ang)
        return x, y, yaw

    def _unsquare(self, o, front):
        """A seat that already stands neat is turned (and often pulled back) in place, kept only if clear. Placing neat first keeps
        every seat; turning first cost half the chairs, because a turned chair's box hit its neighbour (user 2026-10-16: 'chairs all
        facing one way look awkward, rotate them randomly')."""
        f0 = fr.footprint(o)
        if f0 in self.obstacles:
            self.obstacles.remove(f0)
        m0 = o.matrix_world.copy()
        loc0, rz0 = o.location.copy(), o.rotation_euler.z
        fwd = m0.to_3x3() @ Vector((*front, 0)); fwd.z = 0; fwd.normalize()
        for _ in range(6):
            x, y, yaw = self._posed(loc0.x, loc0.y, _yaw(fwd), "natural")
            o.location.x, o.location.y = x, y
            o.rotation_euler.z = rz0 + (yaw - _yaw(fwd))
            bpy.context.view_layer.update()
            f = fr.footprint(o)
            cs = [(f[0] + 0.05, f[2] + 0.05), (f[1] - 0.05, f[2] + 0.05), (f[0] + 0.05, f[3] - 0.05), (f[1] - 0.05, f[3] - 0.05)]
            if all(self.room.on_floor(cx, cy) for cx, cy in cs) and not any(fr._overlap(f, b) for b in self.obstacles):
                self.obstacles.append(f)
                self.stats["seats_turned"] = self.stats.get("seats_turned", 0) + 1
                return True
        o.location, o.rotation_euler.z = loc0, rz0
        bpy.context.view_layer.update()
        self.obstacles.append(f0)
        return False

    def adjust(self, it):
        """Turn or pull out an existing piece in place; kept only if it still stands on the floor clear of everything else."""
        if it["id"] not in self.ids:
            return
        o = self.ids[it["id"]][0]
        f0 = fr.footprint(o)
        if f0 in self.obstacles:
            self.obstacles.remove(f0)
        m0 = o.matrix_world.copy()
        fwd = o.matrix_world.to_3x3() @ Vector((*fr.INF_FRONT, 0)); fwd.z = 0; fwd.normalize()   # existing pieces are Infinigen
        x, y, yaw = self._posed(o.location.x, o.location.y, _yaw(fwd), it["pose"])
        o.location.x, o.location.y = x, y
        o.rotation_euler.z += yaw - _yaw(fwd)
        bpy.context.view_layer.update()
        f = fr.footprint(o)
        corners = [(f[0] + 0.05, f[2] + 0.05), (f[1] - 0.05, f[2] + 0.05), (f[0] + 0.05, f[3] - 0.05), (f[1] - 0.05, f[3] - 0.05)]
        if all(self.room.on_floor(cx, cy) for cx, cy in corners) and not any(fr._overlap(f, b) for b in self.obstacles):
            self.obstacles.append(f); self.stats["adjusted"] += 1
        else:
            o.matrix_world = m0; bpy.context.view_layer.update(); self.obstacles.append(f0)

    def _near_spots(self, tgt, w, d):
        """Floor spots around an object: the shirt by the bed, the basket next to the dresser."""
        o, front = self.ids[tgt]
        c, f, tw, td = _frame(o, front)
        out = []
        for ang in self.rng.sample(range(0, 360, 30), 12):
            v = Vector((math.cos(math.radians(ang)), math.sin(math.radians(ang)), 0))
            for k in (0.15, 0.35, 0.6):
                p = c + v * (max(tw, td) / 2 + max(w, d) / 2 + k)
                out.append((p.x, p.y, self.rng.uniform(-math.pi, math.pi)))
        return out

    def _item(self, cls, F, s, pose):
        """One small item on support s of F (lying if asked); returns it or None."""
        o = self.spawn(cls)
        if o is None:
            return None
        if self.act.try_place(o, F, s, self.rng, "any", yaw_sigma=math.radians(25) * (1 - self.t) + 0.05, lie=pose == "lying"):
            self.stats["placed"][cls.__name__] = self.stats["placed"].get(cls.__name__, 0) + 1
            return o
        self.act.tidy.delete(o); self.stats["no_room"] += 1
        return None

    def _drop_on(self, cls, host, pose, cat):
        """Hold the item just above the host's top at a seat-like spot and let settle() drop it (deleted if it does not stay)."""
        o = self.spawn(cls)
        if o is None:
            return
        F, front = host
        c, f, tw, td = _frame(F, front)
        if "Bed" in F.name:                                      # Infinigen bed front (+x) is the foot: cushions at the head
            at = c - f * td * 0.3 if cat == "cushion" else c + f * td * self.rng.uniform(0.0, 0.3)
        else:
            at = c + f * td * 0.15                               # in front of the backrest
        at += _left(f) * self.rng.uniform(-0.3, 0.3) * tw
        top = fr.footprint(F)[5]
        hit = bpy.context.scene.ray_cast(bpy.context.evaluated_depsgraph_get(), Vector((at.x, at.y, top + 0.01)), Vector((0, 0, -1)),
                                         distance=top + 0.01 - self.room.z)
        if not hit[0] or hit[1].z < self.room.z + 0.15:          # nothing to sit on at that spot
            self.act.tidy.delete(o); self.stats["no_room"] += 1
            print(f"[lived] {cat} on {rd._factory(F.name)}: no seat under drop point", flush=True)
            return
        bpy.context.view_layer.update()
        fo = fr.footprint(o)
        o.location += Vector((at.x - (fo[0] + fo[1]) / 2, at.y - (fo[2] + fo[3]) / 2, hit[1].z + 0.03 - fo[4]))
        bpy.context.view_layer.update()
        self.toss.append((o, host, pose, True))
        self.stats["placed"][cls.__name__] = self.stats["placed"].get(cls.__name__, 0) + 1
        print(f"[lived] {cat} on {rd._factory(F.name)} ({pose}): dropped", flush=True)

    FILL_MIX = {"cardboard_box": [("proc:CardboardBoxFactory", 4), ("abo:BOX", 1), ("inf:FoodBoxFactory", 1), ("inf:JarFactory", 0.5)],
                "storage_bin": [("abo:BOX", 4), ("proc:CardboardBoxFactory", 2), ("inf:FoodBoxFactory", 0.5)],
                # 40% cups/mugs, 20% coffee bags + equipment, 15% jars/bottles, 15% food, 10% plants (user 2026-10-16)
                "backbar_stock": [("inf:CupFactory", 3), ("proc:CupStackFactory", 1), ("inf:FoodBoxFactory", 1.5), ("proc:GrinderFactory", 0.5),
                                  ("inf:JarFactory", 1), ("inf:BottleFactory", 0.5), ("inf:BowlFactory", 1.5), ("abo:PLANTER", 1)],
                "groceries": [("inf:FoodBoxFactory", 3), ("inf:CanFactory", 2), ("inf:BottleFactory", 2), ("inf:JarFactory", 2)]}
    RACK_MAX_Z = 2.3                                             # rack top shelves are stocked too (the surface placer stops at 1.85 m)

    MERCH_HOSTS = ("GondolaFactory", "WallGondolaFactory")

    def merch(self, F, levels, mix):
        """Retail facings (user 2026-10-16: random mixes read as a stockroom): one product type per level and side, identical copies
        side by side along the shelf edge, front-facing, no jitter; both faces of a double gondola."""
        double = rd._factory(F.name) == "GondolaFactory"
        n = 0
        for s in levels:
            for side in ((1, -1) if double else (1,)):
                cls = self.rng.choices([m for m, _ in mix], [w for _, w in mix])[0]
                fac = cls(self.rng.randrange(1 << 20))          # one product, repeated: a facing
                y = s["y0"] + 0.02
                while y < s["y1"] - 0.05:
                    o = fac.spawn_asset(n)
                    bpy.context.view_layer.update()
                    w, d = o.dimensions[1], o.dimensions[0]
                    x = (s["x1"] - d / 2 - 0.02) if side == 1 else (s["x0"] + d / 2 + 0.02)
                    if self.act.try_place(o, F, s, self.rng, None, 0.0, rel_yaw=0.0 if side == 1 else math.pi,
                                          at=(x, y + w / 2), tries=1, jitter=0.0):
                        n += 1
                    else:
                        self.act.tidy.delete(o)
                    y += w + 0.012
        self.stats["placed"]["merch"] = self.stats["placed"].get("merch", 0) + n
        return n

    def fill(self, it, cls):
        mix = [(_cls(src), w) for src, w in self.FILL_MIX.get(it["category"], [])] or [(cls, 1)]
        n0 = sum(self.stats["placed"].values())
        for F, _ in getattr(self, "copies", {}).get(it["on"], [self.ids[it["on"]]]):
            bpy.context.view_layer.update()
            levels = self.act.supports(F, bpy.context.evaluated_depsgraph_get(), top_only=False)
            levels = [s for s in levels if (F.matrix_world @ Vector((0, 0, s["z"]))).z < self.RACK_MAX_Z and s["clear"] > 0.12]
            self.act.mark_occupied(F, levels, self.act.corners_of(rd._tops()))
            if rd._factory(F.name) in self.MERCH_HOSTS:
                self.merch(F, levels, mix)
                continue
            for s in levels:
                misses = 0
                while misses < 6 and len(s["placed"]) < 24:
                    c = self.rng.choices([m for m, _ in mix], [w for _, w in mix])[0]
                    misses = 0 if self._item(c, F, s, "placed") is not None else misses + 1
        _log(f"fill {it['on']} ({it['category']}): {sum(self.stats['placed'].values()) - n0} items on "
             f"{len(getattr(self, 'copies', {}).get(it['on'], []))} copies")

    def lived_in(self, it):
        cls = _cls(catalog.LIVED_IN[it["category"]]["src"])
        pose = it.get("pose", "placed")
        for _ in range(it.get("count", 1)):
            host = self.ids.get(it["on"])
            if host is None and it["on"] != "floor":             # its host was dropped: a lamp does not belong on the floor
                self.stats["no_host"] = self.stats.get("no_host", 0) + 1
                continue
            if host is None:
                o = self.spawn(cls)
                if o is None:
                    return
                w, d = o.dimensions[0], o.dimensions[1]
                spots = (self._near_spots(it["near"], w, d) if it.get("near") in self.ids else []) + self.spots({"relation": "corner"}, w, d)
                _log(f"{it['category']} on floor: {len(spots)} spots, {len(o.data.vertices) if o.type == 'MESH' else 0} verts")
                if any(fr._place(o, x, y, yaw, self.room, self.obstacles, fr.INF_FRONT) for x, y, yaw in spots):
                    if pose in ("tossed", "leaning", "lying"):
                        self.toss.append((o, None, "tossed", False))
                else:
                    self.act.tidy.delete(o); self.stats["no_room"] += 1
                continue
            F = host[0]
            if rd._factory(F.name) in SOFT:
                cat = it["category"]
                if cat == "throw_blanket" and "Bed" not in F.name:          # ponytail: rigid 2 m sheet on a sofa = a slab; cloth sim later
                    cls = _cls(catalog.LIVED_IN["cushion"]["src"])
                self._drop_on(cls, host, "leaning" if pose == "leaning" else "tossed", cat)
                continue
            shelf = rd._factory(F.name) in SHELVES
            bpy.context.view_layer.update()
            levels = self.act.supports(F, bpy.context.evaluated_depsgraph_get(), top_only=not shelf)
            levels = [s for s in levels if (F.matrix_world @ Vector((0, 0, s["z"]))).z < self.act.MAX_Z]
            if not levels:
                self.stats["no_room"] += 1
                print(f"[lived] {it['category']} on {rd._factory(F.name)}: no support level", flush=True)
                continue
            self.act.mark_occupied(F, levels, self.act.corners_of(rd._tops()))
            if it.get("fill"):                                   # stock every level of every copy: a working rack is full
                self.fill(it, cls)
                break
            s = self.rng.choice(levels) if shelf else max(levels, key=lambda s: len(s["cells"]))   # seat, bed top, table top
            o = self._item(cls, F, s, pose)
            print(f"[lived] {it['category']} on {rd._factory(F.name)} ({pose}): {'ok' if o else 'no fit'}", flush=True)
            if o is not None and pose in ("tossed", "leaning") and not shelf:
                self.toss.append((o, host, pose, False))

    def place_all(self, items) -> list:
        """Furniture items in plan order, a second round for those whose target came later. Returns [(item, reason)] not placed."""
        items = [it for it in items if it.get("id") not in self.ids]
        self.pending_ids = {it["id"] for it in items}
        failed = []
        for _ in range(2):
            later = []
            for it in items:
                r = self.furniture(it)
                if r is None:
                    later.append(it)
                    continue
                self.pending_ids.discard(it["id"])
                if not r:
                    failed.append((it, "no free spot for its relation (footprint off the floor or touching other furniture)"))
            items = later
            self.pending_ids = {it["id"] for it in items}
        failed += [(it, f"its target {it.get('target')} was never placed") for it in items]
        return failed

    def fill_empty(self, plan):
        """Cafes only: no large empty floor (user 2026-10-16: a busy cafe's usable floor is all seating, circulation, queue or
        counter). The largest empty region >= 3 m2 gets a cafe table with 2 (4 if >= 6 m2) chairs around it, until none is left;
        door zones and the counter front are already obstacles. A spot that fails is blocked so the next try moves on."""
        from room_planner import proc_assets
        if proc_assets.VENUE == "grocery":
            return self._fill_gondolas(plan)
        if proc_assets.VENUE == "open-office":
            return self._fill_pods(plan)
        if proc_assets.VENUE != "cafe":
            return
        ox, oy = self.doc["_origin"]
        added = 0
        for k in range(12):
            regs = [r for r in self.report(plan, [])["empty_floor"] if r["area_m2"] >= 3.0]
            if not regs:
                break
            r = regs[0]
            cx, cy = ox + sum(r["x_range"]) / 2, oy + sum(r["y_range"]) / 2
            tid = f"fill_t{k}"
            o, front = self._make("cafe_table")
            yaw = self.rng.choice((0.0, math.pi / 2)) + self.rng.uniform(-0.1, 0.1)
            if o is None or not fr._place(o, cx, cy, yaw, self.room, self.obstacles, front):
                if o is not None:
                    bpy.data.objects.remove(o, do_unlink=True)
                self.obstacles.append((cx - 0.4, cx + 0.4, cy - 0.4, cy + 0.4, 0, 0))   # move on
                continue
            self.ids[tid] = (o, front); self.stats["furniture_added"] += 1
            seats = 4 if r["area_m2"] >= 6.0 else 2
            self.pending_ids = set()
            self.furniture({"id": tid + "c", "category": "cafe_chair", "relation": "around", "target": tid, "count": seats})
            if self.rng.random() < 0.5:
                self.lived_in({"category": "mug", "on": tid})
            added += 1
        self.stats["filled_groups"] = self.stats.get("filled_groups", 0) + added
        _log(f"fill_empty: +{added} table groups")

    def _main_aisle(self, width=1.5):
        """A clear strip from the door straight across the room (user 2026-10-16: an office needs a circulation spine)."""
        for d in self.doc.get("doors", []):
            if d["wall"] not in self.walls:
                continue
            a, t_, n, length = self.walls[d["wall"]]
            p = a + t_ * d["at_m"]
            far = p + n * 20
            far.x = min(max(far.x, self.room.box[0]), self.room.box[1]); far.y = min(max(far.y, self.room.box[2]), self.room.box[3])
            w = t_ * (width / 2)
            xs = [p.x + w.x, p.x - w.x, far.x + w.x, far.x - w.x]; ys = [p.y + w.y, p.y - w.y, far.y + w.y, far.y - w.y]
            self.obstacles.append((min(xs), max(xs), min(ys), max(ys), 0, 0))
            self.stats["main_aisles"] = self.stats.get("main_aisles", 0) + 1
            return

    def _pod_grid(self):
        """Open office as a system (critic r1/r2 2026-10-16: pods planned 'corner'/'against_wall' lost their wall-side seats or failed,
        leaving sled chairs facing a wall): identical pods in aligned rows -- desks, a chair zone each side, a 1 m aisle between chair
        zones, the wall-side chair zone doubling as the walkway -- the main aisle from the door kept clear, a task chair at every seat.
        Rows are swept across the room in 0.25 m steps (a row pitch apart once one lands) and pods packed greedily along each row, so
        they flank the aisle and the glass room; both orientations are dry-run and the one that seats more wins (office r3: a fixed
        grid placed 0-1 pods on a 70 m2 floor)."""
        from room_planner import proc_assets as pa
        self._main_aisle()
        x0, x1, y0, y1 = self.room.box
        # pods sized to the room: 2 desks a side under 12 m, else 3 (a 4-desk 5.6 m pod fitted nowhere beside a glass room, office r3)
        P = pa.WorkstationPodFactory(self.rng.randrange(1 << 24), n=2 if max(x1 - x0, y1 - y0) < 12 else 3).spawn_asset(
            self.stats["furniture_added"])
        front = fr.INF_FRONT
        bpy.context.view_layer.update()
        L, D = P.dimensions[1], P.dimensions[0]                  # length along local y, two desks deep along local x
        # 0.8 m chair zones, 0.9 m between facing chair zones, outer chair zones back onto the wall, pods 1.0 m apart with 0.6 m end
        # clearance: with 0.85/1.0/+0.1/1.2/0.9 a 10.3 x 7 m floor held one pod beside its glass room and door aisle (office r3)
        hz, row_pitch = D / 2 + 0.8, D + 2 * 0.8 + 0.9
        mv = hz + 0.02

        def layout(along_x):
            # Each row position (0.25 m steps) gets its best packing: pods greedily from every start offset, 1.0 m between pod ends,
            # the start that seats most wins. Rows are then chosen by a 1-D DP so facing chair zones keep a 0.9 m aisle (row pitch).
            # Greedy-from-the-wall took a 1-pod row and lost the second row on a 10.3 x 7 m floor (office r3).
            U, V = ((x1 - x0), (y1 - y0)) if along_x else ((y1 - y0), (x1 - x0))

            def box(u, v):
                bx = (u - L / 2, u + L / 2, v - hz, v + hz)
                f = (x0 + bx[0], x0 + bx[1], y0 + bx[2], y0 + bx[3]) if along_x else (x0 + bx[2], x0 + bx[3], y0 + bx[0], y0 + bx[1])
                return (*f, self.room.z, self.room.z + 1.2)

            def ok(u, v):
                f = box(u, v)
                cs = [(f[0] + 0.05, f[2] + 0.05), (f[1] - 0.05, f[2] + 0.05), (f[0] + 0.05, f[3] - 0.05), (f[1] - 0.05, f[3] - 0.05)]
                return not any(fr._overlap(f, ob) for ob in self.obstacles) and all(self.room.on_floor(*c) for c in cs)

            us = [0.6 + L / 2 + 0.25 * k for k in range(int((U - 1.2 - L) / 0.25) + 1)]
            rows = []
            for k in range(int((V - 2 * mv) / 0.25) + 1):
                v = mv + 0.25 * k
                free = [u for u in us if ok(u, v)]
                best = []
                for s0 in free:
                    run, last = [], None
                    for u in free:
                        if u >= s0 and (last is None or u - last >= L + 1.0 - 1e-6):
                            run.append(u); last = u
                    best = max(best, run, key=len)
                rows.append((v, best))
            score, pick = [0] * (len(rows) + 1), [[] for _ in range(len(rows) + 1)]
            for i, (v, best) in enumerate(rows, 1):
                j = max([k for k in range(i) if k == 0 or rows[k - 1][0] <= v - row_pitch + 1e-6])
                take = score[j] + len(best)
                score[i], pick[i] = (take, pick[j] + [(v, best)]) if take > score[i - 1] else (score[i - 1], pick[i - 1])
            return [((f[0] + f[1]) / 2, (f[2] + f[3]) / 2) for v, best in pick[-1] for f in [box(u, v) for u in best]]

        plans = {ax: layout(ax) for ax in (True, False)}
        along_x = max(plans, key=lambda ax: (len(plans[ax]), ax == ((x1 - x0) >= (y1 - y0))))
        yaw = (0.0 if along_x else math.pi / 2) + math.pi / 2
        added = 0
        for x, y in plans[along_x]:
            o = P.copy(); o.data = P.data; bpy.context.scene.collection.objects.link(o)   # identical pods share one mesh
            o.name = f"WorkstationPodFactory(grid{added}).spawn_asset({self.stats['furniture_added']})"
            if not fr._place(o, x, y, yaw, self.room, self.obstacles, front):
                bpy.data.objects.remove(o, do_unlink=True)
                continue
            pid = f"grid_pod{added}"
            self.ids[pid] = (o, front); self.stats["furniture_added"] += 1; added += 1
            self._pod_chairs(o)
            for _ in range(self.rng.randint(1, 3)):
                self.lived_in({"category": self.rng.choice(("mug", "paper_stack", "small_plant")), "on": pid})
        bpy.data.objects.remove(P, do_unlink=True)              # the template; its mesh stays with the copies
        self.stats["grid_pods"] = added
        _log(f"pod grid: {added} pods ({len(plans[True])} along x / {len(plans[False])} along y, pod {L:.1f} x {D:.1f} m)")
        if added < 3:                                            # few pods: say what blocked the floor
            _log(f"pod grid sparse: box {[round(c, 2) for c in self.room.box]} obstacles {[[round(c, 1) for c in ob[:4]] for ob in self.obstacles]}")

    def _fill_pods(self, plan):
        """Open office: aligned pods (length along the long wall, no random yaw) into every empty region big enough, after the main
        aisle is reserved; each with its task chairs."""
        self._main_aisle()
        ox, oy = self.doc["_origin"]
        x0, x1, y0, y1 = self.room.box
        yaw = 0.0 if (x1 - x0) >= (y1 - y0) else math.pi / 2
        added = 0
        for k in range(8):
            regs = [r for r in self.report(plan, [])["empty_floor"] if r["area_m2"] >= 7.0]
            if not regs:
                break
            r = regs[0]
            cx, cy = ox + sum(r["x_range"]) / 2, oy + sum(r["y_range"]) / 2
            o, front = self._make("pod_unit")
            if o is None or not fr._place(o, cx, cy, yaw + math.pi / 2, self.room, self.obstacles, front):
                if o is not None:
                    bpy.data.objects.remove(o, do_unlink=True)
                self.obstacles.append((cx - 0.5, cx + 0.5, cy - 0.5, cy + 0.5, 0, 0))
                continue
            self._pod_chairs(o)
            added += 1
        self.stats["filled_pods"] = added
        _log(f"fill_pods: +{added}")

    def _fill_gondolas(self, plan):
        """Grocery sales floor: the largest empty region >= 3 m2 gets a double gondola parallel to the long wall, stocked with facings,
        until none is left (user 2026-10-16: an empty centre reads as a stockroom)."""
        ox, oy = self.doc["_origin"]
        x0, x1, y0, y1 = self.room.box
        yaw = 0.0 if (x1 - x0) >= (y1 - y0) else math.pi / 2          # gondola length (local y) along the long wall
        added = 0
        for k in range(10):
            regs = [r for r in self.report(plan, [])["empty_floor"] if r["area_m2"] >= 3.0]
            if not regs:
                break
            r = regs[0]
            cx, cy = ox + sum(r["x_range"]) / 2, oy + sum(r["y_range"]) / 2
            o, front = self._make("gondola")
            if o is None or not fr._place(o, cx, cy, yaw + math.pi / 2, self.room, self.obstacles, front):
                if o is not None:
                    bpy.data.objects.remove(o, do_unlink=True)
                self.obstacles.append((cx - 0.4, cx + 0.4, cy - 0.4, cy + 0.4, 0, 0))
                continue
            gid = f"fill_g{k}"
            self.ids[gid] = (o, front); self.copies = getattr(self, "copies", {}); self.copies[gid] = [(o, front)]
            self.stats["furniture_added"] += 1
            self.fill({"on": gid, "category": "groceries"}, _cls(catalog.LIVED_IN["groceries"]["src"]))
            added += 1
        self.stats["filled_gondolas"] = added
        _log(f"fill_gondolas: +{added}")

    def report(self, plan, failed) -> dict:
        """What the plan became, in the room frame: placed new items, items not placed (with why), empty floor, free wall."""
        ox, oy = self.doc["_origin"]
        rel = lambda v: [round(v.x - ox, 2), round(v.y - oy, 2)]  # noqa: E731
        placed = []
        for it in plan.get("furniture", []):
            if it["id"] in self.ids:
                c, f, w, d = _frame(*self.ids[it["id"]])
                placed.append({"id": it["id"], "category": it["category"], "center": rel(c), "size_wd": [round(w, 2), round(d, 2)],
                               "facing_deg": round(math.degrees(_yaw(f))) % 360})
        x0, x1, y0, y1 = self.room.box
        step = 0.4
        nx, ny = int((x1 - x0) / step), int((y1 - y0) / step)
        free = set()
        for i in range(nx):
            for j in range(ny):
                cx, cy = x0 + (i + 0.5) * step, y0 + (j + 0.5) * step
                cell = (cx - step / 2, cx + step / 2, cy - step / 2, cy + step / 2)
                if self.room.on_floor(cx, cy) and not any(fr._overlap(cell, b, m=0.0) for b in self.obstacles):
                    free.add((i, j))
        regions, seen = [], set()
        for c0 in sorted(free):
            if c0 in seen:
                continue
            comp, stack = [], [c0]
            seen.add(c0)
            while stack:
                i, j = stack.pop(); comp.append((i, j))
                for n in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                    if n in free and n not in seen:
                        seen.add(n); stack.append(n)
            area = len(comp) * step * step
            if area >= 1.0:
                xs = [x0 + (i + 0.5) * step for i, _ in comp]; ys = [y0 + (j + 0.5) * step for _, j in comp]
                regions.append({"area_m2": round(area, 1), "x_range": [round(min(xs) - ox, 1), round(max(xs) - ox, 1)],
                                "y_range": [round(min(ys) - oy, 1), round(max(ys) - oy, 1)]})
        regions.sort(key=lambda r: -r["area_m2"])
        free_wall = []
        for wid, (a, t_, n, length) in self.walls.items():
            run0 = None
            for k in range(int(length / 0.15) + 1):
                q = a + t_ * (k * 0.15) + n * 0.3
                ok = self.room.on_floor(q.x, q.y) and not any(b[0] <= q.x <= b[1] and b[2] <= q.y <= b[3] for b in self.obstacles)
                if ok and run0 is None:
                    run0 = k * 0.15
                if (not ok or k == int(length / 0.15)) and run0 is not None:
                    end = k * 0.15
                    if end - run0 >= 0.6:
                        free_wall.append({"wall": wid, "from_m": round(run0, 2), "to_m": round(end, 2)})
                    run0 = None
        return {"placed": placed, "not_placed": [{"id": it["id"], "category": it["category"], "relation": it["relation"],
                                                  "target": it.get("target") or it.get("wall"), "reason": why} for it, why in failed],
                "empty_floor": regions[:5], "free_floor_m2": round(len(free) * step * step, 1), "free_wall": free_wall}

    FIRST = ("glass_meeting_room",)                             # structure-like zones go before everything else

    REQUIRED_ZONE = {"break-room": ("pantry_run", "against_wall"), "meeting-room": ("meeting_set", "center"),
                     "cafe": ("coffee_bar", "against_wall"), "open-office": ("workstation_pod", "center")}

    CLUTTER = [("mug", 3), ("paper_stack", 3), ("pen_cup", 2), ("notebook", 2.5), ("takeaway_cup", 1.5), ("snack", 1.5),
               ("book_stack", 1), ("open_book", 0.7), ("phone", 1), ("bottle", 0.7), ("small_plant", 0.4)]
    CLUTTER_HOSTS = {"WorkstationPodFactory": None, "AboDeskFactory": (3, 6), "ConferenceTableFactory": (4, 8),
                     "BreakTableFactory": (2, 4), "SimpleDeskFactory": (3, 6), "OfficeDeskFactory": (4, 7)}

    def desk_clutter(self):
        """Hands on everything (user 2026-10-16: 'too clean -- leftover snacks, books, pencils, cups'): every desk, pod seat and table
        in an office room gets a handful of small things from CLUTTER (a pod 1.5-2.5 per seat)."""
        if self.doc.get("type") not in ("office", "open-office", "meeting-room", "break-room"):
            return
        names, weights = zip(*self.CLUTTER)
        hosts = {}
        for hid, (o, _) in list(self.ids.items()):
            f = rd._factory(o.name)
            if f in self.CLUTTER_HOSTS and o.name not in hosts:
                hosts[o.name] = hid
        added = 0
        for name, hid in hosts.items():
            o = self.ids[hid][0]
            rng_n = self.CLUTTER_HOSTS[rd._factory(o.name)]
            n = round(len(o.get("seats", [])) * self.rng.uniform(1.5, 2.5)) if rng_n is None else self.rng.randint(*rng_n)
            for _ in range(n):
                cat = self.rng.choices(names, weights)[0]
                if cat not in catalog.LIVED_IN:
                    continue
                self.lived_in({"category": cat, "on": hid})
                added += 1
        self.stats["desk_clutter"] = added
        _log(f"desk clutter: {added} items on {len(hosts)} hosts")

    def _in_vocab(self, plan):
        """A workplace plan keeps only categories offered for its room type: the planner still named sideboards and vases from memory
        after they left the office vocabulary (office loop r2, 2026-10-16). Homes are unchanged."""
        rt = self.doc.get("type", "")
        if rt not in catalog.WORK_ROOMS:
            return plan
        def ok(c, tab, default):
            return rt in tab.get(c, {}).get("rooms", default)
        drop = [f["category"] for f in plan.get("furniture", []) if not ok(f["category"], catalog.FURNITURE, [])] + \
               [f["category"] for f in plan.get("lived_in", []) if not ok(f["category"], catalog.LIVED_IN, ["home"])]
        if drop:
            _log(f"off-vocabulary for {rt}: {drop}")
            for c in drop:
                self.stats.setdefault("off_vocab", {})[c] = self.stats.get("off_vocab", {}).get(c, 0) + 1
        return {**plan, "furniture": [f for f in plan.get("furniture", []) if ok(f["category"], catalog.FURNITURE, [])],
                "lived_in": [f for f in plan.get("lived_in", []) if ok(f["category"], catalog.LIVED_IN, ["home"])]}

    def run(self, plan):
        # the zone that makes the room what it is: added when the plan left it out (a break room planned without its pantry, 2026-10-16)
        need = self.REQUIRED_ZONE.get(self.doc.get("type", ""))
        if need and not any(f["category"] == need[0] for f in plan.get("furniture", [])):
            plan = {**plan, "furniture": [{"id": "req_" + need[0], "category": need[0], "relation": need[1]}] + plan.get("furniture", [])}
            self.stats["zones_forced"] = self.stats.get("zones_forced", 0) + 1
            _log(f"required zone {need[0]} added")
        plan = self._in_vocab(plan)
        items = plan.get("furniture", [])
        first = [f for f in items if f["category"] in self.FIRST]
        rest = [f for f in items if f["category"] not in self.FIRST]
        if self.doc.get("type") == "open-office":               # pods are laid out as a grid, not per planned relation
            rest = [f for f in rest if f["category"] != "workstation_pod"]
            failed = self.place_all(first)
            self._pod_grid()
            failed += self.place_all(rest)
        else:
            failed = self.place_all(first + rest)
        rep = self.report(plan, failed) if self.revise is not None else None
        if rep is not None and (failed or any(r["area_m2"] >= 4 for r in rep["empty_floor"])):
            _log(f"report: not placed {[x['category'] for x in rep['not_placed']]}, empty {[r['area_m2'] for r in rep['empty_floor']]} m2")
            new = self.revise(plan, rep)
            if new:
                new = self._in_vocab(new)
                if self.doc.get("type") == "open-office":       # the grid owns the pods
                    new = {**new, "furniture": [f for f in new.get("furniture", []) if f["category"] != "workstation_pod"]}
                before = len(self.ids)
                failed = self.place_all(new.get("furniture", []))
                self.stats["revised_rooms"] = self.stats.get("revised_rooms", 0) + 1
                self.stats["revise_added"] = self.stats.get("revise_added", 0) + len(self.ids) - before
                plan = {**plan, "adjust": new.get("adjust", plan.get("adjust", [])), "lived_in": new.get("lived_in", plan.get("lived_in", []))}
                _log(f"revised: +{len(self.ids) - before} furniture, still not placed {[it['category'] for it, _ in failed]}")
        self.drop_spares()
        self.fill_empty(plan)
        for it, _ in failed:
            self.stats["plan_dropped"][it["category"]] = self.stats["plan_dropped"].get(it["category"], 0) + 1
        for it in plan.get("adjust", []):
            self.adjust(it)
        self.toss = []
        for it in plan.get("lived_in", []):
            self.lived_in(it)
        self.desk_clutter()
        settle(self.toss, self.room, self.rng, self.stats)


# ---- physics settle ----------------------------------------------------------------------------------------------------------------
SETTLE_FRAMES = 90
MAX_DRIFT_M = 0.6


PASSIVE_MAX_FACES = 3000


def _proxy(o, kind):
    """A light stand-in for Bullet: the convex hull (a few hundred verts) of an active item, a decimated copy of a passive one.
    Bullet got every vertex (58k-vert mug hull, 500k-face bed) and ran ~8 s per frame on an apartment (2026-10-15)."""
    import bmesh
    if kind == "ACTIVE":
        bm = bmesh.new(); bm.from_mesh(o.data)
        res = bmesh.ops.convex_hull(bm, input=bm.verts)
        bmesh.ops.delete(bm, geom=res["geom_interior"] + res["geom_unused"], context="VERTS")
        me = bpy.data.meshes.new(o.name + ".rbhull"); bm.to_mesh(me); bm.free()
        p = bpy.data.objects.new(o.name + ".rbproxy", me)
    else:
        p = bpy.data.objects.new(o.name + ".rbproxy", o.data)
        n = len(o.data.polygons)
        if n > PASSIVE_MAX_FACES:
            p.modifiers.new("dec", "DECIMATE").ratio = PASSIVE_MAX_FACES / n
    bpy.context.scene.collection.objects.link(p)
    p.matrix_world = o.matrix_world.copy()
    p.hide_render = True
    return p


def _configure(o, kind):
    rb = o.rigid_body
    rb.type = kind
    rb.collision_shape = "MESH" if kind == "PASSIVE" else "CONVEX_HULL"
    rb.mesh_source = "FINAL"                                     # the decimated proxy, not its full base mesh
    rb.friction, rb.restitution, rb.collision_margin = 0.9, 0.0, 0.002
    if kind == "ACTIVE":
        rb.mass, rb.linear_damping, rb.angular_damping = 0.4, 0.5, 0.7


def settle(toss, room, rng, stats):
    """Drop the tossed / leaning items (tilted, a few cm up) onto what is under them with Bullet, keep the settled pose.

    Everything within 1 m of a tossed item (and the room's floor and wall) is a passive collider. An item that drifts more than
    MAX_DRIFT_M, sinks under the floor or ends up non-finite goes back to its upright placement."""
    if not toss:
        return
    stats.setdefault("settled", 0); stats.setdefault("settle_reverted", 0)
    sc = bpy.context.scene
    frame0 = sc.frame_current
    start = {o.name: o.matrix_world.copy() for o, *_ in toss}
    drop = {o.name for o, _, _, d in toss if d}                  # dropped onto a soft host: no upright pose to go back to
    for o, host, pose, _ in toss:                                   # the throw: a tilt, a turn, a few cm of air
        tilt = math.radians(rng.uniform(25, 45) if pose == "leaning" else rng.uniform(15, 70))
        axis = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), 0)).normalized()
        loc = o.matrix_world.translation.copy()
        if pose == "leaning" and host is not None:               # slide back until it touches the backrest, top falling into it
            back = -(host[0].matrix_world.to_3x3() @ Vector((*host[1], 0))); back.z = 0; back.normalize()
            axis = back.cross(Vector((0, 0, -1))).normalized()
            f = fr.footprint(o)
            half = abs(Vector(((f[1] - f[0]) / 2, (f[3] - f[2]) / 2, 0)).dot(back))
            mid = Vector(((f[0] + f[1]) / 2, (f[2] + f[3]) / 2, (f[4] + f[5]) / 2))
            hit = bpy.context.scene.ray_cast(bpy.context.evaluated_depsgraph_get(), mid + back * (half + 0.005), back, distance=0.6)
            if hit[0]:
                swing = (f[5] - f[4]) / 2 * math.sin(tilt)        # the tilt about the centre swings the top this far back
                loc += back * max(0.0, (hit[1] - mid).dot(back) - half - 0.02 - swing)
        R = Matrix.Rotation(tilt, 4, axis) @ Matrix.Rotation(rng.uniform(-math.pi, math.pi), 4, "Z")
        o.matrix_world = Matrix.Translation(loc + Vector((0, 0, rng.uniform(0.04, 0.12)))) @ R @ o.matrix_world.to_3x3().to_4x4()
    bpy.context.view_layer.update()
    actives = [o for o, *_ in toss]
    boxes = [fr.footprint(o) for o in actives]
    passives = {room.floor.name: room.floor}
    if room.wall is not None:
        passives[room.wall.name] = room.wall
    for t in rd._tops():
        if t in actives or not any(fr._overlap(fr.footprint(t), b, m=0.5) for b in boxes):
            continue
        for x in [t, *t.children_recursive]:
            if x.type == "MESH":
                passives[x.name] = x
    if sc.rigidbody_world is None:
        bpy.ops.rigidbody.world_add()
    rbw = sc.rigidbody_world
    if rbw.collection is None:
        rbw.collection = bpy.data.collections.new("RigidBodyWorld")
    rbw.point_cache.frame_start, rbw.point_cache.frame_end = 1, SETTLE_FRAMES
    # Rigid bodies by collection link, not bpy.ops: an operator per object re-evaluates a whole apartment (minutes per settle).
    proxy = {o.name: _proxy(o, "PASSIVE") for o in passives.values() if o.type == "MESH"}
    proxy.update({o.name: _proxy(o, "ACTIVE") for o in actives if o.type == "MESH"})
    kinds = {proxy[o.name].name: "PASSIVE" for o in passives.values() if o.name in proxy}
    kinds.update({proxy[o.name].name: "ACTIVE" for o in actives if o.name in proxy})
    added = []
    for p in proxy.values():
        rbw.collection.objects.link(p); added.append(p)
    bpy.context.view_layer.update()                              # creates the rigid_body settings of everything linked
    for p in added:
        _configure(p, kinds[p.name])
    rbw.substeps_per_frame, rbw.solver_iterations = 5, 10
    _log(f"settle: {len(actives)} active (hull verts {sum(len(proxy[o.name].data.vertices) for o in actives if o.name in proxy)}), "
         f"{len(added) - len(actives)} passive proxies")
    for f in range(1, SETTLE_FRAMES + 1):
        sc.frame_set(f)
        if f in (1, 10, SETTLE_FRAMES):
            _log(f"settle frame {f}")
    final = {o.name: (proxy[o.name].matrix_world.copy() if o.name in proxy else start[o.name]) for o in actives}
    for p in added:
        rbw.collection.objects.unlink(p)
    coll, rbw.collection = rbw.collection, None
    bpy.data.collections.remove(coll)
    bpy.ops.rigidbody.world_remove()
    sc.frame_set(frame0)
    for p in proxy.values():
        me = p.data if p.data.name.endswith(".rbhull") else None
        bpy.data.objects.remove(p, do_unlink=True)
        if me is not None:
            bpy.data.meshes.remove(me)
    for o in actives:
        m = final[o.name]
        ok = all(math.isfinite(v) for row in m for v in row) and (m.translation.xy - start[o.name].translation.xy).length < MAX_DRIFT_M
        o.matrix_world = m if ok else start[o.name]
        bpy.context.view_layer.update()
        if ok and fr.footprint(o)[4] < room.z - 0.02:            # through the floor
            o.matrix_world, ok = start[o.name], False
        stats["settled" if ok else "settle_reverted"] += 1
        if not ok and o.name in drop:
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()


SYSTEM_PY = "/root/miniconda3/bin/python3"                       # has the anthropic SDK; Blender's python does not
TOOLS = str(Path(__file__).resolve().parents[1])


def llm_revise(room_doc, seed):
    """(plan, report) -> revised plan via room_planner/revise.py in the system python; None on any failure (keep the first pass)."""
    import subprocess
    import tempfile

    def call(plan, report):
        payload = {k: v for k, v in room_doc.items() if not k.startswith("_")}
        payload["existing"] = [{k: v for k, v in e.items() if not k.startswith("_")} for e in room_doc["existing"]]
        with tempfile.TemporaryDirectory() as d:
            req, out = Path(d) / "req.json", Path(d) / "out.json"
            req.write_text(json.dumps({"room": payload, "plan": plan, "report": report, "seed": seed}))
            r = subprocess.run([SYSTEM_PY, "-m", "room_planner.revise", str(req), str(out)], cwd=TOOLS, capture_output=True,
                               text=True, timeout=600)
            if r.returncode != 0 or not out.is_file():
                _log(f"revise failed ({r.returncode}): {r.stderr[-300:]}")
                return None
            return json.loads(out.read_text())
    return call


def realize(plans, rng, stats, spawn, act, revise=True):
    from room_planner import proc_assets, styles
    proc_assets.STYLE.clear()
    proc_assets.VENUE = plans.get("venue") or ""
    proc_assets.STYLE.update(plans.get("style_spec") or styles.get(plans.get("venue") or "", plans.get("style") or "") or {})
    """plans: plan_scene.py output; act: the activity pass module (supports, put, mark_occupied, corners_of, MAX_Z, tidy)."""
    stats.setdefault("furniture_added", 0); stats.setdefault("plan_dropped", {}); stats["planned_rooms"] = 0; stats.setdefault("adjusted", 0)
    rooms = rd._rooms()
    scene = bpy.context.scene
    obstacles, rugzones = fr.obstacles(rd._tops())
    for rid, entry in sorted(plans["rooms"].items()):
        parts = rooms.get(rid)
        if not parts or "floor" not in parts:
            continue
        room = fr.Room(rid, parts, scene, bpy.context.evaluated_depsgraph_get())
        before = stats["furniture_added"]
        RoomRealizer(entry["room"], room, rng, stats, spawn, act, obstacles, rugzones,
                     float(entry["plan"].get("tidiness", 0.6)),
                     revise=llm_revise(entry["room"], int(plans.get("seed", 0))) if revise else None).run(entry["plan"])
        stats["planned_rooms"] += 1
        print(f"[plan] {rid}: +{stats['furniture_added'] - before} furniture ({entry['plan'].get('occupant', '')})", flush=True)

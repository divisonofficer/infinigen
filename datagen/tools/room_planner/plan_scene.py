"""Plan every room of a scene with Claude.

    python -m room_planner.plan_scene rooms.json --out plans.json [--seed N] [--types living-room,bedroom,dining-room] [--dry-run]

Needs ANTHROPIC_API_KEY for a live call; --dry-run prints the first request instead. Plans are cached (client.CACHE).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from room_planner import client  # noqa: E402

PLANNED = ("living-room", "bedroom", "dining-room", "warehouse", "garage", "office", "open-office", "meeting-room", "break-room", "cafe", "grocery",
           "clinic-reception", "exam-room", "dental-room", "physio-room", "convenience", "boutique", "pharmacy")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("rooms", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--types", default=",".join(PLANNED))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--venue", help="relabel every room as this type (a single-room layout used as a cafe / grocery store)")
    ap.add_argument("--style", help="venue style preset (room_planner/styles.py), e.g. cafe: nordic_bakery, industrial_brick")
    ap.add_argument("--reference", type=Path, help="venue spec from room_planner.reference: its brief, must-haves and images steer the plan")
    ap.add_argument("--room-venues", type=Path, help="{room name: venue} json: a multi-room floor whose rooms take venue rules (clinic, "
                                                     "cafe); rooms not in the map keep their own type (user 2026-10-16: floor scenes)")
    a = ap.parse_args()
    types = set(a.types.split(","))
    doc = json.loads(a.rooms.read_text())
    spec = json.loads(a.reference.read_text()) if a.reference else None
    images = spec.get("images") if spec else None  # hand-written briefs carry no images
    out = {"scene": doc["scene"], "model": client.MODEL, "prompt_version": client.PROMPT_VERSION, "seed": a.seed, "rooms": {},
           "venue": a.venue, "style": a.style, "style_spec": spec}
    room_venues = json.loads(a.room_venues.read_text()) if a.room_venues else {}
    out["room_venues"] = room_venues
    for room in doc["rooms"]:
        if a.venue:
            room = {**room, "type": a.venue}
        if room.get("id") in room_venues or room.get("name") in room_venues:
            room = {**room, "type": room_venues.get(room.get("id")) or room_venues[room.get("name")]}
        if a.style:
            from room_planner import styles
            room = {**room, "style": styles.get(a.venue, a.style)["brief"]}
        if a.reference and (len(doc["rooms"]) == 1 or not spec.get("venue") or room["type"] == spec["venue"]):   # on a floor the kit's
            # brief and must-haves belong to its own venue's room, office floors too (floor C r3: the open-office brief made the pantry a
            # hot-desk area -- 1 of 15 items fit, a bare room)
            room = {**room, "style": spec["brief"], "must_have": spec.get("must_have", []), "reference_ids": spec.get("reference_ids", [])}
            # to its own venue's room (floor G: the café brief put a coffee bar and tables in the storage room, reception's in exam rooms)
        if room_venues and room["type"] in ("utility", "closet") and room["id"] not in room_venues:
            # floors: service rooms no venue covers get a fixed fit-out (floor E: the sterilisation room rendered empty)
            clinic = any(v in ("clinic-reception", "exam-room", "dental-room", "physio-room") for v in room_venues.values())
            furn = ([{"id": "run", "category": "medical_cabinet", "relation": "against_wall"},          # sterilisation / supply: counter
                     {"id": "racks", "category": "storage_rack", "relation": "against_wall", "away_from": "run"}]   # run + stocked rack
                    if clinic and room["type"] == "utility" else
                    [{"id": "lockers", "category": "locker", "relation": "against_wall", "count": 2},
                     {"id": "bench", "category": "changing_bench", "relation": "in_front_of", "target": "lockers", "gap_m": 0.6},
                     {"id": "mirror", "category": "mirror", "relation": "against_wall", "away_from": "lockers"}]
                    if room["type"] == "closet" else
                    [{"id": "racks", "category": "storage_rack", "relation": "against_wall", "count": 2}])
            stock = ([{"category": "cardboard_box", "on": "racks", "fill": True}] if any(f["id"] == "racks" for f in furn) else   # every level
                                                                 # (floor E3 r3: one box tried, 'no fit', a bare rack)
                     [{"category": "towel_stack", "on": "bench"}, {"category": "laundry_basket", "on": "floor"}]   # a changing room in use
                     if furn[0]["id"] == "lockers" else [])                                                       # (floor F r2: use 3, 3 of 3)
            out["rooms"][room["id"]] = {"plan": {"occupant": "staff", "tidiness": 0.8, "lived_in": stock, "furniture": furn, "fixed": True}, "room": room}
            continue
        if room["type"] == "restroom":
            # floors: a restroom gets fixed sanitary ware, no LLM call (the solver that would fit it is off on floors, 2026-10-16)
            # always one open WC: the stall factory's panels read as 'loose boards at odd angles' in every floor (A, B, D3, E3, J, 3/3
            # each), while the open WC + basin restrooms scored 7 on function; a large room gets a second basin, not a second stall
            n_basin = 2 if room.get("area_m2", 0) >= 18 else 1
            plan = {"occupant": "staff and visitors", "tidiness": 0.8, "lived_in": [], "fixed": True,
                    "furniture": [{"id": "wc", "category": "wc", "relation": "against_wall"},
                                  {"id": "basin", "category": "wash_basin", "relation": "beside", "target": "wc", "gap_m": 0.4, "count": n_basin}]}
            # (an open WC with its basin on the far wall read as 'a toilet alone in an empty room' -- floor A2 r4; fixtures go together)
            out["rooms"][room["id"]] = {"plan": plan, "room": room}
            continue
        if room["type"] not in types:
            continue
        payload = {k: v for k, v in room.items() if not k.startswith("_")}
        payload["existing"] = [{k: v for k, v in e.items() if not k.startswith("_")} for e in room["existing"]]
        plan = client.plan_room(payload, a.seed, dry_run=a.dry_run, images=images)
        if a.dry_run:
            print(json.dumps(plan["request"], indent=1)[:6000])
            return 0
        out["rooms"][room["id"]] = {"plan": plan, "room": room}        # the realizer needs the room's origin and object names
        print(json.dumps({"room": room["id"], "furniture": len(plan.get("furniture", [])), "lived_in": len(plan.get("lived_in", [])),
                          "occupant": plan.get("occupant")}, ensure_ascii=False), flush=True)
    a.out.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

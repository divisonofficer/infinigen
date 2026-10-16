"""Room furnishing plans from Claude (Anthropic API), cached on disk.

A room description (extract_rooms.py) goes in; a plan comes back as a submit_room_plan tool call (forced where the model allows it,
else tool_choice auto + one nudge), so the reply is always JSON of the schema below. Plans are cached by sha256 of (prompt version, model, seed, room), so a rerun is free and reproducible; every call's
token usage is appended to usage.jsonl. The key is read from ANTHROPIC_API_KEY or the user's mode-600 key file, never printed or logged.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

from . import catalog

MODEL = os.environ.get("ROOM_PLANNER_MODEL", "claude-sonnet-5-5")
PROMPT_VERSION = "room-plan-v11"                                # v9: office system (pods, meeting set, pantry) (v8: retail)
NO_FORCED_TOOL = {"claude-sonnet-5-5", "claude-opus-5-5"}      # measured 2026-10-15 (haiku-5-5, sonnet-5 accept it)
CACHE = Path(os.environ.get("ROOM_PLANNER_CACHE", "/jarvis/project/robomituba/out/room_planner_cache"))

PLAN_TOOL = {
    "name": "submit_room_plan",
    "description": "Submit the furnishing plan for one room.",
    "input_schema": {
        "type": "object",
        "required": ["occupant", "narrative", "tidiness", "furniture", "lived_in", "notes"],
        "properties": {
            "occupant": {"type": "string", "description": "who lives here, one line (e.g. 'couple in their 30s, one works from home')"},
            "narrative": {"type": "string", "description": "the moment the room is seen at, one line (e.g. 'Sunday late morning, breakfast "
                                                           "in front of the TV, laundry not put away')"},
            "tidiness": {"type": "number", "minimum": 0, "maximum": 1, "description": "0 messy .. 1 showroom tidy"},
            "furniture": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "category", "relation"],
                    "properties": {
                        "id": {"type": "string"},
                        "category": {"type": "string", "enum": sorted(catalog.FURNITURE)},
                        "relation": {"type": "string", "enum": sorted(catalog.RELATIONS)},
                        "target": {"type": "string", "description": "existing object id, new item id, wall id or 'room'"},
                        "wall": {"type": "string"},
                        "side": {"type": "string", "enum": ["left", "right", "both"]},
                        "gap_m": {"type": "number"},
                        "count": {"type": "integer", "minimum": 1, "maximum": 8},
                        "facing": {"type": "string"},
                        "pose": {"type": "string", "enum": sorted(catalog.FURNITURE_POSES)},
                        "why": {"type": "string"},
                    },
                },
            },
            "adjust": {
                "type": "array",
                "description": "existing furniture moved out of its neat pose (chairs pulled out from the table, an armchair angled)",
                "items": {"type": "object", "required": ["id", "pose"],
                          "properties": {"id": {"type": "string"}, "pose": {"type": "string", "enum": ["angled", "pulled_out"]}}},
            },
            "lived_in": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["category", "on"],
                    "properties": {
                        "category": {"type": "string", "enum": sorted(catalog.LIVED_IN)},
                        "on": {"type": "string", "description": "an existing object id or new furniture id, or 'floor'"},
                        "near": {"type": "string", "description": "for on='floor': the object id it lies next to"},
                        "fill": {"type": "boolean", "description": "stock every shelf level of the host until it is full"},
                        "pose": {"type": "string", "enum": sorted(catalog.ITEM_POSES)},
                        "count": {"type": "integer", "minimum": 1, "maximum": 4},
                    },
                },
            },
            "notes": {"type": "string"},
        },
    },
}

def _vocab(work: bool) -> str:
    """Catalog lines for a home room or a workplace room (each only sees the categories made for it)."""
    def ok(rooms):
        if "_internal" in rooms:                                 # parts of a zone, placed by the realizer, never planned directly
            return False
        return bool(set(rooms) & catalog.WORK_ROOMS) if work else bool(set(rooms) - catalog.WORK_ROOMS)
    fur = [f"- {k}: {v['size'][0]} x {v['size'][1]} x {v['size'][2]} m, rooms {', '.join(v['rooms'])}"
           for k, v in catalog.FURNITURE.items() if ok(v["rooms"])]
    liv = [f"- {k}: on {', '.join(v['on'])}" for k, v in catalog.LIVED_IN.items() if ok(v.get("rooms", ["home"]))]
    return f"""FURNITURE (geometry source, typical size W x D x H m):
{chr(10).join(fur)}

SMALL items (on furniture or the floor; `fill`: true stocks every shelf level of a rack until it is full):
{chr(10).join(liv)}

RELATIONS:
{chr(10).join(f"- {k}: {v}" for k, v in catalog.RELATIONS.items())}

FURNITURE POSES:
{chr(10).join(f"- {k}: {v}" for k, v in catalog.FURNITURE_POSES.items())}

ITEM POSES:
{chr(10).join(f"- {k}: {v}" for k, v in catalog.ITEM_POSES.items())}"""


_INTRO = """You get one room as JSON: type, floor area, the floor outline (metres, room frame), walls (id, endpoints, length, free stretches
not blocked by doors, windows or furniture), doors, windows, and the furniture already there (id, category, centre, size, yaw).
Keep everything already there (you may only turn or pull out existing pieces, via `adjust`)."""

SYSTEM = f"""You furnish rooms of procedurally generated apartments so they look like a real home someone lives in, not a showroom.
Prompt version {PROMPT_VERSION}.

{_INTRO} Add what this room is missing for the life of its occupant, using ONLY these categories:

{_vocab(False)}

Rules:
- Fill the room the way people actually do: a living room of 25 m2 has a sofa, a coffee table, one or two armchairs, a TV wall, a rug,
  lamps and a plant -- not one sofa in an empty floor. A dining table gets as many chairs as fit (usually 4-6).
- Keep a walkway of at least 0.8 m and the area in front of every door free. Never block a window with tall furniture.
- Prefer walls with a long free stretch for big pieces. Group furniture into functional clusters (a seating group facing a TV, a
  reading corner with an armchair, lamp and side table, a desk under a window).
- People live here: a real room is never square and upright everywhere. Pick a narrative (the moment the room is seen at) and let
  it cause the disorder: chairs pulled out after a meal or angled toward the TV, cushions tossed against the backrest, a book left
  lying open on the sofa arm, a shirt dropped on the bed, a towel on the floor by the bathroom door, a laundry basket with clothes
  next to it. About (1 - tidiness) of the lived-in items and a few furniture pieces should be out of their neat pose; tidy rooms
  still have one or two. Every out-of-place thing needs a reason in the narrative -- never random chaos, never everything messy.
- Return the plan by calling submit_room_plan exactly once.
"""

SYSTEM_WORK = f"""You furnish rooms of procedurally generated buildings so they look like real workplaces in daily use (a small
business's warehouse, a garage, an office floor), not an empty shell and not a catalogue photo.
Prompt version {PROMPT_VERSION}.

{_INTRO} The `occupant` is the business or crew using it. Add what this room needs for its work, using ONLY these categories:

{_vocab(True)}

Rules:
- A warehouse is mostly storage: racks in rows along the walls and in parallel free-standing aisles (`row` with `gap_m`), aisles
  1.2-1.8 m wide so a cart passes, pallets and box piles in a staging area near the door, a workbench with a stool for packing.
  A 60 m2 warehouse holds 8-16 racks; fill most of them (`fill`: true with cardboard_box or storage_bin) and leave a few half
  empty. Keep the front of every door clear (1.2 m).
- An office is a workplace system, not desks in a room (no dining chairs, sofas, armchairs, sideboards, rugs or home decor):
  * open-office: 2-6 `workstation_pod`s (the realizer lays them out on a grid itself) in `row`s parallel to the window wall (each pod brings desks, divider, monitors and a task
    chair per seat), 1.5 m aisles between pod rows, a main aisle from the door, filing_cabinets/bookshelves along the inner walls,
    a whiteboard on a free wall, plants by the windows.
  * meeting-room: ONE `meeting_set` (it brings the conference table, matching chairs, wall display, whiteboard and speakerphone);
    add a plant at most; nothing else.
  * office (private): 1 office_desk facing the door or under the window with 1 desk_chair, 2 conference_chairs as guest chairs in
    front of the desk (facing it), a filing_cabinet and a bookshelf behind it, a whiteboard, a plant; nothing else.
  * break-room (pantry): ONE `pantry_run` against a wall (cabinets, sink, microwave, coffee, fridge), a high break_table with
    bar_stools or a break_table with 4 break_chairs, a floor_plant; nothing else (no sofa, coffee table or lamp).
- If the room JSON has a `style`, it describes the look the owner chose: follow it (which pieces, how many, where).
- A cafe is built around its service zone: place ONE `coffee_bar` (against_wall, usually the back wall opposite the glass) -- it
  brings the back-bar shelf (stocked), the counter in front of it, the espresso machine and cakes; put a beverage_fridge beside it
  and a menu_board on a free wall. Do not add a separate counter or backbar_shelf. Pilasters/columns already in the room are
  structure: furnish around them (a table group between two pilasters, the banquette along a wall bay). Seating is 4-8 table groups spread over the floor
  with 0.9 m aisles: a cafe_table with 2-4 cafe_chairs `around` it; one wall can be a banquette (a sofa against the wall) with 2-3
  cafe_tables in front of it and chairs opposite. No sofas or armchairs elsewhere -- at most 2 armchairs, and only if the
  style asks for them; a cafe is mostly small tables and dining chairs. Plants by the windows. Cups, plates and glasses on
  the tables customers just left, cake on a plate here and there.
- Fill the cafe like a busy one: about one seat per 1.6 m2 of floor (a 60 m2 cafe seats ~36: 8-10 table groups plus the window
  bar and banquette). Apart from the aisle in front of the counter and the door clearance, leave no empty floor patch larger
  than 4 m2 -- put a table group, a plant cluster or a banquette there.
- A shop-front cafe (a window spanning most of one wall) has a window_bar along that glass (`row` on that wall, gap_m 0) with
  bar_stools in front of it (`row`, gap_m 0.45), and small plants and cups on the bar.
- A grocery store is a sales floor, not a stockroom: 2-4 double-sided `gondola` aisles through the middle of the floor (`row`s
  parallel to the long wall, `gap_m` about 2.2, 3.9, 5.6 ... so aisles are 1.2-1.5 m), `wall_gondola` rows along the side walls,
  beverage_fridges along the back wall and 1-2 chest_freezers, a checkout `counter` with a `register` on it next to the door and
  baskets stacked by the door. Every gondola stocked (`groceries` with `fill`: true: the shelves get neat facings, one product
  per shelf). No storage racks or box piles on the sales floor.
- Workplaces are in use, not tidy: a ladder leaning by a rack, a cart parked in an aisle, a box pile half broken down, a box on the
  floor waiting to be shelved, bottles and a mug on the bench. Tie the disorder to a narrative (the moment it is seen at: a delivery
  just arrived, the end of a shift) -- never random chaos.
- Return the plan by calling submit_room_plan exactly once.
"""


KNOWLEDGE = Path(__file__).resolve().parent / "design_knowledge.json"


def learned_rules(room_type: str) -> str:
    """Prompt rules learned by the render -> critic loop (design_knowledge.json, applied_to contains 'prompt', not rejected)."""
    try:
        rules = json.loads(KNOWLEDGE.read_text())["rules"]
    except (OSError, ValueError, KeyError):
        return ""
    lines = [f"- {r['rule']}" for r in rules if "prompt" in r.get("applied_to", "") and r.get("status") != "rejected"
             and (room_type in r.get("rooms", []) or "*" in r.get("rooms", []))]
    return ("\nLearned rules (validated on earlier renders):\n" + "\n".join(lines) + "\n") if lines else ""


def system_for(room_type: str) -> str:
    return (SYSTEM_WORK if room_type in catalog.WORK_ROOMS else SYSTEM) + learned_rules(room_type)


KEY_FILE = Path(os.environ.get("ROOM_PLANNER_KEY_FILE", str(Path.home() / ".config/robomituba/anthropic_key")))


def _api_key() -> str:
    """ANTHROPIC_API_KEY, else the mode-600 key file the user wrote (never printed or logged)."""
    key = os.environ.get("ANTHROPIC_API_KEY") or (KEY_FILE.read_text().strip() if KEY_FILE.is_file() else "")
    if not key:
        raise RuntimeError(f"no API key: set ANTHROPIC_API_KEY or write it to {KEY_FILE} (chmod 600)")
    return key


def _key(room: dict, seed: int) -> str:
    # learned rules are part of the prompt, so part of the key: a new rule re-plans, an unchanged rulebook reuses the cache
    blob = json.dumps({"v": PROMPT_VERSION, "m": MODEL, "seed": seed, "room": room, "rules": learned_rules(room.get("type", ""))},
                      sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:24]


def request(room: dict, seed: int, images=None) -> dict:
    """The Messages API request for one room (what --dry-run prints). images: reference image paths shown with the room."""
    return {
        "model": MODEL,
        "max_tokens": 4000,
        "system": [{"type": "text", "text": system_for(room.get("type", "")), "cache_control": {"type": "ephemeral"}}],
        "tools": [PLAN_TOOL],
        # Sonnet 5.5 rejects a forced tool choice ("tool"/"any", 400); Sonnet 5 takes it. Where it is refused the prompt asks for the
        # call and plan_room nudges once more.
        "tool_choice": {"type": "auto"} if MODEL in NO_FORCED_TOOL else {"type": "tool", "name": "submit_room_plan"},
        "messages": [{"role": "user", "content": (_images(images) + [{"type": "text", "text": "Reference views of the space to furnish "
                                                     "this room after (match its zones, materials and furniture):"}] if images else []) +
                      [{"type": "text", "text": f"Variation seed {seed}. Room:\n" + json.dumps(room, indent=1)}]}],
    }


def _images(paths):
    from room_planner.reference import image_blocks
    return image_blocks(paths)


def plan_room(room: dict, seed: int = 0, *, dry_run: bool = False, images=None) -> dict:
    """The plan for one room: from the cache, or from the API (then cached). With reference images the room carries their ids
    (spec reference_ids), so they are part of the cache key."""
    req = request(room, seed, images)
    if dry_run:
        return {"dry_run": True, "request": req}
    return _submit(req, _key(room, seed), room, seed)


REVISE_NOTE = """Placement result for your plan (room frame, metres). Revise the plan:
- keep every placed item (same id, same entry);
- for each item in `not_placed`, move it (another wall, relation or target) or drop it -- the reason says why it failed;
- use `empty_floor` regions and `free_wall` stretches for what the room still lacks, keeping 0.8 m walkways and door fronts free;
- lived_in entries may now reference new ids.
Submit the complete revised plan with submit_room_plan."""


def revise_room(room: dict, plan: dict, report: dict, seed: int = 0, images=None) -> dict:
    """One feedback round: the realizer's report goes back as the result of the plan's own tool call; the reply is a full plan."""
    req = request(room, seed, images)
    tid = "toolu_room_plan_v1"
    req["messages"] = req["messages"] + [
        {"role": "assistant", "content": [{"type": "tool_use", "id": tid, "name": "submit_room_plan", "input": plan}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tid,
                                      "content": REVISE_NOTE + "\n" + json.dumps(report, indent=1)}]},
    ]
    blob = json.dumps({"v": PROMPT_VERSION, "m": MODEL, "seed": seed, "room": room, "plan": plan, "report": report}, sort_keys=True)
    return _submit(req, "rev-" + hashlib.sha256(blob.encode()).hexdigest()[:24], room, seed)


def _submit(req: dict, key: str, room: dict, seed: int, tool: str = "submit_room_plan") -> dict:
    """The API call behind plan_room / revise_room: cached by key, nudged once if it answers in prose, usage logged."""
    path = CACHE / f"{key}.json"
    if path.is_file():
        return json.loads(path.read_text())["plan"]
    import anthropic                                           # only needed for a live call
    # gzip only: this env's zstd/brotli decoder does not match httpx2's call (TypeError: process() takes no keyword arguments)
    client = anthropic.Anthropic(api_key=_api_key(), max_retries=4, default_headers={"Accept-Encoding": "gzip, deflate"})
    t0 = time.time()
    msgs = [client.messages.create(**req)]
    plan = next((b.input for b in msgs[-1].content if b.type == "tool_use" and b.name == tool), None)
    if plan is None:                                           # it answered in prose: ask once more for the call
        req2 = {**req, "messages": req["messages"] + [{"role": "assistant", "content": msgs[-1].content},
                                                      {"role": "user", "content": f"Please submit it by calling {tool}."}]}
        msgs.append(client.messages.create(**req2))
        plan = next(b.input for b in msgs[-1].content if b.type == "tool_use" and b.name == tool)
    tot = lambda f: sum(getattr(m.usage, f, 0) or 0 for m in msgs)   # noqa: E731  -- a nudge is a second billed call
    usage = {"key": key, "room": room.get("id"), "model": msgs[-1].model, "secs": round(time.time() - t0, 1), "calls": len(msgs),
             "input_tokens": tot("input_tokens"), "output_tokens": tot("output_tokens"),
             "cache_read": tot("cache_read_input_tokens"), "cache_write": tot("cache_creation_input_tokens")}
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"plan": plan, "usage": usage, "room": room, "seed": seed, "prompt_version": PROMPT_VERSION}, indent=1))
    os.replace(tmp, path)
    with open(CACHE / "usage.jsonl", "a") as f:
        f.write(json.dumps(usage) + "\n")
    return plan

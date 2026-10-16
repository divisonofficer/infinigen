"""What the realizer can place: the vocabulary the room planner (LLM) is allowed to use.

Each category names where its geometry comes from -- an ABO product pool (furnish_rooms.POOLS key / abo_assets factory) or an
Infinigen factory -- and a typical size (m, width x depth x height) the planner can reason about clearances with.
"""

FURNITURE = {
    # seating
    "sofa":           {"src": "abo:sofa",        "size": [2.0, 0.9, 0.85], "rooms": ["living-room", "cafe"]},
    "armchair":       {"src": "abo:armchair",    "size": [0.85, 0.85, 0.9], "rooms": ["living-room", "bedroom", "cafe"]},
    "dining_chair":   {"src": "copy:dining",     "size": [0.45, 0.5, 0.85], "rooms": ["dining-room", "kitchen"]},
    "conference_chair": {"src": "abo:officechair", "size": [0.6, 0.6, 1.0], "rooms": ["meeting-room", "office"]},
    "desk_chair":     {"src": "abo:officechair", "size": [0.6, 0.6, 1.0], "rooms": ["bedroom", "living-room", "office", "open-office", "meeting-room"]},
    # tables
    "coffee_table":   {"src": "abo:coffee",      "size": [1.1, 0.6, 0.45], "rooms": ["living-room"]},
    "side_table":     {"src": "abo:side",        "size": [0.5, 0.5, 0.6], "rooms": ["living-room", "bedroom"]},
    "nightstand":     {"src": "abo:nightstand",  "size": [0.5, 0.4, 0.6], "rooms": ["bedroom"]},
    "desk":           {"src": "abo:desk", "size": [1.2, 0.6, 0.75], "rooms": ["bedroom", "living-room"]},
    "office_desk":    {"src": "proc:OfficeDeskFactory", "size": [1.6, 0.8, 0.75], "rooms": ["office", "open-office"]},   # critic r3
    # storage
    "dresser":        {"src": "abo:dresser",     "size": [1.2, 0.5, 0.9], "rooms": ["bedroom"]},
    "sideboard":      {"src": "abo:dresser",     "size": [1.4, 0.45, 0.85], "rooms": ["dining-room", "living-room"]},
    "bookshelf":      {"src": "abo:bookcase", "size": [0.8, 0.3, 1.8], "rooms": ["living-room", "bedroom", "office", "cafe"]},
    "tv_stand":       {"src": "inf:TVStandFactory", "size": [1.6, 0.4, 0.5], "rooms": ["living-room"]},
    # lighting, textiles, plants
    "floor_lamp":     {"src": "abo:floorlamp",   "size": [0.4, 0.4, 1.6], "rooms": ["living-room", "bedroom"]},
    "rug":            {"src": "abo:rug",         "size": [2.0, 1.4, 0.01], "rooms": ["living-room", "bedroom", "dining-room"]},
    "floor_plant":    {"src": "inf:LargePlantContainerFactory", "size": [0.5, 0.5, 1.1], "rooms": ["living-room", "bedroom", "dining-room", "office", "open-office", "meeting-room", "break-room", "cafe", "grocery"]},
    # workplaces: warehouse / garage / utility
    "storage_rack":   {"src": "abo:rack",        "size": [1.2, 0.6, 1.8], "rooms": ["warehouse", "garage", "utility"]},
    "wide_shelf":     {"src": "inf:LargeShelfFactory", "size": [1.6, 0.5, 2.0], "rooms": ["warehouse", "garage"]},
    "pallet":         {"src": "proc:PalletFactory", "size": [1.2, 0.8, 0.14], "rooms": ["warehouse"]},
    "box_pile":       {"src": "proc:BoxPileFactory", "size": [1.2, 0.8, 0.9], "rooms": ["warehouse", "garage", "grocery"]},
    "workbench":      {"src": "inf:SimpleDeskFactory", "size": [1.4, 0.7, 0.8], "rooms": ["warehouse", "garage"]},
    "ladder":         {"src": "abo:ladder",      "size": [0.5, 0.7, 1.5], "rooms": ["warehouse", "garage", "utility"]},
    "stool":          {"src": "abo:stool",       "size": [0.4, 0.4, 0.6], "rooms": ["warehouse", "garage"]},
    "utility_cart":   {"src": "abo:cart",        "size": [0.9, 0.5, 0.9], "rooms": ["warehouse", "grocery"]},
    "fan":            {"src": "abo:fan",         "size": [0.4, 0.3, 1.0], "rooms": ["warehouse", "garage"]},
    # offices
    "meeting_table":  {"src": "proc:ConferenceTableFactory",   "size": [2.4, 1.1, 0.75], "rooms": ["meeting-room", "office"]},   # open office: inside glass_meeting_room only (critic r3)
    "filing_cabinet": {"src": "abo:filing",      "size": [0.5, 0.6, 1.0], "rooms": ["office", "open-office"]},
    "break_table":    {"src": "proc:BreakTableFactory", "size": [1.6, 0.9, 0.75], "rooms": ["break-room", "cafe"]},
    "break_chair":    {"src": "abo:barstool",     "size": [0.45, 0.5, 0.85], "rooms": ["break-room"]},
    # cafe / grocery store (single-room layouts relabelled with plan_scene --venue)
    "counter":        {"src": "proc:CafeCounterFactory", "size": [2.4, 0.65, 1.0], "rooms": ["cafe", "grocery"]},
    "backbar_shelf":  {"src": "proc:BackBarShelfFactory", "size": [2.0, 0.28, 2.2], "rooms": ["cafe"]},
    "cafe_table":     {"src": "proc:CafeTableFactory", "size": [0.7, 0.7, 0.75], "rooms": ["cafe"]},
    "menu_board":     {"src": "abo:board",       "size": [1.0, 0.4, 1.6], "rooms": ["cafe"]},
    "window_bar":     {"src": "proc:WindowBarFactory", "size": [2.4, 0.4, 1.05], "rooms": ["cafe"]},
    "coffee_bar":     {"src": "zone:coffee_bar", "size": [2.6, 1.9, 2.2], "rooms": ["cafe"]},
    "gondola":        {"src": "proc:GondolaFactory", "size": [1.9, 0.9, 1.5], "rooms": ["grocery"]},
    # offices: zones (a set placed as one) and their internal parts
    "workstation_pod": {"src": "zone:workstation_pod", "size": [2.8, 2.4, 1.2], "rooms": ["open-office", "office"]},
    "glass_meeting_room": {"src": "zone:glass_meeting_room", "size": [4.5, 3.5, 2.8], "rooms": ["open-office"]},
    "meeting_set":    {"src": "zone:meeting_set", "size": [4.0, 2.6, 0.75], "rooms": ["meeting-room"]},
    "pantry_run":     {"src": "zone:pantry_run", "size": [3.0, 0.6, 2.2], "rooms": ["break-room"]},
    "pod_unit":       {"src": "proc:WorkstationPodFactory", "size": [2.8, 1.4, 1.2], "rooms": ["_internal"]},
    "pantry_unit":    {"src": "proc:PantryRunFactory", "size": [3.0, 0.6, 2.2], "rooms": ["_internal"]},
    "wall_display":   {"src": "proc:WallDisplayFactory", "size": [1.5, 0.05, 0.9], "rooms": ["_internal"]},
    "whiteboard":     {"src": "proc:WhiteboardFactory", "size": [1.5, 0.05, 1.0], "rooms": ["meeting-room", "office", "open-office"]},
    "wall_gondola":   {"src": "proc:WallGondolaFactory", "size": [1.9, 0.45, 1.5], "rooms": ["grocery"]},
    "chest_freezer":  {"src": "proc:ChestFreezerFactory", "size": [1.6, 0.8, 0.85], "rooms": ["grocery"]},
    "cafe_chair":     {"src": "abo:cafechair",   "size": [0.45, 0.5, 0.85], "rooms": ["cafe", "office", "break-room"]},
    "bar_stool":      {"src": "abo:barstool",    "size": [0.4, 0.4, 0.75], "rooms": ["cafe", "break-room"]},
    "beverage_fridge": {"src": "inf:BeverageFridgeFactory", "size": [0.6, 0.6, 1.8], "rooms": ["grocery", "cafe"]},
}

#: room types that are workplaces: their planner prompt and vocabulary differ from a home's
WORK_ROOMS = {"warehouse", "garage", "utility", "office", "open-office", "meeting-room", "break-room", "factory-office", "cafe",
              "grocery"}

#: small things that show someone lives here, placed on/at furniture
LIVED_IN = {
    "throw_blanket":   {"src": "inf:BlanketFactory", "on": ["sofa", "armchair", "bed"], "rooms": ["home"]},
    "cushion":         {"src": "abo:PILLOW", "on": ["sofa", "armchair", "bed", "floor"], "rooms": ["home"]},
    "book_stack":      {"src": "inf:BookStackFactory", "on": ["coffee_table", "side_table", "nightstand", "desk", "floor"], "rooms": ["home", "office", "open-office"]},
    "mug":             {"src": "inf:CupFactory", "on": ["coffee_table", "side_table", "nightstand", "desk", "dining_table"], "rooms": ["home", "office", "open-office", "meeting-room", "break-room", "cafe"]},
    "fruit_bowl":      {"src": "inf:FruitContainerFactory", "on": ["dining_table", "coffee_table", "counter"], "rooms": ["home", "break-room", "cafe"]},
    "table_lamp":      {"src": "abo:TABLE_LAMP", "on": ["side_table", "nightstand", "desk", "sideboard"], "rooms": ["home", "office"]},
    "vase":            {"src": "abo:VASE", "on": ["coffee_table", "sideboard", "dresser", "dining_table"], "rooms": ["home", "cafe"]},
    "small_plant":     {"src": "abo:PLANTER", "on": ["side_table", "sideboard", "desk", "dresser", "floor"], "rooms": ["home", "office", "open-office", "meeting-room", "break-room", "cafe"]},
    "storage_box":     {"src": "abo:BOX", "on": ["floor", "bookshelf", "dresser"], "rooms": ["home"]},
    "draped_clothes":  {"src": "inf:ShirtFactory", "on": ["armchair", "desk_chair", "bed", "sofa", "floor"]},
    "pants":           {"src": "inf:PantsFactory", "on": ["bed", "armchair", "sofa", "floor"]},
    "towel":           {"src": "inf:TowelFactory", "on": ["bed", "floor", "armchair"]},
    "open_book":       {"src": "inf:BookFactory", "on": ["sofa", "armchair", "bed", "coffee_table", "side_table", "nightstand", "floor"], "rooms": ["home", "office", "open-office", "break-room"]},
    "laundry_basket":  {"src": "inf:BasketBaseFactory", "on": ["floor"]},
    # workplaces ("rooms": only offered there)
    "cardboard_box":   {"src": "proc:CardboardBoxFactory", "on": ["storage_rack", "wide_shelf", "pallet", "workbench", "floor"],
                        "rooms": ["warehouse", "garage", "utility", "grocery"]},
    "storage_bin":     {"src": "abo:BOX", "on": ["storage_rack", "wide_shelf", "workbench", "floor"], "rooms": ["warehouse", "garage", "utility"]},
    "bottle":          {"src": "inf:BottleFactory", "on": ["workbench", "storage_rack"], "rooms": ["warehouse", "garage", "cafe", "grocery"]},
    "can":             {"src": "inf:CanFactory", "on": ["workbench", "storage_rack"], "rooms": ["warehouse", "garage"]},
    "monitor":         {"src": "inf:MonitorFactory", "on": ["desk", "office_desk"], "rooms": ["office", "open-office"]},
    "speakerphone":    {"src": "proc:SpeakerphoneFactory", "on": ["meeting_table"], "rooms": ["meeting-room"]},
    "microwave":       {"src": "inf:MicrowaveFactory", "on": ["pantry_run"], "rooms": ["break-room"]},
    "plate":           {"src": "inf:PlateFactory", "on": ["cafe_table", "counter"], "rooms": ["cafe"]},
    "espresso_machine": {"src": "proc:EspressoMachineFactory", "on": ["counter"], "rooms": ["cafe"]},
    "grinder":         {"src": "proc:GrinderFactory", "on": ["counter"], "rooms": ["cafe"]},
    "cup_stack":       {"src": "proc:CupStackFactory", "on": ["counter", "backbar_shelf"], "rooms": ["cafe"]},
    "pastry_case":     {"src": "proc:PastryCaseFactory", "on": ["counter"], "rooms": ["cafe"]},
    "syrup_rack":      {"src": "proc:SyrupRackFactory", "on": ["counter"], "rooms": ["cafe"]},
    "cake_dome":       {"src": "proc:CakeDomeFactory", "on": ["counter", "cafe_table"], "rooms": ["cafe"]},
    "backbar_stock":   {"src": "inf:BottleFactory", "on": ["backbar_shelf"], "rooms": ["cafe"]},
    "wine_glass":      {"src": "inf:WineglassFactory", "on": ["cafe_table", "counter"], "rooms": ["cafe"]},
    "groceries":       {"src": "inf:FoodBoxFactory", "on": ["gondola", "wall_gondola", "counter"], "rooms": ["grocery"]},
    "basket":          {"src": "inf:BasketBaseFactory", "on": ["floor", "counter"], "rooms": ["grocery"]},
    "register":        {"src": "proc:RegisterFactory", "on": ["counter"], "rooms": ["grocery", "cafe"]},
    # desk clutter (user 2026-10-16: offices looked untouched -- leftover snacks, books, pencils, cups)
    "pen_cup":         {"src": "proc:PenCupFactory", "on": ["desk", "office_desk", "meeting_table"], "rooms": ["office", "open-office", "meeting-room"]},
    "takeaway_cup":    {"src": "proc:TakeawayCupFactory", "on": ["desk", "office_desk", "meeting_table", "break_table", "counter"], "rooms": ["office", "open-office", "meeting-room", "break-room", "cafe"]},
    "snack":           {"src": "proc:SnackFactory", "on": ["desk", "office_desk", "meeting_table", "break_table"], "rooms": ["office", "open-office", "meeting-room", "break-room"]},
    "phone":           {"src": "proc:PhoneFactory", "on": ["desk", "office_desk", "meeting_table", "break_table", "cafe_table"], "rooms": ["office", "open-office", "meeting-room", "break-room", "cafe"]},
    "notebook":        {"src": "proc:NotebookFactory", "on": ["desk", "office_desk", "meeting_table"], "rooms": ["office", "open-office", "meeting-room"]},
    "paper_stack":     {"src": "proc:PaperStackFactory", "on": ["desk", "meeting_table", "filing_cabinet"], "rooms": ["office", "open-office", "meeting-room"]},
}

RELATIONS = {
    "against_wall": "back against wall `wall` (a wall id from the room, or 'longest_free'); `facing` defaults to the room",
    "in_front_of": "in front of `target` at `gap_m` (coffee table 0.4-0.5 m before a sofa)",
    "beside": "next to `target` on `side` (left|right|both), touching distance",
    "around": "spread around `target` (dining chairs around a table), `count` of them",
    "facing": "turned to face `target` (armchair facing the sofa, sofa facing the TV)",
    "under": "under `target` (a rug under the coffee table / bed foot)",
    "corner": "in a free corner",
    "near_window": "within 1 m of a window",
    "row": "`count` of them side by side along wall `wall`, `gap_m` from it (0 = against it; 2-3 m = a free-standing aisle row "
           "parallel to that wall); `facing` 'away' (default) or 'toward' the wall",
}

#: how a piece of furniture stands: square to its wall/target, turned a little, or (chairs) pulled out from the table/desk
FURNITURE_POSES = {"aligned": "square, as placed", "angled": "turned 8-20 deg off square", "pulled_out": "moved 0.15-0.35 m back from its target and turned 10-25 deg"}

#: how a small item lies: upright where it belongs, or the way people leave things
ITEM_POSES = {"placed": "upright, where it belongs", "lying": "on its side / flat (a single book, a bottle on its side)",
              "tossed": "dropped carelessly and settled by physics (cushion against the backrest, clothes on the bed, a book on the sofa)",
              "leaning": "leaning against the host's back or a wall (cushion, book)"}

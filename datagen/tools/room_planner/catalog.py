"""What the realizer can place: the vocabulary the room planner (LLM) is allowed to use.

Each category names where its geometry comes from -- an ABO product pool (furnish_rooms.POOLS key / abo_assets factory) or an
Infinigen factory -- and a typical size (m, width x depth x height) the planner can reason about clearances with.
"""

FURNITURE = {
    # seating
    "sofa":           {"src": "abo:sofa",        "size": [2.0, 0.9, 0.85], "rooms": ["living-room", "cafe"]},
    "armchair":       {"src": "abo:armchair",    "size": [0.85, 0.85, 0.9], "rooms": ["living-room", "bedroom", "cafe", "boutique"]},
    "dining_chair":   {"src": "copy:dining",     "size": [0.45, 0.5, 0.85], "rooms": ["dining-room", "kitchen"]},
    "conference_chair": {"src": "inf:OfficeChairFactory", "size": [0.6, 0.6, 1.0], "rooms": ["meeting-room", "office", "exam-room"]},
    "desk_chair":     {"src": "inf:OfficeChairFactory", "size": [0.6, 0.6, 1.0], "rooms": ["bedroom", "living-room", "office", "open-office", "meeting-room", "clinic-reception", "exam-room", "dental-room", "physio-room", "pharmacy"]},
    # tables
    "coffee_table":   {"src": "abo:coffee",      "size": [1.1, 0.6, 0.45], "rooms": ["living-room"]},
    "side_table":     {"src": "abo:side",        "size": [0.5, 0.5, 0.6], "rooms": ["living-room", "bedroom"]},
    "nightstand":     {"src": "abo:nightstand",  "size": [0.5, 0.4, 0.6], "rooms": ["bedroom"]},
    "desk":           {"src": "abo:desk", "size": [1.2, 0.6, 0.75], "rooms": ["bedroom", "living-room"]},
    "office_desk":    {"src": "proc:OfficeDeskFactory", "size": [1.6, 0.8, 0.75], "rooms": ["office", "open-office"]},   # critic r3
    # storage
    "dresser":        {"src": "abo:dresser",     "size": [1.2, 0.5, 0.9], "rooms": ["bedroom"]},
    "sideboard":      {"src": "abo:dresser",     "size": [1.4, 0.45, 0.85], "rooms": ["dining-room", "living-room"]},
    "bookshelf":      {"src": "abo:bookcase", "size": [0.8, 0.3, 1.8], "rooms": ["living-room", "bedroom", "cafe", "office"]},
    "office_bookcase": {"src": "proc:OfficeShelfFactory", "size": [0.9, 0.35, 1.8], "rooms": ["office"]},   # plain, stocked (floor C r4: an
                                                                                                         # ABO ladder shelf read residential, empty)
    "tv_stand":       {"src": "inf:TVStandFactory", "size": [1.6, 0.4, 0.5], "rooms": ["living-room"]},
    # lighting, textiles, plants
    "floor_lamp":     {"src": "abo:floorlamp",   "size": [0.4, 0.4, 1.6], "rooms": ["living-room", "bedroom"]},
    "rug":            {"src": "abo:rug",         "size": [2.0, 1.4, 0.01], "rooms": ["living-room", "bedroom", "dining-room", "boutique"]},
    "floor_plant":    {"src": "inf:LargePlantContainerFactory", "size": [0.5, 0.5, 1.1], "rooms": ["living-room", "bedroom", "dining-room", "office", "open-office", "meeting-room", "cafe", "grocery", "clinic-reception", "physio-room", "boutique", "pharmacy"]},
    # workplaces: warehouse / garage / utility
    "storage_rack":   {"src": "proc:StorageRackFactory", "size": [2.1, 0.7, 2.3], "rooms": ["warehouse", "garage", "utility"]},
    "stock_shelf":    {"src": "proc:StockShelfFactory", "size": [1.8, 0.55, 2.1], "rooms": ["warehouse", "utility"]},   # back stockrooms
    "supply_shelf":   {"src": "proc:SupplyShelfFactory", "size": [1.2, 0.45, 2.0], "rooms": ["utility", "warehouse"]},   # clinic sterilisation / supply
    "wide_shelf":     {"src": "proc:StorageRackFactory", "size": [2.1, 0.7, 2.3], "rooms": ["warehouse", "garage"]},
    "pallet":         {"src": "proc:PalletFactory", "size": [1.2, 0.8, 0.14], "rooms": ["warehouse"]},
    "box_pile":       {"src": "proc:BoxPileFactory", "size": [1.2, 0.8, 0.9], "rooms": ["warehouse", "garage", "grocery"]},
    "workbench":      {"src": "proc:WorkbenchFactory", "size": [1.8, 0.75, 0.9], "rooms": ["warehouse", "garage"]},
    "ladder":         {"src": "proc:StepLadderFactory", "size": [0.6, 0.5, 1.5], "rooms": ["warehouse", "garage", "utility"]},
    "stool":          {"src": "proc:ShopStoolFactory", "size": [0.35, 0.35, 0.7], "rooms": ["warehouse", "garage"]},
    "utility_cart":   {"src": "proc:PlatformCartFactory", "size": [0.95, 0.6, 1.0], "rooms": ["warehouse", "grocery"]},
    "fan":            {"src": "abo:fan",         "size": [0.4, 0.3, 1.0], "rooms": ["warehouse", "garage"]},
    # offices
    "meeting_table":  {"src": "proc:ConferenceTableFactory",   "size": [2.4, 1.1, 0.75], "rooms": ["meeting-room", "office"]},   # open office: inside glass_meeting_room only (critic r3)
    "filing_cabinet": {"src": "proc:FilingCabinetFactory",      "size": [0.5, 0.6, 1.0], "rooms": ["office", "open-office", "clinic-reception", "exam-room"]},
    "break_table":    {"src": "proc:BreakTableFactory", "size": [1.6, 0.9, 0.75], "rooms": ["break-room", "cafe"]},
    "break_chair":    {"src": "proc:CafeChairFactory",     "size": [0.45, 0.5, 0.85], "rooms": ["break-room"]},
    # cafe / grocery store (single-room layouts relabelled with plan_scene --venue)
    "counter":        {"src": "proc:CafeCounterFactory", "size": [2.4, 0.65, 1.0], "rooms": ["cafe", "grocery", "convenience", "boutique"]},
    "backbar_shelf":  {"src": "proc:BackBarShelfFactory", "size": [2.0, 0.28, 2.2], "rooms": ["cafe", "pharmacy"]},
    "cafe_table":     {"src": "proc:CafeTableFactory", "size": [0.7, 0.7, 0.75], "rooms": ["cafe"]},
    "balloon_sign":   {"src": "inf:BalloonFactory", "size": [0.15, 1.6, 0.4], "rooms": ["_internal"]},   # foil letter balloons (inf)
    "menu_board":     {"src": "proc:MenuBoardFactory",       "size": [1.0, 0.4, 1.6], "rooms": ["cafe"]},
    "window_bar":     {"src": "proc:WindowBarFactory", "size": [2.4, 0.4, 1.05], "rooms": ["cafe"]},
    "coffee_bar":     {"src": "zone:coffee_bar", "size": [2.6, 1.9, 2.2], "rooms": ["cafe"]},
    "gondola":        {"src": "proc:GondolaFactory", "size": [1.9, 0.9, 1.5], "rooms": ["grocery", "convenience", "pharmacy"]},
    "banquette_row":  {"src": "zone:banquette_row", "size": [3.0, 1.9, 1.0], "rooms": ["cafe"]},
    "banquette":      {"src": "proc:BanquetteFactory", "size": [3.0, 0.55, 1.0], "rooms": ["_internal"]},
    # clinics and shops (non-home 20, 2026-10-16)
    "clinic_desk":    {"src": "proc:ClinicDeskFactory", "size": [1.2, 0.65, 0.75], "rooms": ["exam-room", "dental-room", "physio-room"]},
    "reception_desk": {"src": "proc:ReceptionDeskFactory", "size": [2.4, 0.75, 1.12], "rooms": ["clinic-reception", "pharmacy"]},
    "prep_table":     {"src": "proc:PrepTableFactory", "size": [0.7, 1.8, 1.3], "rooms": ["_internal"]},
    "pallet_rack":    {"src": "proc:PalletRackFactory", "size": [1.1, 2.7, 4.4], "rooms": ["_internal"]},
    "dock_door":      {"src": "proc:RollerShutterFactory", "size": [0.5, 4.1, 4.75], "rooms": ["_internal"]},
    "clinic_low_table": {"src": "proc:ClinicLowTableFactory", "size": [1.1, 0.55, 0.42], "rooms": ["_internal"]},
    "exercise_mat":   {"src": "proc:ExerciseMatFactory", "size": [1.8, 0.6, 0.02], "rooms": ["_internal"]},
    "waiting_bench":  {"src": "proc:WaitingBenchFactory", "size": [2.2, 0.6, 0.85], "rooms": ["clinic-reception", "pharmacy"]},   # not exam rooms:
                                                                                     # a 3-seat beam bench read as a second waiting room (floor D3 r2)
    "exam_table":     {"src": "proc:ExamTableFactory", "size": [0.65, 1.9, 0.9], "rooms": ["exam-room", "physio-room"]},
    "toilet":         {"src": "proc:ToiletStallFactory", "size": [1.5, 0.95, 1.95], "rooms": ["restroom"]},   # floor scenes: a cubicle
    "wc":             {"src": "inf:ToiletFactory", "size": [0.7, 0.45, 0.8], "rooms": ["restroom"]},   # a single-user restroom: no cubicle
    "urinal":         {"src": "proc:UrinalFactory", "size": [0.42, 1.6, 1.6], "rooms": ["restroom"]},
    "wash_basin":     {"src": "proc:WashBasinFactory", "size": [0.45, 0.6, 1.9], "rooms": ["restroom"]},
    "locker":         {"src": "proc:LockerFactory", "size": [0.5, 1.4, 1.8], "rooms": ["closet", "break-room"]},
    "changing_bench": {"src": "proc:ChangingBenchFactory", "size": [0.35, 1.3, 0.47], "rooms": ["closet"]},
    "medical_cabinet": {"src": "proc:MedicalCabinetFactory", "size": [3.0, 0.6, 2.2], "rooms": ["exam-room", "dental-room", "physio-room"]},
    "privacy_curtain": {"src": "proc:PrivacyCurtainFactory", "size": [1.6, 2.2, 2.35], "rooms": ["exam-room", "physio-room"]},
    "dental_chair":   {"src": "proc:DentalChairFactory", "size": [0.9, 1.9, 2.0], "rooms": ["dental-room"]},
    "wall_bars":      {"src": "proc:WallBarsFactory", "size": [0.95, 0.12, 2.4], "rooms": ["physio-room"]},
    "exercise_set":   {"src": "proc:ExerciseSetFactory", "size": [0.7, 2.0, 0.66], "rooms": ["physio-room"]},
    "parallel_bars":  {"src": "proc:ParallelBarsFactory", "size": [0.9, 3.0, 0.95], "rooms": ["physio-room"]},
    "exercise_bike":  {"src": "proc:ExerciseBikeFactory", "size": [0.95, 0.5, 1.1], "rooms": ["physio-room"]},
    "clothing_rack":  {"src": "proc:ClothingRackFactory", "size": [1.6, 0.5, 1.55], "rooms": ["boutique"]},
    "display_table":  {"src": "proc:DisplayTableFactory", "size": [1.4, 0.8, 0.9], "rooms": ["boutique"]},
    "mirror":         {"src": "proc:MirrorFactory", "size": [0.65, 0.3, 1.85], "rooms": ["boutique", "closet"]},
    "fitting_room":   {"src": "proc:FittingRoomFactory", "size": [1.25, 1.1, 2.2], "rooms": ["boutique"]},
    # offices: zones (a set placed as one) and their internal parts
    "workstation_pod": {"src": "zone:workstation_pod", "size": [2.8, 2.4, 1.2], "rooms": ["open-office", "office"]},
    "glass_meeting_room": {"src": "zone:glass_meeting_room", "size": [4.5, 3.5, 2.8], "rooms": ["open-office"]},
    "meeting_set":    {"src": "zone:meeting_set", "size": [4.0, 2.6, 0.75], "rooms": ["meeting-room"]},
    "pantry_run":     {"src": "zone:pantry_run", "size": [3.0, 0.6, 2.2], "rooms": ["break-room"]},
    "pod_unit":       {"src": "proc:WorkstationPodFactory", "size": [2.8, 1.4, 1.2], "rooms": ["_internal"]},
    "pantry_unit":    {"src": "proc:PantryRunFactory", "size": [3.0, 0.6, 2.2], "rooms": ["_internal"]},
    "wall_display":   {"src": "proc:WallDisplayFactory", "size": [1.5, 0.05, 0.9], "rooms": ["_internal"]},
    "whiteboard":     {"src": "proc:WhiteboardFactory", "size": [1.5, 0.05, 1.0], "rooms": ["meeting-room", "office", "open-office", "physio-room"]},
    "wall_gondola":   {"src": "proc:WallGondolaFactory", "size": [1.9, 0.45, 1.5], "rooms": ["grocery", "convenience", "pharmacy", "boutique"]},
    "chest_freezer":  {"src": "proc:ChestFreezerFactory", "size": [1.6, 0.8, 0.85], "rooms": ["grocery", "convenience"]},
    "cafe_chair":     {"src": "abo:cafechair",   "size": [0.45, 0.5, 0.85], "rooms": ["cafe", "office", "break-room"]},
    "bar_stool":      {"src": "abo:barstool",    "size": [0.4, 0.4, 0.75], "rooms": ["cafe", "break-room"]},
    "beverage_fridge": {"src": "proc:DisplayCoolerFactory", "size": [0.75, 0.7, 2.0], "rooms": ["grocery", "convenience", "pharmacy"]},   # not cafe: the inf fridge rendered as a black box (floor H r4, 3 of 3)
}

#: room types that are workplaces: their planner prompt and vocabulary differ from a home's
WORK_ROOMS = {"warehouse", "garage", "utility", "office", "open-office", "meeting-room", "break-room", "factory-office", "cafe",
              "grocery", "clinic-reception", "exam-room", "dental-room", "physio-room", "convenience", "boutique", "pharmacy"}

#: small things that show someone lives here, placed on/at furniture
LIVED_IN = {
    "throw_blanket":   {"src": "inf:BlanketFactory", "on": ["sofa", "armchair", "bed"], "rooms": ["home"]},
    "cushion":         {"src": "abo:PILLOW", "on": ["sofa", "armchair", "bed", "floor"], "rooms": ["home"]},
    "book_stack":      {"src": "inf:BookStackFactory", "on": ["coffee_table", "side_table", "nightstand", "desk", "floor", "office_bookcase"], "rooms": ["home", "office", "open-office", "clinic-reception"]},
    "mug":             {"src": "inf:CupFactory", "on": ["coffee_table", "side_table", "nightstand", "desk", "dining_table", "reception_desk"], "rooms": ["home", "office", "open-office", "meeting-room", "break-room", "cafe", "clinic-reception", "exam-room", "pharmacy", "dental-room"]},
    "fruit_bowl":      {"src": "inf:FruitContainerFactory", "on": ["dining_table", "coffee_table", "counter"], "rooms": ["home", "break-room", "cafe"]},
    "table_lamp":      {"src": "abo:TABLE_LAMP", "on": ["side_table", "nightstand", "desk", "sideboard"], "rooms": ["home", "office"]},
    "vase":            {"src": "abo:VASE", "on": ["coffee_table", "sideboard", "dresser", "dining_table"], "rooms": ["home", "cafe"]},
    "small_plant":     {"src": "abo:PLANTER", "on": ["side_table", "sideboard", "desk", "dresser", "floor"], "rooms": ["home", "office", "open-office", "meeting-room", "break-room", "cafe", "clinic-reception", "boutique", "restroom"]},
    "storage_box":     {"src": "abo:BOX", "on": ["floor", "bookshelf", "dresser"], "rooms": ["home"]},
    "draped_clothes":  {"src": "inf:ShirtFactory", "on": ["armchair", "desk_chair", "bed", "sofa", "floor"]},
    "pants":           {"src": "inf:PantsFactory", "on": ["bed", "armchair", "sofa", "floor"]},
    "towel":           {"src": "inf:TowelFactory", "on": ["bed", "floor", "armchair"]},
    "open_book":       {"src": "inf:BookFactory", "on": ["sofa", "armchair", "bed", "coffee_table", "side_table", "nightstand", "floor"], "rooms": ["home", "office", "open-office", "break-room"]},
    "laundry_basket":  {"src": "inf:BasketBaseFactory", "on": ["floor"]},
    # workplaces ("rooms": only offered there)
    "autoclave":       {"src": "proc:AutoclaveFactory", "on": ["medical_cabinet"], "rooms": ["utility"]},
    "bag":             {"src": "proc:BagFactory", "on": ["floor", "changing_bench"], "rooms": ["office", "open-office", "meeting-room", "break-room",
                        "clinic-reception", "exam-room", "dental-room", "physio-room", "closet", "warehouse", "kitchen", "cafe", "pharmacy"]},
    "cafe_stock":      {"src": "proc:CafeStockFactory", "on": ["stock_shelf", "storage_rack", "floor"], "rooms": ["utility", "warehouse"]},
    "dry_goods":       {"src": "proc:DryGoodsFactory", "on": ["stock_shelf", "storage_rack", "supply_shelf", "floor"], "rooms": ["warehouse", "utility"]},
    "cardboard_box":   {"src": "proc:CardboardBoxFactory", "on": ["storage_rack", "wide_shelf", "pallet", "workbench", "floor", "supply_shelf", "stock_shelf"],
                        "rooms": ["warehouse", "garage", "utility", "grocery"]},
    "storage_bin":     {"src": "abo:BOX", "on": ["storage_rack", "wide_shelf", "workbench", "floor", "supply_shelf"], "rooms": ["warehouse", "garage", "utility"]},
    "bottle":          {"src": "inf:BottleFactory", "on": ["workbench", "storage_rack"], "rooms": ["warehouse", "garage", "cafe", "grocery", "convenience", "pharmacy", "exam-room", "dental-room"]},
    "can":             {"src": "inf:CanFactory", "on": ["workbench", "storage_rack"], "rooms": ["warehouse", "garage"]},
    "monitor":         {"src": "inf:MonitorFactory", "on": ["desk", "office_desk", "reception_desk"], "rooms": ["office", "open-office", "exam-room", "dental-room", "clinic-reception", "pharmacy"]},
    "speakerphone":    {"src": "proc:SpeakerphoneFactory", "on": ["meeting_table"], "rooms": ["meeting-room"]},
    "microwave":       {"src": "inf:MicrowaveFactory", "on": ["pantry_run"], "rooms": ["break-room"]},
    "plate":           {"src": "inf:PlateFactory", "on": ["cafe_table", "counter", "window_bar"], "rooms": ["cafe"]},
    "espresso_machine": {"src": "proc:EspressoMachineFactory", "on": ["counter"], "rooms": ["cafe"]},
    "grinder":         {"src": "proc:GrinderFactory", "on": ["counter"], "rooms": ["cafe"]},
    "cup_stack":       {"src": "proc:CupStackFactory", "on": ["counter", "backbar_shelf"], "rooms": ["cafe"]},
    "pastry_case":     {"src": "proc:PastryCaseFactory", "on": ["counter"], "rooms": ["cafe"]},
    "syrup_rack":      {"src": "proc:SyrupRackFactory", "on": ["counter"], "rooms": ["cafe"]},
    "cake_dome":       {"src": "proc:CakeDomeFactory", "on": ["counter", "cafe_table"], "rooms": ["cafe"]},
    "backbar_stock":   {"src": "inf:BottleFactory", "on": ["backbar_shelf"], "rooms": ["cafe"]},
    "wine_glass":      {"src": "inf:WineglassFactory", "on": ["cafe_table", "counter"], "rooms": ["cafe"]},
    "groceries":       {"src": "inf:FoodBoxFactory", "on": ["gondola", "wall_gondola", "counter"], "rooms": ["grocery", "convenience", "pharmacy"]},
    "basket":          {"src": "inf:BasketBaseFactory", "on": ["counter"], "rooms": ["grocery", "convenience", "pharmacy"]},   # not floor: loose baskets in the queue path read as dropped (floor I r14, 3 of 3)
    "register":        {"src": "proc:RegisterFactory", "on": ["counter"], "rooms": ["grocery", "cafe", "convenience", "boutique", "pharmacy"]},
    # desk clutter (user 2026-10-16: offices looked untouched -- leftover snacks, books, pencils, cups)
    "bud_vase":        {"src": "proc:BudVaseFactory", "on": ["cafe_table", "counter", "window_bar"], "rooms": ["cafe"]},
    "flower_arrangement": {"src": "proc:FlowerArrangementFactory", "on": ["counter"], "rooms": ["cafe"]},
    "drink_cans":      {"src": "proc:DrinkCansFactory", "on": ["pantry_run", "break_table", "counter"], "rooms": ["break-room", "convenience"]},
    "snack_basket":    {"src": "proc:SnackBasketFactory", "on": ["pantry_run", "break_table"], "rooms": ["break-room"]},
    "pen_cup":         {"src": "proc:PenCupFactory", "on": ["desk", "office_desk", "meeting_table", "reception_desk"], "rooms": ["office", "open-office", "meeting-room", "clinic-reception", "exam-room", "pharmacy", "dental-room"]},
    "takeaway_cup":    {"src": "proc:TakeawayCupFactory", "on": ["desk", "office_desk", "meeting_table", "break_table", "counter", "reception_desk"], "rooms": ["office", "open-office", "meeting-room", "break-room", "cafe", "clinic-reception"]},
    "snack":           {"src": "proc:SnackFactory", "on": ["desk", "office_desk", "meeting_table", "break_table"], "rooms": ["office", "open-office", "meeting-room", "break-room"]},
    "phone":           {"src": "proc:PhoneFactory", "on": ["desk", "office_desk", "meeting_table", "break_table", "cafe_table", "reception_desk"], "rooms": ["office", "open-office", "meeting-room", "break-room", "cafe", "clinic-reception", "pharmacy", "boutique", "convenience"]},
    "notebook":        {"src": "proc:NotebookFactory", "on": ["desk", "office_desk", "meeting_table", "reception_desk"], "rooms": ["office", "open-office", "meeting-room", "clinic-reception", "exam-room", "dental-room"]},
    "open_box":        {"src": "proc:OpenBoxFactory", "on": ["workbench"], "rooms": ["warehouse", "garage"]},
    "tape_gun":        {"src": "proc:TapeGunFactory", "on": ["workbench"], "rooms": ["warehouse", "garage"]},
    "kraft_roll":      {"src": "proc:KraftRollFactory", "on": ["workbench"], "rooms": ["warehouse", "garage"]},
    "towel_stack":     {"src": "proc:TowelStackFactory", "on": ["exam_table", "changing_bench"], "rooms": ["physio-room", "exam-room", "closet"]},
    # clinical counter / desk props (clinic r6 critic: 'no glove boxes, sanitizer or trays -- an unfurnished showroom')
    "glove_box":       {"src": "proc:GloveBoxFactory", "on": ["medical_cabinet", "clinic_desk", "reception_desk"], "rooms": ["clinic-reception", "exam-room", "dental-room", "physio-room", "pharmacy", "utility"]},
    "sanitizer":       {"src": "proc:SanitizerFactory", "on": ["medical_cabinet", "clinic_desk", "reception_desk", "counter", "wash_basin"], "rooms": ["clinic-reception", "exam-room", "dental-room", "physio-room", "pharmacy"]},
    "paper_towel":     {"src": "proc:PaperTowelFactory", "on": ["medical_cabinet"], "rooms": ["clinic-reception", "exam-room", "dental-room", "physio-room", "pharmacy"]},
    "clipboard":       {"src": "proc:ClipboardFactory", "on": ["medical_cabinet", "clinic_desk", "reception_desk", "exam_table"], "rooms": ["clinic-reception", "exam-room", "dental-room", "physio-room", "pharmacy"]},
    "kidney_tray":     {"src": "proc:KidneyTrayFactory", "on": ["medical_cabinet", "clinic_desk"], "rooms": ["exam-room", "dental-room"]},
    "paper_stack":     {"src": "proc:PaperStackFactory", "on": ["desk", "meeting_table", "filing_cabinet", "reception_desk"], "rooms": ["office", "open-office", "meeting-room", "clinic-reception", "exam-room", "dental-room", "pharmacy"]},
}

RELATIONS = {
    "against_wall": "back against wall `wall` (a wall id from the room, or 'longest_free'); `facing` defaults to the room",
    "in_front_of": "in front of `target` at `gap_m` (coffee table 0.4-0.5 m before a sofa)",
    "behind": "on the far side of `target`, facing it (the staff chair behind a reception desk or counter)",
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

# Non-home 20: LLM-loop scene campaign (goal set 2026-10-16)

Goal: 20 finished non-home interiors made by the generate → render → critique → generator-fix loop.

Done means: the **median of three independent critic calls** is ≥ 7 on every criterion (target 8), a sheet the user has seen, then a dataset render (v2.1 naming `infinigen_<venue>_v2_1_<seed>`). One call is not enough: the same storage images scored 7–9, 7–9, 6–8 and 6–8 in four calls (2026-10-16).

| # | Venue | Room / style | Status | Last critic (min–max) |
|---|---|---|---|---|
| 1 | Office | open office, glass meeting ref | r9 medians ws 6 / circ 6 / ceil 8 / coh 7: loose single desks, mixed chairs → r10 one chair model per scene | 6–8 (r9) |
| 2 | Office | open office, high-rise ref | **DONE by the median rule: r9 (scene kr_officeK_highrise_47308706) ws 7 / circ 7 / ceil 9 / coh 7**; queued for the dataset render | medians ≥ 7 |
| 3 | Office | meeting room | **DONE by the median rule: r9 (scene kr_officeK_meeting_47308702) circ 7 / meeting 7 / ceil 8 / coh 7**; queued for the dataset render | medians ≥ 7 |
| 4 | Office | private office | **DONE by the median rule: r8 (scene kr_officeJ_private_47308703) circ 7 / ceil 7 / coh 7 (other criteria n/a)**; queued for the dataset render | medians ≥ 7 |
| 5 | Office | pantry | r8 medians circ 7 / pantry 7 / ceil 7 / coh 7 / provisioning 6 (no snack bags) | 6–8 (r8) |
| 6 | Café | industrial brick | r5 medians 6/5/6/7/6/6 (desk-like tables, white blocks at the counter front) | 5–7 (r5) |
| 7 | Café | nordic bakery | r5 medians 5/6/5/7/6/7 (counter still read as an island, tree beside it) | 4–7 (r5) |
| 8 | Café | minimal bar | r5 medians 8/6/7/8/7/7 (only seating 6) → r6 vases on ~1/3 tables | 6–8 (r5) |
| 9 | Café | chain banquette | r5 medians 7/7/6/7/8/7 (only circulation 6) | 6–8 (r5) |
| 10 | Café | floral moody | ablation s0–s3c done (lighting is the lever) | coherence 2→6; colour 0→7.5 |
| 11 | Warehouse | racks / storage | **DONE by the median rule: five calls on the r11 images, medians function 8, layout 7, industrial 8, ceiling 7, stock 7, signs of use 7**; sheet sent; next: dataset render | medians ≥ 7 |
| 12 | Warehouse | packing / loading | **DONE by the median rule: r26 (scene kr_whA2_packing_46200002) medians 8/7/8/7/7/7**; sheet loop_wh_r26.jpg sent. Fixes that got it there: gap_m read as wall distance, benches before racks, rules on the revision, merged lived_in, auto-exposure, packing props per bench | medians ≥ 7 |
| 13 | Shop | grocery sales floor | earlier sample | – |
| 14 | Shop | convenience store | r12 medians 8/6/7/7/7/4 (merch = coloured blocks: asset-bound; no baskets / out-of-place items) | 3–8 (r12) |
| 15 | Shop | clothing boutique | r12 medians 8/6/7/7/8/5 (garments flat slabs: asset-bound) | 4–8 (r12) |
| 16 | Shop | pharmacy | r12 medians 6/5/7/5/7/3 (one counter now, still reads as an office desk; OTC stock blank boxes) | 3–7 (r12) |
| 17 | Clinic | reception + waiting room | r28 medians 8/6/8/7/6/6 (r27 8/6/7/9/8/8; seats read as grey slabs, rows packed) | 5–8 (r28) |
| 18 | Clinic | exam room | **DONE by the median rule: r22 (scene kr_clinicV_exam_47310702) medians 9/8/9/8/8/7**; sheet loop_clinic_r22.jpg to the user; next: dataset render | medians ≥ 7 |
| 19 | Clinic | dental treatment room | **DONE by the median rule: r23 (scene kr_clinicW_dental_47310803) medians 9/8/9/8/8/8**; sheet loop_clinic_r23.jpg sent | medians ≥ 7 |
| 20 | Clinic | physiotherapy room | plateau r31-r33 at 8/6/8/8-9/6/4-5: one 40-48 m2 room holds the gym and the treatment beds, so the second plinth, the curtain bays and a clear gait lane never fit together; the floor scene F6 (gym + 2 treatment rooms) is the structural answer | 4–9 (r33) |

Style-fidelity eval (critic_style.md, 9 axes 0–10, anchor = floral s0 render in every call; compare by variant − anchor):
reference images are synthetic (Codex imagegen), the room shell is generated per seed and not judged.

| Café (kit F) | space | surf | light | furn | dens | decor | coher | real | multi | Δ vs anchor (sum) |
|---|---|---|---|---|---|---|---|---|---|---|
| industrial | 6 | 5 | 4 | 3 | 6 | 4 | 4 | 4 | 6 | +10 |
| nordic | 6 | 5 | 5 | 5 | 5 | 3 | 6 | 4 | 7 | +18 |
| minimal | 7 | 5 | 4 | 5 | 5 | 5 | 5 | 5 | 5 | +16 |
| chain | 7 | 4 | 5 | 3 | 6 | 4 | 5 | 4 | 5 | +7 |
| industrial G | 6 | 6 | 4 | 3 | 5 | 3 | 5 | 4 | 7 | +8 |
| nordic G | 6 | 5 | 4 | 4 | 4 | 4 | 4 | 3 | 6 | +8 |
| minimal G | 7 | 5 | 6 | 4 | 7 | 5 | 4 | 4 | 6 | +14 |
| chain G | 6 | 4 | 4 | 4 | 5 | 5 | 5 | 3 | 6 | +9 |
| industrial H | 7 | 5 | 4 | 4 | 6 | 5 | 5 | 5 | 7 | +10 |
| nordic H | 7 | 5 | 6 | 5 | 5 | 5 | 7 | 5 | 8 | +23 |
| minimal H | 7 | 4 | 6 | 4 | 6 | 4 | 5 | 4 | 6 | +17 |
| chain H | 6 | 5 | 4 | 3 | 4 | 4 | 5 | 4 | 6 | +3 |

Shared gaps: the furniture family (kit 'mixed' fell back to grey upholstered ABO chairs), plants (kits ask 9–14, renders had 1–3),
flat lighting without pools of light, floors (glossy orange pine / flat cream instead of pale oak / polished concrete).

G (kit plants to target, bistro chairs for 'mixed', new cooler) did not beat F: the new coral cooler, blond chairs drawn for 'mixed',
low-poly olive blobs, flat untextured wood and an unbalanced warm cast each cost more than the plants gained. All five fixed for H.

H (white balance 30%, wood grain, rebuilt olive trees, dark bistro 'mixed', neutral cooler): colour_score industrial 5.7→7.2,
nordic 4.7→5.7, minimal 4.9→6.0; d_warmth from +4..+6.5 to -0.6..-1.6. Chain stays bright (+21 L) -- its reference is a dark
golden-hour room the kit records as 'daylight high'.

## Multi-room floors (+10, user 2026-10-16: "지금 만드는 한개짜리신들은 유지하고 멀티룸 씬 10개더")

Single rooms stay. Why floors: a 17-22 m2 room capped the dataset at ~8 hover + 4 walk takes (exam room, measured); the user's target
is 30+ per mode, and real offices / clinics have many rooms. Same done rule (median of three critic calls >= 7, per room on the floor
sheet), then the hover + walk dataset render.

| # | Floor | Rooms | Status |
|---|---|---|---|
| F1 | Office floor A (open plan + glass) | open office hub, 2 meeting rooms, 2 private offices, pantry, restroom | r4 paged medians: meeting 8/7/8/8/8 + 8/7/8/7/7 PASS, pantry 8/7/7/7/7 PASS, open office 9/8/8/7/5, office_0-1 8/7/6/7/7, office_0-0 7/6/7/5/5, restroom 7/5/4/5/3 (open WC far from basin, painted), F 6 -> tiled restroom, basin beside WC; r5 rendering |
| F2 | Office floor B (corridor offices) | corridor, 6 private offices, meeting room, pantry, restroom | r5 medians: corridor 8/8/7/7/4, pantry 8/7/7/7/6, offices ~7/6/7/6/5 (0-4 6/5/7/5/4), meeting 7/6/7/5/6, restroom 4/5/6/3/2, F 6 -- offices cloned, floating guest chair, meeting under-seated, arched casing -> guest pair faces desk, whiteboard 50%; r6 rendering |
| F3 | Office floor C (loft) | open office hub, meeting room, 2 small offices, pantry, restroom | r4 paged medians: open office 9/8/8/8/6, pantry 8/7/7/6/7, office_0-0 7/7/6/6/6, office_0-1 7/6/7/5/5, restroom 7/6/5/5/3, meeting 6/6/7/5/7 (desk-sized table), F 7 -- empty ABO ladder shelves -> stocked inf bookcase; meeting table long-1.5 m |
| F4 | GP clinic | reception hub + corridor, 4 exam rooms, staff room, restroom | D3 r5 paged medians: corridor 8/9/7/7/5, exams 8/7/8/7/6, staff 8/7/8/7/6, manager 7/6/7/6/6, reception 7/6/7/5/4 (benches on walls -> 'empty hall'), exam 0-5 7/6/8/5/5 (desk unplaced), restroom 6/6/5/5/3 (open WC), F 6 -> lobby up to 5 wall benches + coffee table, shrinkable clinic desk; r6 rendering |
| F5 | Dental clinic | reception hub + corridor, 3 dental rooms, sterilisation, staff room, restroom | E3 r4 paged medians: dental 9/7/8/8/5 x3, corridor 8/7/7/6/5, staff 7/7/7/6/6, manager 7/5/7/7/5, reception 7/5/7/6/4 (rows mid-floor), steri 5/5/6/5/6, restroom 4/4/5/4/3 (2 stalls, pre <24 rule), F 6 -- open lite-door leaves read as 'tall cabinets'; r5 rendering |
| F6 | Physio / rehab clinic | reception (front) + office, corridor, gym, 2 treatment rooms, changing, restroom | r4 medians: corridor 8/9/8/7/5, gym 9/7/8/8/5, reception 8/7/8/7/5, treatment 8/6/8/7/6 + 7/5/8/6/5, manager 7/8/8/6/4, changing 7/7/7/6/4, restroom 5/6/7/4/3 (open WC, only a sliver in frame), F 7 -- use 3-6 is the floor-wide limit; restroom wides now frame the WC |
| F7 | Café A | dining hub, kitchen, storage, restroom | r7 paged medians: stockroom 8/6/7/7/7, dining 8/5/8/8/7, staff 5/6/6/4/5 (table at the window = ledge), restroom 4/6/5/2/2 (basin out of frame), F 5 -> staff table centred >= 12 m2, tiled restroom, basin beside WC; r8 rendering |
| F8 | Café B (bigger) | dining hub, kitchen, storage, 2 restrooms | r8 paged medians: dining 8/6/8/8/7 (pre aisle fix), stockroom 8/6/7/6/7, staff 7/7/6/6/7, restrooms 7/6/5/6/4 x2, F 6 -- restrooms want tile / frosted glass / no duct (open) |
| F9 | Convenience store | sales floor hub, stockroom, staff room, restroom | r2 medians: sales 7/7/7/5/6, staff 6/6/6/5/7, restroom 6/4/4/4/3, stockroom 6/6/6/4/5, F 6 — no visible till, stockroom unracked, restroom pre-stalls; r3 (no critic; read by eye): till present (c20, was close-up 5 off the 4-tile sheet), black slab = a cooler's back mid-floor, two stalls filled the 11 m2 restroom, stockroom racks unplaced (bench first) -> coolers against_wall, small-stockroom racks first, 1 stall < 14 m2; r4 rendering |
| F10 | Warehouse with office | warehouse hall hub, site office, break room, restroom | r6 paged medians: hall 8/7/8/7/7 PASS, break 8/7/7/7/7 PASS, site office 7/6/7/5/5, restroom 4/4/5/3/3 (2 stalls at 24.9 m2), F 6 -> restrooms always one open WC (+2nd basin >= 18 m2); r7 rendering |

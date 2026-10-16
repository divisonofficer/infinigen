# Non-home 20: LLM-loop scene campaign (goal set 2026-10-16)

Goal: 20 finished non-home interiors made by the generate → render → critique → generator-fix loop.

Done means: every applicable critic criterion ≥ 7 (target 8), a sheet the user has seen, then a dataset render (v2.1 naming `infinigen_<venue>_v2_1_<seed>`).

| # | Venue | Room / style | Status | Last critic (min–max) |
|---|---|---|---|---|
| 1 | Office | open office, glass meeting ref | loop r7 | 6–7 |
| 2 | Office | open office, high-rise ref | loop r7 | 6–8 |
| 3 | Office | meeting room | loop r7 | 7–8 |
| 4 | Office | private office | loop r7 | 7–8 |
| 5 | Office | pantry | r13: run 2.4 m complete, stools without a table → small-room ledge + coffee slot priority; r14 running | 5–6 (r13) |
| 6 | Café | industrial brick | H; café fridge under-counter, finer grain; I running | style Δ +10 (H), +8 (G) |
| 7 | Café | nordic bakery | H best so far; I running | style Δ +23 (H), +8 (G), +18 (F) |
| 8 | Café | minimal bar | H; I running | style Δ +17 (H), +14 (G) |
| 9 | Café | chain banquette | H: banquette placed but never in a view → hero close-ups; I running | style Δ +3 (H), +9 (G) |
| 10 | Café | floral moody | ablation s0–s3c done (lighting is the lever) | coherence 2→6; colour 0→7.5 |
| 11 | Warehouse | racks / storage | r3: racks stocked, roof industrial; r4 with image kit, 5 m, bench props running | 4–7 (r3) |
| 12 | Warehouse | packing / loading | r3: loaded pallet carries it; r4 with image kit running | 3–6 (r3) |
| 13 | Shop | grocery sales floor | earlier sample | – |
| 14 | Shop | convenience store | r3: lit coolers convincing; r4 with kit + one floor basket running | 5–7 (r3) |
| 15 | Shop | clothing boutique | r3: underlit → image kit, track spots ×3; r4 running | 5–7 (r3) |
| 16 | Shop | pharmacy | r3: stocked; desk mid-floor → counter + shelves on walls; r4 running | 5–8 (r3) |
| 17 | Clinic | reception + waiting room | r7: olive trees, chair on the patient side → 1 plant, 'behind' relation; r8 running | 3–8 (r7) |
| 18 | Clinic | exam room | r7: signs of use 2→6; r8 running | 5–8 (r7) |
| 19 | Clinic | dental treatment room | r7; r8 running | 5–8 (r7) |
| 20 | Clinic | physiotherapy room | r7: olive grove on the floor → cap 1 plant; r8 running | 3–8 (r7) |

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

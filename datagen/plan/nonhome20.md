# Non-home 20: LLM-loop scene campaign (goal set 2026-10-16)

Goal: 20 finished non-home interiors made by the generate → render → critique → generator-fix loop.

Done means: the **median of three independent critic calls** is ≥ 7 on every criterion (target 8), a sheet the user has seen, then a dataset render (v2.1 naming `infinigen_<venue>_v2_1_<seed>`). One call is not enough: the same storage images scored 7–9, 7–9, 6–8 and 6–8 in four calls (2026-10-16).

| # | Venue | Room / style | Status | Last critic (min–max) |
|---|---|---|---|---|
| 1 | Office | open office, glass meeting ref | loop r7 | 6–7 |
| 2 | Office | open office, high-rise ref | loop r7 | 6–8 |
| 3 | Office | meeting room | loop r7 | 7–8 |
| 4 | Office | private office | loop r7 | 7–8 |
| 5 | Office | pantry | r17-r23 plateau 6–7 (r23 provisioning 7; ceiling / coherence 6) | 6–7 |
| 6 | Café | industrial brick | M: auto-exposure, reference pendants (black dome), duct raised; colour 7.2; N running | raw 50 (M), 44 (L) |
| 7 | Café | nordic bakery | M: 15 cone pendants → bowl domes, max 7; colour 8.2; N running | raw 43 (M), 48 (L) |
| 8 | Café | minimal bar | M best; colour 8.0; N running | raw 50 (M), 48 (L) |
| 9 | Café | chain banquette | auto-exposure fixed brightness (colour 2.1 → 5.2); N running | raw 49 (M), 49 (L) |
| 10 | Café | floral moody | ablation s0–s3c done (lighting is the lever) | coherence 2→6; colour 0→7.5 |
| 11 | Warehouse | racks / storage | **DONE by the median rule: five calls on the r11 images, medians function 8, layout 7, industrial 8, ceiling 7, stock 7, signs of use 7**; sheet sent; next: dataset render | medians ≥ 7 |
| 12 | Warehouse | packing / loading | **DONE by the median rule: r26 (scene kr_whA2_packing_46200002) medians 8/7/8/7/7/7**; sheet loop_wh_r26.jpg sent. Fixes that got it there: gap_m read as wall distance, benches before racks, rules on the revision, merged lived_in, auto-exposure, packing props per bench | medians ≥ 7 |
| 13 | Shop | grocery sales floor | earlier sample | – |
| 14 | Shop | convenience store | r6; wide views 85° → 65° (lens distortion) | 5–7 (r6) |
| 15 | Shop | clothing boutique | r6; garments still read as slabs | 5–7 (r6) |
| 16 | Shop | pharmacy | r6 checkout 8; 'diamond shelf' = 85° lens distortion of the wall shelf (4 rounds) | 5–8 (r6) |
| 17 | Clinic | reception + waiting room | r24 medians 8/7/6/8/7/5 (magenta checker = clinic monitor without art kept an empty image; walls still tan at 60%) → r25 dark screens, walls 85% cool | 4–9 (r24) |
| 18 | Clinic | exam room | **DONE by the median rule: r22 (scene kr_clinicV_exam_47310702) medians 9/8/9/8/8/7**; sheet loop_clinic_r22.jpg to the user; next: dataset render | medians ≥ 7 |
| 19 | Clinic | dental treatment room | **DONE by the median rule: r23 (scene kr_clinicW_dental_47310803) medians 9/8/9/8/8/8**; sheet loop_clinic_r23.jpg sent | medians ≥ 7 |
| 20 | Clinic | physiotherapy room | r24 medians 8/7/8/8/7/4 (physio kit never fitted a wall; faceted ball) → r25 1 m kit, smooth ball | 4–9 (r24) |

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

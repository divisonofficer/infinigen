# datagen: Infinigen scene generation for robomituba

This directory holds the data-generation logic built on top of this Infinigen fork. It covers layout generation, Infinigen 2.0 rematerialing, architecture, LLM furnishing (room_planner), lived-in dressing and probe renders for the render → critique loop. Its outputs feed the robomituba IR / OpticalNav datasets.

The code is a snapshot of the live copies in the robomituba repo. Those are `tools/infinigen/` and `scripts/` in `divisonofficer/isaacmistuba`, from the shared checkout `/jarvis/project/robomituba`, branch `rescue/ir-dataset-recovery-20260828`, as of 2026-10-16. Render and campaign workers still import the robomituba paths. Until those paths are switched over to this branch, change both places together or treat this as the record.

## Layout

| dir | what |
|---|---|
| `scripts/` | `infinigen_gen.py` (generation entry point, presets, gin overrides), `floorplan_gen.py` (apartment / office / single-room plans; `ROBOMITUBA_STOREFRONT`), `infinigen_room_programs.py`, `infinigen_generate_indoors_safe.py`, plus the helpers they import |
| `tools/` | Blender-side passes: `rematerial_rooms_infinigen2.py` (Infinigen 2.0 shaders; venue / style / reference finishes), `architecture_pass.py` (pilasters, beams, ceiling kits, office grid / linear LEDs, exterior HDRI), `activity_pass_infinigen2.py` (the furnish / realize / dressing driver), `furnish_rooms.py` (ABO pools, placement, obstacles), `room_dressing.py` (closes exterior doors by leaf geometry), `ceiling_fixtures.py`, `tidy_objects_infinigen2.py`, `build_v2_scene.sh`, render and export helpers |
| `tools/room_planner/` | LLM furnishing. `client.py` (Claude planner, prompt v11, plan cache, learned-rule injection), `catalog.py` (vocabulary per room type), `realize.py` (relations, zones: workstation pod grid, meeting set, pantry run, glass meeting room, coffee bar; natural seat poses; desk clutter; physics settle), `proc_assets.py` (procedural furniture and props), `reference.py` (reference images → venue spec), `styles.py`, `design_knowledge.json` (rules learned by the critique loop, with evidence and status) |
| `loop/` | Render → critique loop: `venue_pipeline_v11.sh` (one room: layout → materials → architecture → plan → furnish → probe renders, normal + clay), `probe_views.py`, `render_views.py`, `sheet.py` (contact sheet), `critic_office.md` (brief for the independent critic agent) |
| `refs/` | Venue reference specs (`spec.json`) and provenance (`sources.json`). Images are not committed. Views marked `synthetic_view` were generated from one real photo and are not real multi-view observations. |
| `../infinigen/assets/objects/elements/doors/` | Fork patch. `ROBOMITUBA_DOOR_STYLE=office` gives commercial door types only, and casing bevels use the Blender 4.x `bevel_weight_edge` attribute. |

## The loop

`generate → render (normal + clay) → independent critic sub-agent → generic generator fix → fresh seeds`. Every finding becomes a rule in `room_planner/design_knowledge.json`. A rule starts as `proposed` and becomes `validated` only after scores rise on fresh layouts. Office rounds r1-r4 (2026-10-16) took the scores from 3-5 to 6-9.

## Runtime notes

- Blender: the bundled 4.2 (`tools/run_bundled_blender.py`). Infinigen 2.0 shaders come from a pip site (`--site`, default `/root/robomituba-envs/infinigen2-2.0.0a2-site`).
- The planner key is read from `~/.config/robomituba/anthropic_key` and is never committed.
- Assets: the ABO index, plus extra pools through `ROOM_EXTRA_ASSET_INDEXES` (HSSD, Poly Haven).

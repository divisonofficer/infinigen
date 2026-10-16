#!/bin/bash
# Single-room workplace sample: Infinigen layout + large furniture (solve_large; medium/small off) -> 2.0 materials -> LLM plan (+feedback) -> activity/realize/fixtures -> probe views (GPU 1)
#   [STOREFRONT=1] [REF=spec.json] venue_pipeline_v14.sh SEED ROOM_TYPE TAG VENUE [STYLE]
#   STOREFRONT=1: door + panoramic glass on the street wall; REF: a room_planner.reference spec (wall/floor/counter + images for the plan)
set -euo pipefail
S=$1; RT=$2; TAG=$3; VENUE=${4:-}; STYLE=${5:-}
REPO=/jarvis/project/robomituba; W=$REPO/out/infinigen_v2/kr_${TAG}_$S; F=$W/full; O=/tmp/claude-0/objreal; IGPY=/root/miniconda3/envs/infinigen/bin/python
mkdir -p $F; cd $REPO
[ -f $F/scene.blend ] || ROBOMITUBA_SINGLE_ROOM_AREA=${ROOM_AREA:-} ROBOMITUBA_DOOR_STYLE=${DOOR_STYLE:-} ROBOMITUBA_STOREFRONT=${STOREFRONT:-0} MPLBACKEND=Agg PYTHONPATH=$REPO/modules/infinigen python3 scripts/infinigen_gen.py --seed $S --floor-plan single_room \
  --room-type $RT --density normal_lived_in --stage full --base-config vanilla --small-objects activity --out $F \
  -p fast_solve_config.placeholder_reuse=3 -p fast_solve_config.factory_fail_limit=8 -p fast_solve_config.stall_limit=30 \
  -p compose_indoors.solve_medium_enabled=False ${VENUE:+-p compose_indoors.solve_large_enabled=False -p compose_indoors.floating_objs_enabled=False} \
  -p populate_doors.casing_chance=1.0 --run > $W/gen.log 2>&1
if [ ! -f $F/scene.blend ]; then                                 # solve_large failed for this room type: layout only, LLM + ABO place all
  echo "SOLVE_LARGE_FAILED $TAG -> layout only"
  ROBOMITUBA_SINGLE_ROOM_AREA=${ROOM_AREA:-} ROBOMITUBA_DOOR_STYLE=${DOOR_STYLE:-} ROBOMITUBA_STOREFRONT=${STOREFRONT:-0} MPLBACKEND=Agg PYTHONPATH=$REPO/modules/infinigen python3 scripts/infinigen_gen.py --seed $S --floor-plan single_room \
    --room-type $RT --density normal_lived_in --stage full --base-config vanilla --small-objects activity --out $F \
    -p compose_indoors.solve_large_enabled=False -p compose_indoors.solve_medium_enabled=False ${VENUE:+-p compose_indoors.floating_objs_enabled=False} --run > $W/gen_layout_only.log 2>&1
fi
[ -f $F/scene.blend ] || { echo "GEN_FAILED $TAG"; exit 1; }
echo "GEN_DONE $TAG large_objects=$(python3 -c "import json; print(sum(1 for o in json.load(open('$F/solve_state.json'))['objs'].values() if any('Factory' in str(o.get('generator') or '') for _ in [0])))")"
CUDA_VISIBLE_DEVICES= python3 tools/infinigen/run_bundled_blender.py -t 8 --background "$F/scene.blend" --python-exit-code 1 \
    --python tools/infinigen/rematerial_rooms_infinigen2.py -- --out "$F/scene_mat2.blend" --seed $S ${VENUE:+--venue $VENUE} ${STYLE:+--style $STYLE} ${REF:+--style $REF} > $W/rematerial.log 2>&1
# architectural envelope (pilasters, beams, soffit, accent wall, ceiling kit with track spots) before the plan
(cd /tmp && CUDA_VISIBLE_DEVICES= $IGPY $REPO/tools/infinigen/architecture_pass.py $F/scene_mat2.blend --out $F/scene_arch.blend --seed $S \
   ${REF:+--palette $REF} ${EXTERIOR:+--exterior $EXTERIOR} ${ARCH_ARGS:-} ${ARCHETYPE:+--archetype $ARCHETYPE}) > $W/arch.log 2>&1 || grep -q '^ARCH' $W/arch.log
(cd /tmp && CUDA_VISIBLE_DEVICES= $IGPY $REPO/tools/infinigen/room_planner/extract_rooms.py $F/scene_arch.blend --out $F/rooms.json) > $W/plan.log 2>&1
(cd $REPO/tools/infinigen && /root/miniconda3/bin/python3 -m room_planner.plan_scene $F/rooms.json --out $F/plans.json --seed $S ${VENUE:+--venue $VENUE} ${STYLE:+--style $STYLE} ${REF:+--reference $REF}) >> $W/plan.log 2>&1
grep -a '^{"room"' $W/plan.log | sed "s/^/$TAG /" || true
(cd /tmp && CUDA_VISIBLE_DEVICES= $IGPY $REPO/tools/infinigen/activity_pass_infinigen2.py $F/scene_arch.blend --out $F/scene_mat2_activity.blend \
   --solve-state $F/solve_state.json --seed $S --abo --plans $F/plans.json) > $W/activity.log 2>&1 || grep -q '^ACTIVITY' $W/activity.log
(cd /tmp && CUDA_VISIBLE_DEVICES= $IGPY $REPO/tools/infinigen/kit_lighting.py $F/scene_mat2_activity.blend --out $F/scene_mat2_activity.blend \
   --plans $F/plans.json --seed $S) > $W/kitlight.log 2>&1 || grep -q '^KITLIGHT' $W/kitlight.log
echo "ACTIVITY_DONE $TAG $(grep -a '^ACTIVITY' $W/activity.log | grep -o '"furniture_added": [0-9]*')"
if [ -n "${VIEWS:-}" ]; then cp "$VIEWS" $O/views_$TAG.json; else   # fixed cameras (ablations: every stage seen from the same views)
(cd /tmp && CUDA_VISIBLE_DEVICES= $IGPY $O/probe_views.py $F/scene_mat2_activity.blend $O/views_$TAG.json 8) > $O/probe_$TAG.log 2>&1 || grep -q '^VIEWS' $O/probe_$TAG.log
fi
rm -rf $O/rv_$TAG; mkdir -p $O/rv_$TAG
PROBE_DAYLIGHT=1 CUDA_VISIBLE_DEVICES=${RENDER_GPU:-1} flock $O/gpu${RENDER_GPU:-1}.lock timeout 1h python3 tools/infinigen/run_bundled_blender.py --background $F/scene_mat2_activity.blend --python $O/render_views.py -- $O/views_$TAG.json $O/rv_$TAG > $O/rv_$TAG.log 2>&1
rm -rf $O/rv_${TAG}_clay; mkdir -p $O/rv_${TAG}_clay
CLAY=1 PROBE_DAYLIGHT=1 CUDA_VISIBLE_DEVICES=${RENDER_GPU:-1} flock $O/gpu${RENDER_GPU:-1}.lock timeout 1h python3 tools/infinigen/run_bundled_blender.py --background $F/scene_mat2_activity.blend --python $O/render_views.py -- $O/views_$TAG.json $O/rv_${TAG}_clay > $O/rv_${TAG}_clay.log 2>&1 || true
echo "VIEWS_DONE $TAG $(ls $O/rv_$TAG | wc -l)"

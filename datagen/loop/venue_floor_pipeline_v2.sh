#!/bin/bash
# Multi-room floor (user 2026-10-16: +10 floor scenes): Infinigen floor-plan LAYOUT only (the large-furniture solve ran 3 h+ on an office
# floor) -> 2.0 materials -> architecture -> LLM plan per room -> activity/realize/fixtures -> kit lighting -> probe views -> render
#   [REF=kit.json] [ARCHETYPE=..] [DOOR_STYLE=office] [ROOM_VENUES=map.json] venue_floor_pipeline.sh SEED FLOOR_PLAN TAG
# ROOM_VENUES: {room_name: venue} for floors whose rooms take a venue's rules (clinic, cafe); office rooms keep their native types.
set -euo pipefail
S=$1; FP=$2; TAG=$3
REPO=/jarvis/project/robomituba; W=$REPO/out/infinigen_v2/kr_${TAG}_$S; F=$W/full; O=/tmp/claude-0/objreal; IGPY=/root/miniconda3/envs/infinigen/bin/python
mkdir -p $F; cd $REPO
[ -f $F/scene.blend ] || ROBOMITUBA_DOOR_STYLE=${DOOR_STYLE:-} MPLBACKEND=Agg PYTHONPATH=$REPO/modules/infinigen python3 scripts/infinigen_gen.py --seed $S --floor-plan $FP \
  --density normal_lived_in --stage full --base-config vanilla --small-objects activity --out $F \
  -p compose_indoors.solve_large_enabled=False -p compose_indoors.solve_medium_enabled=False -p compose_indoors.floating_objs_enabled=False \
  -p populate_doors.casing_chance=1.0 ${GEN_ARGS:+-p "$GEN_ARGS"} --run > $W/gen.log 2>&1
[ -f $F/scene.blend ] || { echo "GEN_FAILED $TAG"; exit 1; }
echo "GEN_DONE $TAG rooms=$(python3 -c "import json; d=json.load(open('$F/floor_plan.json')); print(len(d.get('rooms',{})))" 2>/dev/null || echo ?)"
[ -f $F/scene_mat2.blend ] || CUDA_VISIBLE_DEVICES= python3 tools/infinigen/run_bundled_blender.py -t 8 --background "$F/scene.blend" --python-exit-code 1 \
    --python tools/infinigen/rematerial_rooms_infinigen2.py -- --out "$F/scene_mat2.blend" --seed $S ${REF:+--style $REF} > $W/rematerial.log 2>&1
[ -f $F/scene_arch.blend ] || { (cd /tmp && CUDA_VISIBLE_DEVICES= $IGPY $REPO/tools/infinigen/architecture_pass.py $F/scene_mat2.blend --out $F/scene_arch.blend --seed $S \
   ${REF:+--palette $REF} ${ARCHETYPE:+--archetype $ARCHETYPE}) > $W/arch.log 2>&1 || grep -q '^ARCH' $W/arch.log; }
(cd /tmp && CUDA_VISIBLE_DEVICES= $IGPY $REPO/tools/infinigen/room_planner/extract_rooms.py $F/scene_arch.blend --out $F/rooms.json) > $W/plan.log 2>&1
(cd $REPO/tools/infinigen && /root/miniconda3/bin/python3 -m room_planner.plan_scene $F/rooms.json --out $F/plans.json --seed $S \
   ${REF:+--reference $REF} $( [ -n "${ROOM_VENUES:-}" ] && echo "--room-venues $ROOM_VENUES" || { [ -f $F/room_venues.json ] && echo "--room-venues $F/room_venues.json"; } )) >> $W/plan.log 2>&1
grep -a '^{"room"' $W/plan.log | sed "s/^/$TAG /" || true
(cd /tmp && CUDA_VISIBLE_DEVICES= $IGPY $REPO/tools/infinigen/activity_pass_infinigen2.py $F/scene_arch.blend --out $F/scene_mat2_activity.blend \
   --solve-state $F/solve_state.json --seed $S --abo --plans $F/plans.json) > $W/activity.log 2>&1 || grep -q '^ACTIVITY' $W/activity.log
(cd /tmp && CUDA_VISIBLE_DEVICES= $IGPY $REPO/tools/infinigen/kit_lighting.py $F/scene_mat2_activity.blend --out $F/scene_mat2_activity.blend \
   --plans $F/plans.json --seed $S) > $W/kitlight.log 2>&1 || grep -q '^KITLIGHT' $W/kitlight.log
echo "ACTIVITY_DONE $TAG $(grep -a '^ACTIVITY' $W/activity.log | grep -o '"furniture_added": [0-9]*')"
(cd /tmp && CUDA_VISIBLE_DEVICES= $IGPY $O/probe_views.py $F/scene_mat2_activity.blend $O/views_$TAG.json 10) > $O/probe_$TAG.log 2>&1 || grep -q '^VIEWS' $O/probe_$TAG.log
REF_L=""
if [ -n "${REF:-}" ]; then REF_L=$(python3 -c "
import json,sys; sys.path.insert(0,'$REPO/tools/infinigen'); import style_metrics as sm
k=json.load(open('$REF')); ims=k.get('images') or []
print(round(sm.stats(sm.load(ims))[1]['mean_L'],1) if ims else '')" 2>/dev/null || true); fi
for M in "" _clay; do
  rm -rf $O/rv_$TAG$M; mkdir -p $O/rv_$TAG$M
  env ${M:+CLAY=1} REF_L=$REF_L PROBE_DAYLIGHT=1 CUDA_VISIBLE_DEVICES=${RENDER_GPU:-1} flock $O/gpu${RENDER_GPU:-1}.lock timeout 2h python3 tools/infinigen/run_bundled_blender.py --background $F/scene_mat2_activity.blend --python $O/render_views.py -- $O/views_$TAG.json $O/rv_$TAG$M > $O/rv_$TAG$M.log 2>&1 || true
done
echo "VIEWS_DONE $TAG $(ls $O/rv_$TAG | wc -l)"

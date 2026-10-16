#!/bin/bash
# One ablation stage on a FIXED layout and a FIXED plan: copy the base layout, rematerial / architecture / activity / kit lighting with
# this stage's spec, render the fixed views (normal + clay).  ablate_stage.sh BASE_DIR STAGE_SPEC TAG [PLAN_FROM]
#   PLAN_FROM: a plans.json whose furniture plan is reused (its style_spec is replaced by STAGE_SPEC); empty = plan from the spec
set -euo pipefail
B=$1; SPEC=$2; TAG=$3; PLAN_FROM=${4:-}
REPO=/jarvis/project/robomituba; O=/tmp/claude-0/objreal; IGPY=/root/miniconda3/envs/infinigen/bin/python
S=$(basename $B | sed 's/.*_//'); W=$REPO/out/infinigen_v2/kr_${TAG}_$S; F=$W/full; mkdir -p $F
cp $B/full/scene.blend $B/full/solve_state.json $F/
cd $REPO
CUDA_VISIBLE_DEVICES= python3 tools/infinigen/run_bundled_blender.py -t 8 --background "$F/scene.blend" --python-exit-code 1 \
    --python tools/infinigen/rematerial_rooms_infinigen2.py -- --out "$F/scene_mat2.blend" --seed $S --venue cafe --style $SPEC > $W/rematerial.log 2>&1
(cd /tmp && CUDA_VISIBLE_DEVICES= $IGPY $REPO/tools/infinigen/architecture_pass.py $F/scene_mat2.blend --out $F/scene_arch.blend --seed $S \
   --palette $SPEC --archetype warm) > $W/arch.log 2>&1 || grep -q '^ARCH' $W/arch.log
(cd /tmp && CUDA_VISIBLE_DEVICES= $IGPY $REPO/tools/infinigen/room_planner/extract_rooms.py $F/scene_arch.blend --out $F/rooms.json) > $W/plan.log 2>&1
if [ -n "$PLAN_FROM" ]; then
  python3 -c "import json,sys; p=json.load(open('$PLAN_FROM')); p['style_spec']=json.load(open('$SPEC')); json.dump(p,open('$F/plans.json','w'))"
else
  (cd $REPO/tools/infinigen && /root/miniconda3/bin/python3 -m room_planner.plan_scene $F/rooms.json --out $F/plans.json --seed $S --venue cafe --reference $SPEC) >> $W/plan.log 2>&1
fi
(cd /tmp && CUDA_VISIBLE_DEVICES= $IGPY $REPO/tools/infinigen/activity_pass_infinigen2.py $F/scene_arch.blend --out $F/scene_mat2_activity.blend \
   --solve-state $F/solve_state.json --seed $S --abo --plans $F/plans.json) > $W/activity.log 2>&1 || grep -q '^ACTIVITY' $W/activity.log
(cd /tmp && CUDA_VISIBLE_DEVICES= $IGPY $REPO/tools/infinigen/kit_lighting.py $F/scene_mat2_activity.blend --out $F/scene_mat2_activity.blend \
   --plans $F/plans.json --seed $S) > $W/kitlight.log 2>&1 || grep -q '^KITLIGHT' $W/kitlight.log
echo "ACTIVITY_DONE $TAG $(grep -a '^KITLIGHT' $W/kitlight.log)"
if [ ! -f $O/views_ablation_floral.json ]; then
  (cd /tmp && PROBE_HFOV=62 PROBE_LABEL=cafe PROBE_REFVIEWS=1 CUDA_VISIBLE_DEVICES= $IGPY $O/probe_views.py $F/scene_mat2_activity.blend $O/views_ablation_floral.json 4) > $O/probe_$TAG.log 2>&1 || true
fi
rm -rf $O/rv_$TAG $O/rv_${TAG}_clay; mkdir -p $O/rv_$TAG $O/rv_${TAG}_clay
PROBE_DAYLIGHT=1 CUDA_VISIBLE_DEVICES=${RENDER_GPU:-3} flock $O/gpu${RENDER_GPU:-3}.lock timeout 1h python3 tools/infinigen/run_bundled_blender.py --background $F/scene_mat2_activity.blend --python $O/render_views.py -- $O/views_ablation_floral.json $O/rv_$TAG > $O/rv_$TAG.log 2>&1
CLAY=1 PROBE_DAYLIGHT=1 CUDA_VISIBLE_DEVICES=${RENDER_GPU:-3} flock $O/gpu${RENDER_GPU:-3}.lock timeout 1h python3 tools/infinigen/run_bundled_blender.py --background $F/scene_mat2_activity.blend --python $O/render_views.py -- $O/views_ablation_floral.json $O/rv_${TAG}_clay > $O/rv_${TAG}_clay.log 2>&1 || true
echo "VIEWS_DONE $TAG $(ls $O/rv_$TAG | wc -l)"

#!/bin/bash
# Re-probe and re-render an existing scene with the current probe_views.py: reprobe.sh TAG LABEL GPU  (scene untouched)
TAG=$1; LABEL=$2; G=$3
REPO=/jarvis/project/robomituba; O=/tmp/claude-0/objreal; IGPY=/root/miniconda3/envs/infinigen/bin/python
F=$(ls -d $REPO/out/infinigen_v2/kr_${TAG}_*/full | head -1)
cd $REPO
(cd /tmp && PROBE_HFOV=65 PROBE_LABEL=$LABEL CUDA_VISIBLE_DEVICES= $IGPY $O/probe_views.py $F/scene_mat2_activity.blend $O/views_$TAG.json 8) > $O/probe_$TAG.log 2>&1
for M in "" _clay; do
  rm -rf $O/rv_$TAG$M; mkdir -p $O/rv_$TAG$M
  env ${M:+CLAY=1} PROBE_DAYLIGHT=1 CUDA_VISIBLE_DEVICES=$G flock $O/gpu$G.lock timeout 1h python3 tools/infinigen/run_bundled_blender.py --background $F/scene_mat2_activity.blend --python $O/render_views.py -- $O/views_$TAG.json $O/rv_$TAG$M > $O/rv_$TAG$M.log 2>&1
done
echo "REPROBED $TAG $(ls $O/rv_$TAG | wc -l)"

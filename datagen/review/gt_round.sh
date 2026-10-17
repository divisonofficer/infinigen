#!/bin/bash
# gt_round.sh TAG ROUND SEED GPU [wait_out_file]  -- ground-truth channels (albedo/normal/rough/metal) of the first wide of every room
# of a finished round; with wait_out_file it first waits for that run's VIEWS_DONE.
TAG=$1; RND=$2; SEED=$3; GPU=$4; WAIT=$5; O=/tmp/claude-0/objreal; REPO=/jarvis/project/robomituba
[ -n "$WAIT" ] && until grep -q "^VIEWS_DONE" "$O/$WAIT" 2>/dev/null; do sleep 60; done
OUT=$O/gt_${TAG}_${RND}; rm -rf $OUT; mkdir -p $OUT; cd $REPO
CUDA_VISIBLE_DEVICES=$GPU flock $O/gpu$GPU.lock timeout 3600 python3 tools/infinigen/run_bundled_blender.py --background \
  out/infinigen_v2/kr_${TAG}_${SEED}/full/scene_mat2_activity.blend --python $O/render_gt_views.py -- $O/views_${TAG}.json $OUT > $O/gt_${TAG}_${RND}.log 2>&1
echo "GT_DONE $TAG $RND $(ls $OUT | wc -l)"

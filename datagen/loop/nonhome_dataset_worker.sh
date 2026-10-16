#!/bin/bash
# Dataset render worker for finished non-home scenes: nonhome_dataset_worker.sh GPU
# Takes the next unclaimed, unrendered line of nonhome_dataset_queue.txt; hover 32 takes x 10 poses, walk 32 takes x 30 poses
# (user 2026-10-16: 'hover walk 30+ take each'); idles 300 s when the queue is empty, so a newly passed scene starts on its own.
G=$1; O=/tmp/claude-0/objreal; ROOT=/bean/ir_dataset_work/hssd_ir_apartment_v2; CL=$ROOT/.claims_nonhome; mkdir -p $CL
export NOBAKE_WORK=/bean/ir_dataset_work/infinigen_v2_nobake_work HSSD_IR_STAGE_ROOT=/bean/ir_dataset_work/hssd_ir_stage_nonhome
cd /jarvis/project/robomituba
while true; do
  picked=
  while read -r S SRC; do
    [ -z "$S" ] && continue; case "$S" in \#*) continue;; esac
    [ -f "$ROOT/$S/hover/four_pass.json" ] && [ -f "$ROOT/$S/walk/four_pass.json" ] && continue
    mkdir "$CL/$S" 2>/dev/null || continue          # another worker has it
    picked=$S
    echo "$(date -u +%FT%TZ) START $S gpu$G"
    if timeout 20h tools/infinigen/run_nobake_scene.sh "$S" "$SRC" "$ROOT" "$G" 320 32 960 32 > $O/dataset_$S.log 2>&1; then
      echo "$(date -u +%FT%TZ) DONE $S"
    else
      echo "$(date -u +%FT%TZ) FAILED $S rc=$? (log $O/dataset_$S.log; claim kept)"; continue
    fi
    rmdir "$CL/$S"
  done < $O/nonhome_dataset_queue.txt
  [ -z "$picked" ] && sleep 300
done

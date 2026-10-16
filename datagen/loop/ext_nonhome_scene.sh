#!/bin/bash
# Hover extension of one finished non-home scene toward 32 takes (user 2026-10-16: 30+ takes): ext_nonhome_scene.sh SCENE GPU
export HOVER_EXT_OUT_ROOT=/bean/ir_dataset_work/hssd_ir_apartment_v2
export HOVER_EXT_SCENE_GLOB="$1"
export HOVER_EXT_SKIP=
export HOVER_EXT_NOBAKE_WORK=/bean/ir_dataset_work/infinigen_v2_nobake_work
export HOVER_EXT_RES=512x384
export HOVER_EXT_HOVER_ARGS="--azimuth-span-deg 130 --min-take-frames 8 --frame-budget 10"
export HOVER_EXT_WALK_ARGS="--min-take-frames 10"
export HOVER_EXT_MIN_FREE_GB=5
export HOVER_EXT_STAGE=/bean/ir_dataset_work/hover_ext_stage_nonhome
cd /jarvis/project/robomituba
exec python3 -u apps/extend_apartment_hover.py --gpu "$2" --slot nonhome --scene "$1" --target-frames 320 --max-visits 4

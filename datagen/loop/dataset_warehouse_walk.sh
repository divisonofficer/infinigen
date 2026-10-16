#!/bin/bash
# Warehouse dataset render with walk headroom for a high-bay roof (HSSD_IR_WALK_CEILING_MAX_M, gated; unset = 3.00 m): SCENE SRC GPU
S=$1; SRC=$2; G=$3; ROOT=/bean/ir_dataset_work/hssd_ir_apartment_v2
export NOBAKE_WORK=/bean/ir_dataset_work/infinigen_v2_nobake_work HSSD_IR_STAGE_ROOT=/bean/ir_dataset_work/hssd_ir_stage_nonhome HSSD_IR_WALK_CEILING_MAX_M=4.6
cd /jarvis/project/robomituba
timeout 20h tools/infinigen/run_nobake_scene.sh "$S" "$SRC" "$ROOT" "$G" 320 32 960 32 && rmdir "$ROOT/.claims_nonhome/$S" 2>/dev/null; echo "WAREHOUSE_DATASET_EXIT $S $?"

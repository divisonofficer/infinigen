#!/bin/bash
# usage: floor_monitor.sh OUT...  -- one line per ACTIVITY_DONE / VIEWS_DONE / error, and EXITED_WITHOUT_VIEWS when a run dies silently
cd /tmp/claude-0/objreal
declare -A seen pos
for o in "$@"; do pos[$o]=0; done
sleep 20
while true; do
  for o in "$@"; do
    [ -f $o ] || continue
    n=$(wc -l < $o)
    if [ $n -gt ${pos[$o]} ]; then
      sed -n "$((${pos[$o]}+1)),${n}p" $o | grep -E "ACTIVITY_DONE|VIEWS_DONE|Traceback|Error|Segmentation|corrupted|Killed" | cut -c1-200
      pos[$o]=$n
    fi
    t=${o#venue_}; t=${t%_r*.out}
    alive=$(ps -eo args | awk -v t="$t" '($1=="/bin/bash" || $1=="bash") && ($2=="./venue_floor_pipeline_v2.sh" || $2=="venue_floor_pipeline_v2.sh") && $NF==t' | wc -l)
    if [ "$alive" = 0 ] && [ -z "${seen[$o]}" ]; then
      seen[$o]=1; grep -q VIEWS_DONE $o || echo "EXITED_WITHOUT_VIEWS $o"
    fi
  done
  sleep 30
done

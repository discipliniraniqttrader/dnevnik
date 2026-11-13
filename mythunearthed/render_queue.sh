#!/bin/bash
# Renders all approved topics one after another; skips finished ones (caches make reruns cheap).
cd /home/user/zenit
for t in ark_covenant sodom lost_tribes jonah eden babel jericho ophir abraham elijah samson; do
  if [ -f topics/$t/out/${t}_9mb.mp4 ]; then echo "skip $t"; continue; fi
  echo "$(date +%H:%M) start $t"
  python3 make_short.py topics/$t > topics/$t/run.log 2>&1 && echo "$(date +%H:%M) done $t" || echo "$(date +%H:%M) FAIL $t"
done
echo "$(date +%H:%M) queue finished"

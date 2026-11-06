#!/bin/bash
# Run a script in the shared editor, retrying while another agent holds the remote-exec connection.
#   bash Tools/lighting/run.sh <abs or Tools-relative script.py> [args...]
T="J:/Projets/Unreal_Projects/Guess Who/Tools"
S="$1"; shift
case "$S" in /*|?:*) ;; *) S="$T/$S";; esac
for i in 1 2 3 4 5 6 7 8; do
  out=$(python -I -X utf8 "$T/level/ue_main.py" "$S" "$@" 2>&1)
  if echo "$out" | grep -q "interactive editor not found\|ConnectionAbortedError\|ConnectionResetError"; then sleep 4; continue; fi
  echo "$out"; exit 0
done
echo "$out"; exit 1

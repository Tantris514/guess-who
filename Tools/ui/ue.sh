#!/bin/bash
# Run a Tools/ui script in the shared interactive editor (absolute path, retries while the editor is busy/restarting).
export MSYS_NO_PATHCONV=1
T="J:/Projets/Unreal_Projects/Guess Who/Tools"
S="$1"; shift
case "$S" in /*|?:*) ;; *) S="$T/ui/$S";; esac
for i in 1 2 3 4 5 6; do
  out=$(python -I -X utf8 "$T/ui/ue_run.py" "$S" "$@" 2>&1)
  if echo "$out" | grep -q "interactive editor not found"; then echo "[ue.sh] editor busy, retry $i" >&2; sleep 15; continue; fi
  echo "$out"; exit 0
done
echo "[ue.sh] gave up"; exit 3

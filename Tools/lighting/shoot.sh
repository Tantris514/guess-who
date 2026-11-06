#!/bin/bash
# Robust review-cam shots (one connection per camera, retries when another agent's command aborts ours).
#   bash Tools/lighting/shoot.sh <tag> [wait] [cam1,cam2,...]
T="J:/Projets/Unreal_Projects/Guess Who/Tools"
TAG="$1"; WAIT="${2:-7}"; ONLY="$3"
ALL="Cam_Ballroom_Diag Cam_Ballroom_Stage Cam_Billiard Cam_Billiard_Bar Cam_Cloakroom Cam_Conservatory Cam_Conservatory_Up Cam_CorridorE Cam_CorridorW Cam_Dining_Fire Cam_Dining_Table Cam_Hall_FromCloak Cam_Hall_FromGallery Cam_Hall_Stairs Cam_Library_Fire Cam_Library_Shelves Cam_Study"
[ -n "$ONLY" ] && ALL="${ONLY//,/ }"
for c in $ALL; do
  for try in 1 2 3 4 5 6 7 8; do
    if python -I -X utf8 "$T/qa/shoot_cams.py" --tag "$TAG" --wait "$WAIT" --only "$c" 2>/dev/null | grep -q "^ok"; then
      echo "ok $c"; break
    fi
    echo "retry $c ($try)"; sleep 6
  done
done

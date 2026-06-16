#!/usr/bin/env bash
#
# Make buildings + regions baselines for the CURRENTLY INSTALLED game version,
# auto-named baselines/baseline_{buildings,regions}_v<version>.xlsx.
#
# Workflow: switch the Steam version (Properties -> Betas), let it download,
# then run this once. Repeat for each version you want to keep as a diff
# reference (regions map-diff / regions diff / diff).
#
# Usage:
#   bash scripts/make_baseline.sh                    # auto-detect the install
#   PYTHON=py bash scripts/make_baseline.sh          # custom Python launcher
#   GAME_ROOT="D:/Games/Victoria 3" bash scripts/make_baseline.sh   # force path
#
# Windows: run from Git Bash.

set -uo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-python}"
GR=(); [ "${GAME_ROOT:-}" ] && GR=(--game-root "$GAME_ROOT")

VER="$("$PY" - <<'PYEOF'
import os
from pathlib import Path
from v3_eat.game_root import find_game_root
from v3_eat.loader import _load_version
gr = os.environ.get("GAME_ROOT")
root = Path(gr) if gr else find_game_root(None)
print(_load_version(root)[1])   # rawVersion, e.g. 1.6.2
PYEOF
)" || { echo "ERROR: could not detect the game (is Victoria 3 installed / detected?)"; exit 1; }

[ -z "$VER" ] && { echo "ERROR: empty version string — game not detected"; exit 1; }
echo "Detected game version: $VER"

BB="$PWD/baselines/baseline_buildings_v$VER.xlsx"
BR="$PWD/baselines/baseline_regions_v$VER.xlsx"
"$PY" -m v3_eat report        --out "$BB" "${GR[@]}"
"$PY" -m v3_eat regions report --out "$BR" "${GR[@]}"
echo
echo "Wrote:"
echo "  baselines/baseline_buildings_v$VER.xlsx"
echo "  baselines/baseline_regions_v$VER.xlsx"
echo "Diff a later version against it with e.g.:  v3-eat regions map-diff baseline_regions_v$VER.xlsx <newer>.xlsx"

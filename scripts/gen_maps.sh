#!/usr/bin/env bash
#
# Regenerate the full Feature-2b map gallery into out/regions/maps/.
# Exercises every `regions map…` command + option once, bucketed into subfolders.
#
# Usage:
#   bash scripts/gen_maps.sh                 # default (auto-detects the V3 install)
#   PYTHON=py bash scripts/gen_maps.sh       # use a different Python launcher
#   GAME_ROOT="D:/Games/Victoria 3" bash scripts/gen_maps.sh   # force the game path
#
# Windows: run it from Git Bash (ships with Git for Windows). The commands are
# just `python -m v3_ema …`, so a PowerShell user can equally copy them by hand.
#
# Outputs go under out/regions/ (git-ignored) — nothing here is committed.

set -uo pipefail
cd "$(dirname "$0")/.."                       # project root (scripts/..)

PY="${PYTHON:-python}"
M="out/regions/maps"
OLD="baseline_regions_v1.8.7.xlsx"            # bundled baselines (baselines/ is auto-searched)
NEW="baseline_regions_v1.13.4.xlsx"
GR=(); [ "${GAME_ROOT:-}" ] && GR=(--game-root "$GAME_ROOT")

run() { echo; echo ">>> $*"; "$@" || echo "    (command failed — continuing)"; }

echo "== V3_EMA Feature 2b — regenerating all maps into $M/ =="

# 1. Gallery: every layer as PNG + vector SVG, plus the interactive HTML viewer
run "$PY" -m v3_ema regions map --all --svg "${GR[@]}"

# 2. Crop-distribution maps (16 crops) -> maps/crops/
run "$PY" -m v3_ema regions map --crops --svg "${GR[@]}"

# 3. 1836 national borders on every layer (civilized filter) -> maps/national/
run "$PY" -m v3_ema regions map --all --countries --format png --out "$M/national" "${GR[@]}"

# 4. Recognized-only national borders -> maps/national_recognized/
run "$PY" -m v3_ema regions map --metric total_capacity --countries --country-filter recognized \
    --format png --out "$M/national_recognized" "${GR[@]}"

# 5. High-res showcase (native 8192 + borders + SVG) -> maps/showcase/
run "$PY" -m v3_ema regions map --metric total_capacity --full-res --countries --svg \
    --format png --out "$M/showcase" "${GR[@]}"

# 6. Option demos (grid+cmap, log+no-borders, gamma+reverse) -> maps/options/
run "$PY" -m v3_ema regions map --metric building_coal_mine --grid --cmap magma \
    --format png --out "$M/options" "${GR[@]}"
run "$PY" -m v3_ema regions map --metric building_gold_mine --log-scale --no-borders \
    --format png --out "$M/options" "${GR[@]}"
run "$PY" -m v3_ema regions map --metric building_iron_mine --gamma 1.0 --reverse --cmap viridis \
    --format png --out "$M/options" "${GR[@]}"

# 7. Cross-version change maps -> maps/diffs/
run "$PY" -m v3_ema regions map-diff "$OLD" "$NEW" --metric building_coal_mine --countries --svg "${GR[@]}"
run "$PY" -m v3_ema regions map-diff "$OLD" "$NEW" --metric total_capacity "${GR[@]}"
run "$PY" -m v3_ema regions map-diff "$OLD" "$NEW" --metric building_iron_mine "${GR[@]}"

# 8. Multi-version timeline viewer (default + a no-current variant)
run "$PY" -m v3_ema regions map-timeline "$OLD" "$NEW" "${GR[@]}"
run "$PY" -m v3_ema regions map-timeline "$OLD" "$NEW" --no-current \
    --out "$M/timeline_nocurrent" "${GR[@]}"

# 9. Excel region report with the map atlas embedded
run "$PY" -m v3_ema regions report --maps --out report_regions_with_maps.xlsx "${GR[@]}"

echo
echo "== Done =="
echo "   $M/                  gallery PNG/SVG + resource_map.html + resource_timeline.html"
echo "   $M/crops/            16 crop-distribution maps"
echo "   $M/national/         national borders on every layer"
echo "   $M/diffs/            cross-version change maps"
echo "   $M/showcase/         native-8192 showcase"
echo "   $M/options/ national_recognized/ timeline_nocurrent/   option variants"
echo "   out/regions/reports/report_regions_with_maps.xlsx       Excel + embedded atlas"

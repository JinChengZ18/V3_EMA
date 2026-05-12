from __future__ import annotations
import argparse
import sys
from datetime import datetime
from pathlib import Path

from . import __version__
from .game_root import (
    clear_cached,
    find_game_root,
    is_valid_game_root,
    load_cached,
    save_cached,
)
from .loader import load
from .analysis.construction import build_construction_rows
from .analysis.diff import diff_snapshots, read_report
from .analysis.regions import build_region_rows
from .analysis.regions_diff import diff_regions_snapshots, read_regions_report
from .analysis.rows import build_rows
from .i18n import get_ui, ui_lang_for
from .output.csv_writer import write_csv
from .output.diff_writer import write_diff_xlsx
from .output.regions_diff_writer import write_regions_diff_xlsx
from .output.regions_writer import write_regions_xlsx
from .output.xlsx_writer import ReportMeta, write_xlsx
from .util.logging import get_logger

log = get_logger()

DEFAULT_OUT_DIR = Path(__file__).resolve().parent.parent / "out"
# Per-feature subdirectories so out/ stays organized as features grow.
# Layout: out/<feature>/{reports,diffs}/
DEFAULT_BUILDINGS_REPORTS_DIR = DEFAULT_OUT_DIR / "buildings" / "reports"
DEFAULT_BUILDINGS_DIFFS_DIR = DEFAULT_OUT_DIR / "buildings" / "diffs"
DEFAULT_REGIONS_REPORTS_DIR = DEFAULT_OUT_DIR / "regions" / "reports"
DEFAULT_REGIONS_DIFFS_DIR = DEFAULT_OUT_DIR / "regions" / "diffs"
# Bundled baselines that ship with the project — let users diff right away
# without having to first generate one for the previous game version.
DEFAULT_BASELINES_DIR = Path(__file__).resolve().parent.parent / "baselines"
# Legacy locations kept for backwards-compat input lookups
_LEGACY_REPORTS_DIR = DEFAULT_OUT_DIR / "reports"
_LEGACY_DIFFS_DIR = DEFAULT_OUT_DIR / "diffs"


def _add_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--game-root", type=Path, default=None,
                   help="Victoria 3 install root (parent of game/). If omitted, "
                        "auto-detected from Steam libraries; cached after first "
                        "successful detection. See `v3-ema config --help`.")
    p.add_argument("--lang", default="simp_chinese",
                   help="Game-data localization language (e.g. simp_chinese, english, "
                        "french, german, japanese, korean, polish, russian, spanish, "
                        "turkish, braz_por). Default: simp_chinese")
    p.add_argument("--ui-lang", choices=["zh", "en", "auto"], default="auto",
                   help="Tool-UI language (sheet names, headers). 'auto' (default) = "
                        "zh for simp_chinese, en for everything else")


def _resolve_game_root(args) -> Path | None:
    """Wrap find_game_root to print a friendly error and return None on failure."""
    try:
        return find_game_root(args.game_root)
    except FileNotFoundError as e:
        log.error("%s", e)
        return None


def _resolve_ui_lang(args) -> str:
    if args.ui_lang != "auto":
        return args.ui_lang
    return ui_lang_for(args.lang)


def cmd_report(args: argparse.Namespace) -> int:
    game_root = _resolve_game_root(args)
    if game_root is None:
        return 2
    game = load(game_root, args.lang)
    ui_lang = _resolve_ui_lang(args)
    ui = get_ui("simp_chinese" if ui_lang == "zh" else "english")
    rows = list(build_rows(game, ui))
    construction_rows = list(build_construction_rows(game, ui))
    out: Path = args.out if args.out else Path(
        f"report_buildings_v{game.raw_version or 'unknown'}.xlsx"
    )
    if not out.is_absolute():
        out = DEFAULT_BUILDINGS_REPORTS_DIR / out
    out.parent.mkdir(parents=True, exist_ok=True)

    meta = ReportMeta(
        game_version=game.version,
        raw_version=game.raw_version,
        tool_version=__version__,
        generated_at=datetime.now().isoformat(timespec="seconds"),
        data_lang=args.lang,
        ui_lang=ui_lang,
        counts={
            "goods": len(game.goods),
            "pops": len(game.pops),
            "pms": len(game.pms),
            "pmgs": len(game.pmgs),
            "buildings": len(game.buildings),
            "bgs": len(game.building_groups),
            "combo_rows": len(rows),
            "construction_rows": len(construction_rows),
        },
    )

    fmt = args.format
    if fmt in ("xlsx", "both"):
        xpath = out if out.suffix.lower() == ".xlsx" else out.with_suffix(".xlsx")
        write_xlsx(rows, construction_rows, xpath, meta=meta, ui=ui)
        log.info("Wrote %d combo rows + %d construction rows (V3 %s, data=%s, ui=%s) -> %s",
                 len(rows), len(construction_rows), game.version or "?",
                 args.lang, ui_lang, xpath)
    if fmt in ("csv", "both"):
        cpath = out if out.suffix.lower() == ".csv" else out.with_suffix(".csv")
        n = write_csv(rows, cpath, ui=ui)
        log.info("Wrote %d rows -> %s", n, cpath)
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    game_root = _resolve_game_root(args)
    if game_root is None:
        return 2
    game = load(game_root, args.lang)
    failures: list[str] = []

    pm = game.pms.get("pm_simple_farming")
    if pm is None:
        failures.append("pm_simple_farming missing")
    else:
        if pm.outputs.get("grain") != 20:
            failures.append(f"pm_simple_farming.outputs.grain expected 20, got {pm.outputs}")
        if pm.employment.get("laborers") != 4000 or pm.employment.get("farmers") != 1000:
            failures.append(f"pm_simple_farming employment unexpected: {pm.employment}")

    b = game.buildings.get("building_rye_farm")
    if b is None:
        failures.append("building_rye_farm missing")
    else:
        if b.required_construction != "construction_cost_low":
            failures.append(f"building_rye_farm required_construction unexpected: {b.required_construction}")

    grain = game.goods.get("grain")
    if grain is None or grain.cost != 20:
        failures.append(f"grain price unexpected: {grain}")

    cc = game.construction_costs
    expected = {
        "construction_cost_very_low": 100,
        "construction_cost_low": 200,
        "construction_cost_medium": 400,
        "construction_cost_high": 600,
        "construction_cost_very_high": 800,
    }
    for k, v in expected.items():
        if cc.get(k) != v:
            failures.append(f"{k} expected {v}, got {cc.get(k)}")

    if game.loc is not None:
        food = game.loc.get_clean("building_food_industry")
        if food == "building_food_industry":
            failures.append("Localization for building_food_industry not loaded")
        else:
            log.info("Loc check: building_food_industry -> %s", food)

    # Annualized per-capita formula: weekly profit × 52 / employment.
    # rye_farm × pm_simple_farming: profit 400 / week, employment 5000 →
    # 人均年产值 = 400 × 52 / 5000 = 4.16
    from .analysis import metrics as _m
    pc = _m.per_capita(400.0, 5000)
    if pc is None or abs(pc - 4.16) > 1e-6:
        failures.append(f"per_capita annualization mismatch: expected 4.16, got {pc}")

    if failures:
        for f in failures:
            log.error("FAIL: %s", f)
        return 1
    log.info("All smoke checks passed.")
    return 0


def _resolve_input_path(p: Path, *bases: Path) -> Path:
    """Resolve a CLI-supplied input path. Tries (in order):
    1. The literal path (absolute or relative to cwd)
    2. Each `<base>/<p>` in `bases` order
    3. Legacy `out/reports/<p>` and `out/<p>` (always tried last for back-compat)

    Returns the first hit, or the literal path if nothing exists.
    """
    if p.is_absolute() or p.exists():
        return p
    for base in (*bases, DEFAULT_BASELINES_DIR, _LEGACY_REPORTS_DIR, DEFAULT_OUT_DIR):
        candidate = base / p
        if candidate.exists():
            return candidate
    return p


def cmd_diff(args: argparse.Namespace) -> int:
    bases = (DEFAULT_BUILDINGS_REPORTS_DIR,)
    old_path = _resolve_input_path(args.old, *bases)
    new_path = _resolve_input_path(args.new, *bases)
    if not old_path.exists():
        log.error("Old report not found: %s (also checked %s)",
                  args.old, DEFAULT_BUILDINGS_REPORTS_DIR / args.old)
        return 2
    if not new_path.exists():
        log.error("New report not found: %s (also checked %s)",
                  args.new, DEFAULT_BUILDINGS_REPORTS_DIR / args.new)
        return 2
    log.info("Reading old: %s", old_path)
    old = read_report(old_path)
    log.info("Reading new: %s", new_path)
    new = read_report(new_path)

    def _meta_lookup(meta: dict, *keys: str) -> str:
        for k in keys:
            if k in meta:
                return meta[k]
        return "?"
    old_ver = _meta_lookup(old.meta, "数据版本", "Raw Version")
    new_ver = _meta_lookup(new.meta, "数据版本", "Raw Version")
    log.info(
        "Old: V3 %s | New: V3 %s",
        _meta_lookup(old.meta, "游戏版本", "Game Version"),
        _meta_lookup(new.meta, "游戏版本", "Game Version"),
    )
    diff = diff_snapshots(old, new, eps_abs=args.eps_abs, eps_rel=args.eps_rel)
    log.info(
        "Combo: +%d / -%d / Δ%d ; Construction: +%d / -%d / Δ%d",
        len(diff.combo_added), len(diff.combo_removed), len(diff.combo_changed),
        len(diff.construction_added), len(diff.construction_removed), len(diff.construction_changed),
    )
    out: Path = args.out if args.out else Path(
        f"diff_buildings_v{old_ver}_to_v{new_ver}.xlsx"
    )
    if not out.is_absolute():
        out = DEFAULT_BUILDINGS_DIFFS_DIR / out
    out.parent.mkdir(parents=True, exist_ok=True)
    ui_lang = _resolve_ui_lang(args)
    ui = get_ui("simp_chinese" if ui_lang == "zh" else "english")
    write_diff_xlsx(diff, out, ui=ui)
    log.info("Wrote diff (ui=%s) -> %s", ui_lang, out)
    return 0


def cmd_regions_report(args: argparse.Namespace) -> int:
    game_root = _resolve_game_root(args)
    if game_root is None:
        return 2
    game = load(game_root, args.lang)
    ui_lang = _resolve_ui_lang(args)
    ui = get_ui("simp_chinese" if ui_lang == "zh" else "english")
    rows = list(build_region_rows(game, ui))
    out: Path = args.out if args.out else Path(
        f"report_regions_v{game.raw_version or 'unknown'}.xlsx"
    )
    if not out.is_absolute():
        out = DEFAULT_REGIONS_REPORTS_DIR / out
    out.parent.mkdir(parents=True, exist_ok=True)

    meta = ReportMeta(
        game_version=game.version,
        raw_version=game.raw_version,
        tool_version=__version__,
        generated_at=datetime.now().isoformat(timespec="seconds"),
        data_lang=args.lang,
        ui_lang=ui_lang,
        counts={
            "states": sum(1 for s in game.state_regions.values() if not s.is_sea),
            "state_traits": len(game.state_traits),
            "strategic_regions": len(game.strategic_regions),
        },
    )
    n = write_regions_xlsx(rows, out, meta=meta, ui=ui, game=game)
    log.info("Wrote %d region rows (V3 %s, data=%s, ui=%s) -> %s",
             n, game.version or "?", args.lang, ui_lang, out)
    return 0


def cmd_regions_diff(args: argparse.Namespace) -> int:
    bases = (DEFAULT_REGIONS_REPORTS_DIR,)
    old_path = _resolve_input_path(args.old, *bases)
    new_path = _resolve_input_path(args.new, *bases)
    if not old_path.exists():
        log.error("Old regions report not found: %s (also checked %s)",
                  args.old, DEFAULT_REGIONS_REPORTS_DIR / args.old)
        return 2
    if not new_path.exists():
        log.error("New regions report not found: %s (also checked %s)",
                  args.new, DEFAULT_REGIONS_REPORTS_DIR / args.new)
        return 2
    log.info("Reading old regions report: %s", old_path)
    old = read_regions_report(old_path)
    log.info("Reading new regions report: %s", new_path)
    new = read_regions_report(new_path)

    def _meta_lookup(meta: dict, *keys: str) -> str:
        for k in keys:
            if k in meta:
                return meta[k]
        return "?"
    old_ver = _meta_lookup(old.meta, "数据版本", "Raw Version")
    new_ver = _meta_lookup(new.meta, "数据版本", "Raw Version")

    diff = diff_regions_snapshots(old, new, eps_abs=args.eps_abs, eps_rel=args.eps_rel)
    log.info("Regions: +%d / -%d / Δ%d",
             len(diff.added), len(diff.removed), len(diff.changed))
    out: Path = args.out if args.out else Path(
        f"diff_regions_v{old_ver}_to_v{new_ver}.xlsx"
    )
    if not out.is_absolute():
        out = DEFAULT_REGIONS_DIFFS_DIR / out
    out.parent.mkdir(parents=True, exist_ok=True)
    ui_lang = _resolve_ui_lang(args)
    ui = get_ui("simp_chinese" if ui_lang == "zh" else "english")
    write_regions_diff_xlsx(diff, out, ui=ui)
    log.info("Wrote regions diff (ui=%s) -> %s", ui_lang, out)
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    """Manage the cached game-root path (`<V3_EMA>/.game_root`)."""
    if args.show:
        cached = load_cached()
        if cached is not None:
            print(f"Cached game root: {cached}")
        else:
            print("No cached game root.")
        # Also probe the full resolution chain for diagnostic purposes.
        try:
            resolved = find_game_root(None)
            print(f"Currently resolves to: {resolved}")
        except FileNotFoundError as e:
            print(f"Auto-resolution would fail:\n{e}")
        return 0
    if args.clear:
        cleared = clear_cached()
        print("Cleared cache." if cleared else "No cache to clear.")
        return 0
    if args.game_root is not None:
        p = Path(args.game_root).resolve()
        if not is_valid_game_root(p):
            log.error("Not a valid V3 install: %s", p)
            log.error("Expected `launcher/launcher-settings.json` and "
                      "`game/common/production_methods/` under that path.")
            return 2
        save_cached(p)
        print(f"Saved game root to cache: {p}")
        return 0
    log.error("Specify one of: --game-root <path>, --show, --clear")
    return 2


def cmd_dump_pm(args: argparse.Namespace) -> int:
    game_root = _resolve_game_root(args)
    if game_root is None:
        return 2
    game = load(game_root, args.lang)
    pm = game.pms.get(args.pm_id)
    if pm is None:
        log.error("PM not found: %s", args.pm_id)
        return 2
    print(f"id      : {pm.id}")
    if game.loc is not None:
        print(f"name    : {game.loc.get_clean(pm.id)}")
    print(f"inputs  : {pm.inputs}")
    print(f"outputs : {pm.outputs}")
    print(f"employs : {pm.employment}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="v3-ema", description="V3_EMA — Victoria 3 Econometrics Automation")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    p_report = sub.add_parser("report", help="Generate xlsx/csv report")
    _add_common_args(p_report)
    p_report.add_argument("--out", type=Path, default=None,
                          help="Output filename. Default: report_buildings_v<version>.xlsx")
    p_report.add_argument("--format", choices=["xlsx", "csv", "both"], default="xlsx")
    p_report.set_defaults(func=cmd_report)

    p_verify = sub.add_parser("verify", help="Run smoke checks against the live game files")
    _add_common_args(p_verify)
    p_verify.set_defaults(func=cmd_verify)

    p_dump = sub.add_parser("dump-pm", help="Dump a single parsed PM (debug)")
    _add_common_args(p_dump)
    p_dump.add_argument("pm_id")
    p_dump.set_defaults(func=cmd_dump_pm)

    p_config = sub.add_parser(
        "config",
        help="Set / show / clear the cached Victoria 3 install path",
    )
    g = p_config.add_mutually_exclusive_group(required=True)
    g.add_argument("--game-root", type=Path,
                   help="Save this path to the cache for future runs")
    g.add_argument("--show", action="store_true",
                   help="Print the cached path and the currently resolved one")
    g.add_argument("--clear", action="store_true",
                   help="Delete the cached path; next run re-detects from scratch")
    p_config.set_defaults(func=cmd_config)

    p_diff = sub.add_parser("diff", help="Compare two V3_EMA xlsx reports across versions")
    p_diff.add_argument("old", type=Path, help="Older xlsx report path")
    p_diff.add_argument("new", type=Path, help="Newer xlsx report path")
    p_diff.add_argument("--out", type=Path, default=None,
                        help="Output filename. Default: diff_buildings_v<old>_to_v<new>.xlsx")
    p_diff.add_argument("--lang", default="simp_chinese",
                        help="(unused for diff itself; only affects UI lang inference)")
    p_diff.add_argument("--ui-lang", choices=["zh", "en", "auto"], default="auto",
                        help="UI language for the diff workbook (default auto)")
    p_diff.add_argument("--eps-abs", type=float, default=0.01,
                        help="Absolute epsilon below which numeric changes are ignored")
    p_diff.add_argument("--eps-rel", type=float, default=0.005,
                        help="Relative epsilon (fraction) below which numeric changes are ignored")
    p_diff.set_defaults(func=cmd_diff)

    # ---- regions namespace (nested subcommands) ----
    p_regions = sub.add_parser("regions", help="State-region resource analysis")
    regions_sub = p_regions.add_subparsers(dest="regions_cmd", required=True)

    p_rr = regions_sub.add_parser("report", help="Generate regions report xlsx")
    _add_common_args(p_rr)
    p_rr.add_argument("--out", type=Path, default=None,
                      help="Output filename. Default: report_regions_v<version>.xlsx")
    p_rr.set_defaults(func=cmd_regions_report)

    p_rd = regions_sub.add_parser("diff", help="Compare two regions reports")
    p_rd.add_argument("old", type=Path)
    p_rd.add_argument("new", type=Path)
    p_rd.add_argument("--out", type=Path, default=None,
                      help="Output filename. Default: diff_regions_v<old>_to_v<new>.xlsx")
    p_rd.add_argument("--lang", default="simp_chinese",
                      help="(unused for diff itself; affects UI lang inference)")
    p_rd.add_argument("--ui-lang", choices=["zh", "en", "auto"], default="auto")
    p_rd.add_argument("--eps-abs", type=float, default=0.01)
    p_rd.add_argument("--eps-rel", type=float, default=0.005)
    p_rd.set_defaults(func=cmd_regions_diff)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

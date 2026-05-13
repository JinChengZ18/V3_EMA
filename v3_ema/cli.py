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
from .demography.constants import PopGrowthConstants
from .demography.game_modifiers import (
    build_scenarios_from_game,
    build_sensitivity_scenarios_from_game,
)
from .demography.model import pollution_impact_from_generation, simulate_pollution
from .demography.modifier_scan import scan_modifier_sources, summarize_sources
from .demography.report import build_analysis_report, build_html_report
from .demography.rows import (
    make_grouped_rates_rows,
    make_projection_rows,
    make_rates_rows,
    make_workforce_sensitivity_rows,
    write_csv as write_demography_csv,
)
from .demography.scenarios import (
    NET_SENSITIVITY_GROUP_KEYS,
    default_scenarios,
    workforce_sensitivity_scenarios,
)
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
DEFAULT_DEMOGRAPHY_DIR = DEFAULT_OUT_DIR / "demography"
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


def _demography_languages(args: argparse.Namespace) -> list[str]:
    """Resolve the list of UI languages to emit demography HTML for."""
    if args.ui_lang == "both":
        return ["en", "zh"]
    if args.ui_lang == "auto":
        return [_resolve_ui_lang(args)]
    return [args.ui_lang]


def cmd_demography_report(args: argparse.Namespace) -> int:
    """Population-growth and workforce-ratio analysis report (HTML + CSV)."""
    game_root = _resolve_game_root(args)
    if game_root is None:
        return 2

    if (args.sol_start is None) != (args.sol_end is None):
        log.error("--sol-start and --sol-end must be provided together.")
        return 2

    out_dir: Path = args.out if args.out else DEFAULT_DEMOGRAPHY_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    constants = PopGrowthConstants.from_game_root(game_root)
    if args.scenarios_from == "game":
        scenarios = build_scenarios_from_game(game_root, constants)
        sensitivity_groups_all = build_sensitivity_scenarios_from_game(game_root, constants)
    else:
        scenarios = default_scenarios(constants)
        sensitivity_groups_all = workforce_sensitivity_scenarios(constants)
    growth_sensitivity_groups = {
        key: sensitivity_groups_all[key] for key in NET_SENSITIVITY_GROUP_KEYS
    }
    rates_rows = make_rates_rows(scenarios, constants, args.sol_min, args.sol_max)
    growth_sensitivity_rows = make_grouped_rates_rows(
        growth_sensitivity_groups, constants, args.sol_min, args.sol_max
    )
    projection_initial_ratio = (
        args.initial_workforce_ratio
        if args.initial_workforce_ratio is not None
        else constants.working_adult_ratio_base
    )
    projection_target_ratio = (
        args.projection_target
        if args.projection_target is not None
        else constants.working_adult_ratio_base + 0.25
    )
    use_skew = not args.no_skew
    sol_trajectory = None
    if args.sol_start is not None:
        start = args.sol_start
        end = args.sol_end
        duration_years = max(args.months / 12.0, 1e-9)

        def sol_trajectory(year: float, _s=start, _e=end, _d=duration_years) -> float:
            t = min(max(year / _d, 0.0), 1.0)
            return _s + (_e - _s) * t

    projection_rows = make_projection_rows(
        scenarios,
        constants,
        sol=args.projection_sol,
        months=args.months,
        population=args.population,
        initial_workforce_ratio=projection_initial_ratio,
        target_workforce_ratio=projection_target_ratio,
        sol_trajectory=sol_trajectory,
        use_skew=use_skew,
    )
    sensitivity_rows = make_workforce_sensitivity_rows(
        sensitivity_groups_all,
        constants,
        sol=args.projection_sol,
        months=args.months,
        population=args.population,
        initial_workforce_ratio=projection_initial_ratio,
        default_target_workforce_ratio=projection_target_ratio,
        sol_trajectory=sol_trajectory,
        use_skew=use_skew,
    )

    if args.skip_modifier_scan:
        source_rows: list[dict[str, object]] = []
        source_summary: list[dict[str, str | float | int]] = []
    else:
        sources = scan_modifier_sources(game_root)
        source_rows = [
            {
                "key": source.key,
                "value": source.value,
                "file": source.file,
                "line_number": source.line_number,
                "scope": source.scope,
                "line": source.line,
            }
            for source in sources
        ]
        source_summary = summarize_sources(sources)

    written: list[Path] = []

    if not args.no_csv:
        write_demography_csv(out_dir / "rates_by_sol.csv", rates_rows)
        write_demography_csv(out_dir / "net_growth_sensitivity.csv", growth_sensitivity_rows)
        write_demography_csv(out_dir / "workforce_projection.csv", projection_rows)
        write_demography_csv(out_dir / "workforce_sensitivity.csv", sensitivity_rows)
        written += [
            out_dir / "rates_by_sol.csv",
            out_dir / "net_growth_sensitivity.csv",
            out_dir / "workforce_projection.csv",
            out_dir / "workforce_sensitivity.csv",
        ]
        if not args.skip_modifier_scan:
            write_demography_csv(out_dir / "modifier_sources.csv", source_rows)
            write_demography_csv(out_dir / "modifier_source_summary.csv", source_summary)
            written += [out_dir / "modifier_sources.csv", out_dir / "modifier_source_summary.csv"]

    # Pollution example tables — needed by both CSV output and HTML, so build
    # them unconditionally.
    pollution_examples: list[dict[str, object]] = []
    for generated in (0, 100, 250, 500, 1000, 2000, 5000):
        for arable in (20, 100, 300):
            pollution_examples.append(
                {
                    "generated_pollution": generated,
                    "arable_land": arable,
                    "pollution_impact": pollution_impact_from_generation(generated, arable, constants),
                }
            )
    dynamics_rows: list[dict[str, object]] = []
    if args.pollution_dynamics_months > 0:
        for generated, arable in (
            (500, 100),
            (1000, 100),
            (2000, 100),
            (5000, 100),
            (1000, 300),
        ):
            for row in simulate_pollution(
                float(generated),
                float(arable),
                constants,
                months=args.pollution_dynamics_months,
            ):
                dynamics_rows.append({"label": f"gen={generated}, arable={arable}", **row})

    if not args.no_csv:
        write_demography_csv(out_dir / "pollution_impact_examples.csv", pollution_examples)
        written.append(out_dir / "pollution_impact_examples.csv")
        if dynamics_rows:
            write_demography_csv(out_dir / "pollution_dynamics.csv", dynamics_rows)
            written.append(out_dir / "pollution_dynamics.csv")

    if not args.no_html:
        for language in _demography_languages(args):
            compact_report = build_html_report(
                game_root=game_root,
                constants=constants,
                scenarios=scenarios,
                rates_rows=rates_rows,
                projection_rows=projection_rows,
                growth_sensitivity_rows=growth_sensitivity_rows,
                sensitivity_rows=sensitivity_rows,
                source_summary=source_summary,
                pollution_examples=pollution_examples,
                pollution_dynamics_rows=dynamics_rows,
                projection_initial_ratio=projection_initial_ratio,
                projection_target_ratio=projection_target_ratio,
                projection_sol=args.projection_sol,
                language=language,
                compact=True,
            )
            analysis_report = build_analysis_report(
                game_root=game_root,
                constants=constants,
                scenarios=scenarios,
                rates_rows=rates_rows,
                projection_rows=projection_rows,
                growth_sensitivity_rows=growth_sensitivity_rows,
                sensitivity_rows=sensitivity_rows,
                source_summary=source_summary,
                pollution_examples=pollution_examples,
                projection_initial_ratio=projection_initial_ratio,
                projection_target_ratio=projection_target_ratio,
                projection_sol=args.projection_sol,
                language=language,
            )
            compact_path = out_dir / f"demography_report_{language}.html"
            analysis_path = out_dir / f"demography_analysis_report_{language}.html"
            compact_path.write_text(compact_report, encoding="utf-8")
            analysis_path.write_text(analysis_report, encoding="utf-8")
            written += [compact_path, analysis_path]

        duplicate_generic = out_dir / "demography_report.html"
        if duplicate_generic.exists():
            duplicate_generic.unlink()

    for path in written:
        log.info("Wrote %s", path)
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

    # ---- demography namespace (nested subcommands) ----
    p_demo = sub.add_parser(
        "demography",
        help="Pop-growth and workforce-ratio analysis (HTML reports + CSV data)",
    )
    demo_sub = p_demo.add_subparsers(dest="demo_cmd", required=True)

    p_dr = demo_sub.add_parser(
        "report",
        help="Build the HTML/CSV demography report under out/demography/",
    )
    p_dr.add_argument(
        "--game-root", type=Path, default=None,
        help="Victoria 3 install root (auto-detected by default; see `config`).",
    )
    p_dr.add_argument(
        "--lang", default="simp_chinese",
        help="(Game-data localization language; unused by the demography reader, "
             "only affects UI-language inference when --ui-lang=auto.)",
    )
    p_dr.add_argument(
        "--ui-lang", choices=["zh", "en", "both", "auto"], default="both",
        help="HTML report language. 'both' (default) emits both en and zh "
             "compact + analysis HTMLs.",
    )
    p_dr.add_argument(
        "--out", type=Path, default=None,
        help=f"Output directory. Default: {DEFAULT_DEMOGRAPHY_DIR}",
    )
    p_dr.add_argument("--sol-min", type=int, default=0, help="Minimum SoL to plot.")
    p_dr.add_argument("--sol-max", type=int, default=35, help="Maximum SoL to plot.")
    p_dr.add_argument("--months", type=int, default=1200,
                      help="Months for workforce-ratio projection (default 1200 = 100 years).")
    p_dr.add_argument("--projection-sol", type=float, default=15.0,
                      help="SoL used for workforce-ratio projection (default 15).")
    p_dr.add_argument("--initial-workforce-ratio", type=float, default=None,
                      help="Initial workforce ratio. Default: WORKING_ADULT_RATIO_BASE from defines.")
    p_dr.add_argument("--projection-target", type=float, default=None,
                      help="Target workforce ratio. Default: base + 0.25 (suffrage + trade unions).")
    p_dr.add_argument("--population", type=float, default=1_000_000.0,
                      help="Initial population for projection (default 1e6).")
    p_dr.add_argument("--no-skew", action="store_true",
                      help="Disable WORKING_ADULT_RATIO_SKEW_MAXIMUM mortality skew (legacy uniform model).")
    p_dr.add_argument("--sol-start", type=float, default=None,
                      help="Starting SoL for a linear-trajectory projection (requires --sol-end).")
    p_dr.add_argument("--sol-end", type=float, default=None,
                      help="Ending SoL for a linear-trajectory projection (requires --sol-start).")
    p_dr.add_argument("--pollution-dynamics-months", type=int, default=240,
                      help="Length of the transient pollution simulation (default 240; 0 to skip).")
    p_dr.add_argument("--skip-modifier-scan", action="store_true",
                      help="Skip the slow recursive scan of game/common/*.txt for modifier sources.")
    p_dr.add_argument("--bar-chart-top-n", type=int, default=12,
                      help="Number of bars in the modifier-frequency chart (default 12).")
    p_dr.add_argument("--scenarios-from", choices=("game", "hardcoded"), default="game",
                      help="Source for scenario modifier values (default: 'game' parses live).")
    p_dr.add_argument("--no-html", action="store_true", help="Skip HTML output (CSVs only).")
    p_dr.add_argument("--no-csv", action="store_true", help="Skip CSV output (HTMLs only).")
    p_dr.set_defaults(func=cmd_demography_report)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

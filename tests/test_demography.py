"""Tests for the v3_ema.demography package.

Runnable two ways:
    pytest tests/test_demography.py
    python tests/test_demography.py        (no pytest needed; plain asserts)
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from v3_ema.demography.constants import PopGrowthConstants
from v3_ema.demography.model import (
    Scenario,
    adjusted_rates,
    base_birth_rate,
    base_mortality,
    pollution_impact_from_generation,
    project_workforce_ratio,
    simulate_pollution,
    sol_to_wealth,
)
from v3_ema.demography.modifier_lookup import parse_modifier_block
from v3_ema.demography.modifier_scan import is_tracked_modifier_key
from v3_ema.demography.report import workforce_chart_bounds
from v3_ema.demography.scenarios import (
    default_scenarios,
    workforce_sensitivity_scenarios,
)
from v3_ema.demography.util import clamp, integer_percent_ticks, pct


# ---- Fixture text -----------------------------------------------------------

DEFINES_FIXTURE = """\
NPopulation = {
    @min_birthrate              = 0.00060
    @max_birthrate              = 0.00450
    @min_mortality              = 0.00045
    @max_mortality              = 0.00550
    @pop_growth_equilibrium_sol = 5
    @pop_growth_transition_sol  = 10
    @pop_growth_max_sol         = 15
    @pop_growth_stable_sol      = 25
    @transition_birthrate_mult  = 1
    @max_growth_mortality_mult  = 0.35

    WORKING_ADULT_RATIO_BASE             = 0.25
    WORKING_ADULT_RATIO_SKEW_MAXIMUM     = 2.0

    POLLUTION_TARGET_DIVISOR_BASE              = 50
    POLLUTION_TARGET_DIVISOR_ARABLE_LAND_MULT  = 1.5
    POLLUTION_CHANGE_SPEED                     = 0.255
    POLLUTION_MAX                              = 255
    POLLUTION_SPREAD_TO_NEIGHBOR               = 0.25
}
"""

LAWS_FIXTURE = """\
law_public_health = {
    institution = institution_health_system
    institution_modifier = {
        state_mortality_mult = -0.05
        state_pollution_reduction_health_mult = -0.15
        state_standard_of_living_add = 0.5
    }
}

law_charitable_health = {
    institution = institution_health_system
    institution_modifier = {
        state_mortality_mult = -0.03
        interest_group_ig_devout_pol_str_mult = 0.1
        state_pollution_reduction_health_mult = -0.1
        state_food_security_add = 0.02
    }
}
"""

STATIC_MOD_FIXTURE = """\
literacy_penalty = {
    icon = something.dds
    state_birth_rate_mult = -0.1
}

starvation_penalty = {
    state_birth_rate_mult = -0.7
    state_mortality_mult = 0.6
}

severe_starvation_penalty = {
    state_birth_rate_mult = -0.9
    state_mortality_mult = 1.0
}
"""


# ---- Constants --------------------------------------------------------------

def test_constants_parse_from_text() -> None:
    c = PopGrowthConstants.from_defines_text(DEFINES_FIXTURE)
    assert c.min_birthrate == 0.00060
    assert c.max_birthrate == 0.00450
    assert c.min_mortality == 0.00045
    assert c.max_mortality == 0.00550
    assert c.equilibrium_sol == 5.0
    assert c.transition_sol == 10.0
    assert c.growth_max_sol == 15.0
    assert c.stable_sol == 25.0
    assert c.working_adult_ratio_base == 0.25
    assert c.working_adult_ratio_skew_maximum == 2.0
    assert c.pollution_max == 255.0


def test_constants_use_defaults_when_missing() -> None:
    c = PopGrowthConstants.from_defines_text("")
    # All fields should fall back to the documented defaults.
    assert c.min_birthrate == 0.00060
    assert c.working_adult_ratio_base == 0.25


# ---- Base curves ------------------------------------------------------------

def _stock_constants() -> PopGrowthConstants:
    return PopGrowthConstants.from_defines_text(DEFINES_FIXTURE)


def test_base_birth_rate_endpoints() -> None:
    c = _stock_constants()
    assert base_birth_rate(0.0, c) == c.max_birthrate
    # SoL 10 = transition_sol: birth rate equals birthrate_at_transition.
    assert abs(base_birth_rate(10.0, c) - c.birthrate_at_transition) < 1e-12
    # SoL >= stable_sol clamps to min_birthrate.
    assert base_birth_rate(25.0, c) == c.min_birthrate
    assert base_birth_rate(40.0, c) == c.min_birthrate


def test_base_mortality_endpoints() -> None:
    c = _stock_constants()
    assert base_mortality(0.0, c) == c.max_mortality
    # SoL 5 = equilibrium_sol: mortality should equal birth rate at equilibrium.
    assert abs(base_mortality(5.0, c) - c.rate_at_equilibrium) < 1e-12
    assert base_mortality(25.0, c) == c.min_mortality
    assert base_mortality(40.0, c) == c.min_mortality


def test_base_mortality_is_continuous_at_growth_max() -> None:
    c = _stock_constants()
    # The piecewise function should join continuously at growth_max_sol.
    eps = 1e-6
    just_below = base_mortality(c.growth_max_sol - eps, c)
    just_above = base_mortality(c.growth_max_sol + eps, c)
    assert abs(just_below - just_above) < 1e-6


# ---- Pollution --------------------------------------------------------------

def test_pollution_impact_zero_when_no_generation() -> None:
    c = _stock_constants()
    assert pollution_impact_from_generation(0.0, 100.0, c) == 0.0


def test_pollution_impact_clamped_to_unity() -> None:
    c = _stock_constants()
    huge = pollution_impact_from_generation(10_000_000.0, 20.0, c)
    assert huge == 1.0


def test_pollution_impact_grows_with_generation() -> None:
    c = _stock_constants()
    low = pollution_impact_from_generation(100.0, 100.0, c)
    high = pollution_impact_from_generation(500.0, 100.0, c)
    assert 0.0 < low < high < 1.0


# ---- Adjusted rates ---------------------------------------------------------

def test_adjusted_rates_baseline_matches_base_curves() -> None:
    c = _stock_constants()
    base = Scenario("base")
    r = adjusted_rates(12.0, base, c)
    assert abs(r["birth_monthly"] - base_birth_rate(12.0, c)) < 1e-12
    assert abs(r["mortality_monthly"] - base_mortality(12.0, c)) < 1e-12
    assert r["net_annual"] == (r["birth_monthly"] - r["mortality_monthly"]) * 12.0


def test_adjusted_rates_literacy_lowers_birth_rate() -> None:
    c = _stock_constants()
    no_lit = adjusted_rates(15.0, Scenario("no"), c)
    full_lit = adjusted_rates(15.0, Scenario("full", literacy=1.0), c)
    assert full_lit["birth_monthly"] < no_lit["birth_monthly"]
    # At 100% literacy the birth multiplier channel should be exactly -0.10.
    assert abs(full_lit["literacy_birth_mult"] + 0.10) < 1e-12


def test_adjusted_rates_pollution_raises_mortality_and_lowers_effective_sol() -> None:
    c = _stock_constants()
    clean = adjusted_rates(12.0, Scenario("clean"), c)
    polluted = adjusted_rates(12.0, Scenario("polluted", pollution_impact=0.5), c)
    assert polluted["effective_sol"] < clean["effective_sol"]
    assert polluted["mortality_monthly"] > clean["mortality_monthly"]


# ---- Projection invariants --------------------------------------------------

def test_projection_initial_ratio_equals_target_holds_ratio() -> None:
    c = _stock_constants()
    s = Scenario(
        "stable",
        initial_workforce_ratio=0.4,
        target_workforce_ratio=0.4,
    )
    rows = project_workforce_ratio(s, c, sol=12.0, months=120, population=1_000_000.0)
    # Ratio should not drift when initial == target.
    for row in rows:
        assert abs(row["workforce_ratio"] - 0.4) < 1e-9


def test_projection_population_conserved_when_birth_equals_mortality() -> None:
    c = _stock_constants()
    # SoL 5 is the equilibrium point where birth == mortality on the base curve.
    s = Scenario("equilibrium")
    rows = project_workforce_ratio(s, c, sol=5.0, months=120, population=1_000_000.0)
    initial_pop = rows[0]["population"]
    final_pop = rows[-1]["population"]
    assert abs(final_pop - initial_pop) / initial_pop < 1e-6


def test_projection_ratio_moves_toward_target() -> None:
    c = _stock_constants()
    s = Scenario(
        "growing",
        initial_workforce_ratio=0.25,
        target_workforce_ratio=0.50,
    )
    rows = project_workforce_ratio(s, c, sol=12.0, months=1200, population=1_000_000.0)
    assert rows[0]["workforce_ratio"] == 0.25
    # After 100 years should be much closer to target than to initial.
    final_ratio = rows[-1]["workforce_ratio"]
    assert final_ratio > 0.40


# ---- Modifier scan ----------------------------------------------------------

def test_is_tracked_modifier_key() -> None:
    assert is_tracked_modifier_key("state_birth_rate_mult")
    assert is_tracked_modifier_key("state_mortality_mult")
    assert is_tracked_modifier_key("state_pollution_reduction_health_mult")
    # Generic *_mortality_mult / *_birth_rate_mult should also be tracked.
    assert is_tracked_modifier_key("building_steel_mills_mortality_mult")
    assert is_tracked_modifier_key("country_birth_rate_mult")
    assert not is_tracked_modifier_key("state_construction_mult")
    assert not is_tracked_modifier_key("random_other_key")


# ---- Modifier lookup --------------------------------------------------------

def test_parse_modifier_block_health_laws() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "laws.txt"
        p.write_text(LAWS_FIXTURE, encoding="utf-8")
        public = parse_modifier_block(p, "law_public_health")
        assert public is not None
        assert public["state_mortality_mult"] == -0.05
        assert public["state_pollution_reduction_health_mult"] == -0.15
        assert public["state_standard_of_living_add"] == 0.5

        charitable = parse_modifier_block(p, "law_charitable_health")
        assert charitable is not None
        assert charitable["state_mortality_mult"] == -0.03
        assert charitable["state_pollution_reduction_health_mult"] == -0.1
        assert charitable["state_food_security_add"] == 0.02


def test_parse_modifier_block_static_modifiers() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "static.txt"
        p.write_text(STATIC_MOD_FIXTURE, encoding="utf-8")
        sev = parse_modifier_block(p, "severe_starvation_penalty")
        assert sev == {"state_birth_rate_mult": -0.9, "state_mortality_mult": 1.0}
        lit = parse_modifier_block(p, "literacy_penalty")
        assert lit == {"state_birth_rate_mult": -0.1}


def test_parse_modifier_block_returns_none_for_missing() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.txt"
        p.write_text(LAWS_FIXTURE, encoding="utf-8")
        assert parse_modifier_block(p, "law_nonexistent") is None


def test_hardcoded_scenarios_match_game_lookup_fixture() -> None:
    """Drift guard: the hardcoded health and starvation scenarios should match
    what the modifier_lookup parses from the fixture text. If a future game
    patch shifts these values, the scenarios file needs an explicit update.
    """
    with tempfile.TemporaryDirectory() as td:
        laws_path = Path(td) / "laws.txt"
        laws_path.write_text(LAWS_FIXTURE, encoding="utf-8")
        static_path = Path(td) / "static.txt"
        static_path.write_text(STATIC_MOD_FIXTURE, encoding="utf-8")

        public = parse_modifier_block(laws_path, "law_public_health")
        charitable = parse_modifier_block(laws_path, "law_charitable_health")
        starv = parse_modifier_block(static_path, "starvation_penalty")
        severe = parse_modifier_block(static_path, "severe_starvation_penalty")

    c = _stock_constants()
    sens = workforce_sensitivity_scenarios(c)
    hc = {s.name: s for s in sens["healthcare"]}

    assert hc["Public health"].mortality_mult == public["state_mortality_mult"]
    assert hc["Public health"].pollution_health_reduction_mult == public["state_pollution_reduction_health_mult"]
    assert hc["Charitable health"].mortality_mult == charitable["state_mortality_mult"]
    assert hc["Charitable health"].pollution_health_reduction_mult == charitable["state_pollution_reduction_health_mult"]

    default = {s.name: s for s in default_scenarios(c)}
    assert default["Severe starvation"].birth_mult == severe["state_birth_rate_mult"]
    assert default["Severe starvation"].mortality_mult == severe["state_mortality_mult"]
    assert default["Starvation (partial)"].birth_mult == starv["state_birth_rate_mult"]
    assert default["Starvation (partial)"].mortality_mult == starv["state_mortality_mult"]


# ---- Util / report helpers --------------------------------------------------

def test_clamp() -> None:
    assert clamp(0.5, 0.0, 1.0) == 0.5
    assert clamp(-1.0, 0.0, 1.0) == 0.0
    assert clamp(2.0, 0.0, 1.0) == 1.0


def test_pct_rounds_near_zero() -> None:
    assert pct(0.000001, 2) == "0.00%"
    assert pct(0.123, 1) == "12.3%"


def test_integer_percent_ticks_spans_zero() -> None:
    ticks = integer_percent_ticks([-0.02, 0.05])
    assert 0.0 in ticks
    assert ticks == sorted(ticks)


def test_workforce_chart_bounds_default_matches_legacy() -> None:
    y_min, y_max, ticks = workforce_chart_bounds(0.25, 0.50)
    assert y_min == 0.25
    assert y_max == 0.50
    assert ticks == [0.25, 0.30, 0.35, 0.40, 0.45, 0.50]


def test_workforce_chart_bounds_expands_for_low_initial() -> None:
    y_min, y_max, _ = workforce_chart_bounds(0.15, 0.40)
    # 15% must be visible.
    assert y_min <= 0.15
    assert y_max >= 0.40


def test_workforce_chart_bounds_expands_for_high_target() -> None:
    y_min, y_max, _ = workforce_chart_bounds(0.25, 0.60)
    assert y_min <= 0.25
    assert y_max >= 0.60


# ---- Analysis report --------------------------------------------------------

def _build_minimal_analysis_inputs():
    from v3_ema.demography.rows import (
        make_grouped_rates_rows,
        make_projection_rows,
        make_rates_rows,
        make_workforce_sensitivity_rows,
    )
    from v3_ema.demography.scenarios import (
        default_scenarios,
        population_growth_sensitivity_scenarios,
        workforce_sensitivity_scenarios,
    )

    c = _stock_constants()
    scenarios = default_scenarios(c)
    rates = make_rates_rows(scenarios, c, 0, 35)
    growth_sens_groups = population_growth_sensitivity_scenarios(c)
    growth_sens = make_grouped_rates_rows(growth_sens_groups, c, 0, 35)
    proj = make_projection_rows(
        scenarios,
        c,
        sol=15.0,
        months=12,
        population=1_000_000.0,
        initial_workforce_ratio=0.25,
        target_workforce_ratio=0.50,
    )
    sens_groups = workforce_sensitivity_scenarios(c)
    sens = make_workforce_sensitivity_rows(
        sens_groups,
        c,
        sol=15.0,
        months=12,
        population=1_000_000.0,
        initial_workforce_ratio=0.25,
        default_target_workforce_ratio=0.50,
    )
    return c, rates, proj, growth_sens, sens


def test_build_analysis_report_emits_both_languages() -> None:
    from v3_ema.demography.report import build_analysis_report

    c, rates, proj, growth_sens, sens = _build_minimal_analysis_inputs()
    common_kwargs = dict(
        game_root=Path("/fake/root"),
        constants=c,
        rates_rows=rates,
        projection_rows=proj,
        growth_sensitivity_rows=growth_sens,
        sensitivity_rows=sens,
        source_summary=[],
        projection_initial_ratio=0.25,
        projection_target_ratio=0.50,
        projection_sol=15.0,
    )
    zh = build_analysis_report(**common_kwargs, language="zh")
    en = build_analysis_report(**common_kwargs, language="en")
    # Distinct outputs with topic-style section titles.
    assert "维多利亚 3" in zh and "人口与劳动力机制分析" in zh
    assert "Victoria 3" in en and "Population and Workforce Mechanics" in en
    # Topical section titles.
    assert "医疗法案的选择" in zh
    assert "Health-System Law" in en
    assert "通用食品公司" in zh
    assert "food company" in en.lower()
    assert "劳动力比例的提升路径" in zh
    assert "工业化的人口代价" in zh
    # Single merged document: model basis + sensitivity charts + modifier scan
    # + data dictionary all live inline as h2 sections.
    assert "<h2>模型基础与默认场景</h2>" in zh
    assert "<h2>Model Basis and Default Scenarios</h2>" in en
    assert "<h2>数据字典</h2>" in zh
    assert "<h2>Data Dictionary</h2>" in en
    # AI-flavored boxes should be gone.
    assert "TL;DR" not in en
    assert "速览" not in zh
    assert 'class="rec"' not in zh
    assert 'class="callout"' not in zh


# ---- M3/M4/M5/M6/M7/M8 new-behavior tests -----------------------------------

def test_starvation_partial_scenario_present() -> None:
    c = _stock_constants()
    names = [s.name for s in default_scenarios(c)]
    assert "Starvation (partial)" in names
    assert "Severe starvation" in names
    partial = next(s for s in default_scenarios(c) if s.name == "Starvation (partial)")
    assert partial.birth_mult == -0.70
    assert partial.mortality_mult == 0.60


def test_skew_pulls_workforce_ratio_toward_target_faster() -> None:
    c = _stock_constants()
    s = Scenario("ramp", initial_workforce_ratio=0.25, target_workforce_ratio=0.50)
    without_skew = project_workforce_ratio(s, c, sol=12.0, months=600, population=1_000_000.0, use_skew=False)
    with_skew = project_workforce_ratio(s, c, sol=12.0, months=600, population=1_000_000.0, use_skew=True)
    assert with_skew[-1]["workforce_ratio"] >= without_skew[-1]["workforce_ratio"]


def test_skew_does_not_break_initial_equals_target_invariant() -> None:
    c = _stock_constants()
    s = Scenario("flat", initial_workforce_ratio=0.4, target_workforce_ratio=0.4)
    rows = project_workforce_ratio(s, c, sol=12.0, months=120, population=1_000_000.0, use_skew=True)
    for row in rows:
        assert abs(row["workforce_ratio"] - 0.4) < 1e-9


def test_sol_trajectory_changes_birth_rate_over_time() -> None:
    c = _stock_constants()
    s = Scenario("traj", initial_workforce_ratio=0.25, target_workforce_ratio=0.5)
    # Linear: SoL rises from 5 to 20 across 120 months (10 years).
    rows = project_workforce_ratio(
        s, c, sol=5.0, months=120, population=1_000_000.0,
        sol_trajectory=lambda year: 5.0 + (20.0 - 5.0) * min(year / 10.0, 1.0),
    )
    # Birth rate must change because SoL changes — meaning the cached fast path
    # is bypassed when a trajectory is supplied.
    first_birth = rows[0]["birth_monthly"]
    last_birth = rows[-1]["birth_monthly"]
    assert first_birth != last_birth
    # At SoL 5 birth ≈ max_birthrate, at SoL 20 birth has fallen toward the
    # post-transition slope.
    assert last_birth < first_birth


def test_sol_to_wealth_monotonic_and_nonnegative() -> None:
    assert sol_to_wealth(0.0) >= 0.0
    assert sol_to_wealth(5.0) < sol_to_wealth(15.0) < sol_to_wealth(25.0)


def test_private_health_uses_mapped_wealth() -> None:
    c = _stock_constants()
    s = Scenario(
        "private",
        mortality_wealth_mult=-0.002,
        wealth_from_sol=True,
    )
    r = adjusted_rates(15.0, s, c)
    # Mapped wealth at SoL 15 is 22.5, not 15.0 (which would be the legacy proxy).
    assert abs(r["wealth_used"] - sol_to_wealth(15.0)) < 1e-12
    assert r["wealth_used"] != 15.0


def test_pollution_sol_penalty_scaled_by_reduction() -> None:
    c = _stock_constants()
    polluted = adjusted_rates(15.0, Scenario("dirty", pollution_impact=1.0), c)
    polluted_with_health = adjusted_rates(
        15.0,
        Scenario("dirty+health", pollution_impact=1.0, pollution_health_reduction_mult=-0.5),
        c,
    )
    # With reduction, effective_sol should drop less (so be higher).
    assert polluted_with_health["effective_sol"] > polluted["effective_sol"]
    # And mortality multiplier should also be reduced proportionally.
    assert polluted_with_health["pollution_mortality_mult"] < polluted["pollution_mortality_mult"]


def test_simulate_pollution_monotonic_toward_target() -> None:
    c = _stock_constants()
    rows = simulate_pollution(1000.0, 100.0, c, months=600)
    target = rows[0]["target_impact"]
    assert 0.0 < target <= 1.0
    # Pollution should never overshoot the target and should grow monotonically
    # when starting at 0 below target.
    for prev, curr in zip(rows, rows[1:]):
        assert curr["pollution_impact"] >= prev["pollution_impact"]
        assert curr["pollution_impact"] <= target + 1e-9
    # Default change_speed = 0.255 over pollution_max = 255 gives step 0.001/mo;
    # after 600 months the closed-form remainder is (1 - 0.001)^600 ≈ 0.549,
    # so impact should have crossed ~40% of target.
    final = rows[-1]["pollution_impact"]
    assert final >= target * 0.40


def test_simulate_pollution_zero_generation_stays_zero() -> None:
    c = _stock_constants()
    rows = simulate_pollution(0.0, 100.0, c, months=60)
    assert all(row["pollution_impact"] == 0.0 for row in rows)


def test_build_analysis_report_zh_back_compat_shim() -> None:
    from v3_ema.demography.report import build_analysis_report_zh

    c, rates, proj, growth_sens, sens = _build_minimal_analysis_inputs()
    out = build_analysis_report_zh(
        game_root=Path("/fake/root"),
        constants=c,
        rates_rows=rates,
        projection_rows=proj,
        growth_sensitivity_rows=growth_sens,
        sensitivity_rows=sens,
        source_summary=[],
        projection_initial_ratio=0.25,
        projection_target_ratio=0.50,
        projection_sol=15.0,
    )
    assert "维多利亚 3" in out


# ---- Self-runner ------------------------------------------------------------

def _collect_tests() -> list[tuple[str, callable]]:
    return [(name, obj) for name, obj in sorted(globals().items()) if name.startswith("test_") and callable(obj)]


def main() -> int:
    tests = _collect_tests()
    failures: list[tuple[str, str]] = []
    for name, fn in tests:
        try:
            fn()
            print(f"  ok  {name}")
        except AssertionError as e:
            failures.append((name, str(e) or "AssertionError"))
            print(f"  FAIL {name}: {e}")
        except Exception as e:  # noqa: BLE001
            failures.append((name, f"{type(e).__name__}: {e}"))
            print(f"  ERR  {name}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - len(failures)}/{len(tests)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

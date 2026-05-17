from __future__ import annotations

from .constants import PopGrowthConstants
from .model import Scenario


NET_OVERVIEW_EXCLUDE = {
    "Women's workplace",
    "Women's suffrage + food",
    "Women's suffrage + trade unions",
}

NET_SENSITIVITY_GROUP_KEYS = (
    "birth_multiplier",
    "mortality_multiplier",
    "literacy",
    "pollution",
    "healthcare",
    "healthcare_pollution",
)


def default_scenarios(constants: PopGrowthConstants) -> list[Scenario]:
    base = constants.working_adult_ratio_base
    return [
        Scenario("Base SoL curve", target_workforce_ratio=base, notes="No state modifiers."),
        Scenario(
            "Literacy 100%",
            literacy=1.0,
            target_workforce_ratio=base,
            notes="literacy_penalty: birth rate mult -10% at 100% literacy.",
        ),
        Scenario(
            "Food company prosperity",
            birth_mult=0.05,
            target_workforce_ratio=base,
            notes="Food company prosperity_modifier: state_birth_rate_mult = 0.05.",
        ),
        Scenario(
            "Women's workplace",
            birth_mult=-0.05,
            literacy=0.8,
            target_workforce_ratio=base + 0.10,
            notes="law_women_in_the_workplace: target workforce +10%, birth rate -5%; literacy set to 80%.",
        ),
        Scenario(
            "Women's suffrage + food",
            birth_mult=0.0,
            literacy=0.8,
            target_workforce_ratio=base + 0.15,
            notes="Women's suffrage -5% and food company +5% cancel before literacy penalty.",
        ),
        Scenario(
            "Women's suffrage + trade unions",
            birth_mult=-0.05,
            literacy=0.8,
            target_workforce_ratio=base + 0.25,
            notes="Women's suffrage +15% plus two trade-union trait bonuses at +5% each; birth rate -5%.",
        ),
        Scenario(
            "Pollution impact 50%",
            pollution_impact=0.50,
            target_workforce_ratio=base,
            notes="state_region_pollution_health scaled by 50% impact: SoL -1.5, mortality mult +25%.",
        ),
        Scenario(
            "Starvation (partial)",
            birth_mult=-0.70,
            mortality_mult=0.60,
            target_workforce_ratio=base,
            notes="starvation_penalty: state_birth_rate_mult=-0.7, state_mortality_mult=0.6 at full strength (engine scales by Starvation, capping near 50% strength so typical effect is ~-0.35/+0.30).",
        ),
        Scenario(
            "Severe starvation",
            birth_mult=-0.90,
            mortality_mult=1.00,
            target_workforce_ratio=base,
            notes="severe_starvation_penalty: birth -90%, mortality +100%.",
        ),
    ]


def workforce_sensitivity_scenarios(constants: PopGrowthConstants) -> dict[str, list[Scenario]]:
    base = constants.working_adult_ratio_base
    return {
        "birth_multiplier": [
            Scenario("Birth mult -10%", birth_mult=-0.10, target_workforce_ratio=base + 0.25),
            Scenario("Birth mult -5%", birth_mult=-0.05, target_workforce_ratio=base + 0.25),
            Scenario("Base", target_workforce_ratio=base + 0.25),
            Scenario("Birth mult +5%", birth_mult=0.05, target_workforce_ratio=base + 0.25),
            Scenario("Birth mult +10%", birth_mult=0.10, target_workforce_ratio=base + 0.25),
        ],
        "mortality_multiplier": [
            Scenario("Mortality mult -10%", mortality_mult=-0.10, target_workforce_ratio=base + 0.25),
            Scenario("Mortality mult -5%", mortality_mult=-0.05, target_workforce_ratio=base + 0.25),
            Scenario("Base", target_workforce_ratio=base + 0.25),
            Scenario("Mortality mult +5%", mortality_mult=0.05, target_workforce_ratio=base + 0.25),
            Scenario("Mortality mult +10%", mortality_mult=0.10, target_workforce_ratio=base + 0.25),
            Scenario("Mortality mult +50%", mortality_mult=0.50, target_workforce_ratio=base + 0.25),
        ],
        "literacy": [
            Scenario("Literacy 0%", literacy=0.00, target_workforce_ratio=base + 0.25),
            Scenario("Literacy 25%", literacy=0.25, target_workforce_ratio=base + 0.25),
            Scenario("Literacy 50%", literacy=0.50, target_workforce_ratio=base + 0.25),
            Scenario("Literacy 75%", literacy=0.75, target_workforce_ratio=base + 0.25),
            Scenario("Literacy 100%", literacy=1.00, target_workforce_ratio=base + 0.25),
        ],
        "pollution": [
            Scenario("Pollution 0%", pollution_impact=0.00, target_workforce_ratio=base + 0.25),
            Scenario("Pollution 25%", pollution_impact=0.25, target_workforce_ratio=base + 0.25),
            Scenario("Pollution 50%", pollution_impact=0.50, target_workforce_ratio=base + 0.25),
            Scenario("Pollution 75%", pollution_impact=0.75, target_workforce_ratio=base + 0.25),
            Scenario("Pollution 100%", pollution_impact=1.00, target_workforce_ratio=base + 0.25),
        ],
        "healthcare": [
            Scenario("No health system", target_workforce_ratio=base + 0.25),
            Scenario("Charitable health", mortality_mult=-0.03, pollution_health_reduction_mult=-0.10, target_workforce_ratio=base + 0.25),
            Scenario("Public health", mortality_mult=-0.05, pollution_health_reduction_mult=-0.15, sol_add=0.5, target_workforce_ratio=base + 0.25),
            Scenario("Private health (wealth from SoL)", mortality_wealth_mult=-0.002, wealth_from_sol=True, pollution_health_reduction_mult=-0.10, target_workforce_ratio=base + 0.25),
        ],
        "healthcare_pollution": [
            Scenario("No health + pollution 50%", pollution_impact=0.50, target_workforce_ratio=base + 0.25),
            Scenario("Charitable health + pollution 50%", mortality_mult=-0.03, pollution_impact=0.50, pollution_health_reduction_mult=-0.10, target_workforce_ratio=base + 0.25),
            Scenario("Public health + pollution 50%", mortality_mult=-0.05, pollution_impact=0.50, pollution_health_reduction_mult=-0.15, sol_add=0.5, target_workforce_ratio=base + 0.25),
            Scenario("Private health + pollution 50%", mortality_wealth_mult=-0.002, wealth_from_sol=True, pollution_impact=0.50, pollution_health_reduction_mult=-0.10, target_workforce_ratio=base + 0.25),
        ],
        "target_ratio": [
            Scenario("Target 25%", target_workforce_ratio=base),
            Scenario("Target 35%", target_workforce_ratio=base + 0.10),
            Scenario("Target 40%", target_workforce_ratio=base + 0.15),
            Scenario("Target 45%", target_workforce_ratio=base + 0.20),
            Scenario("Target 50%", target_workforce_ratio=base + 0.25),
        ],
        "sol": [
            Scenario("SoL 5", projection_sol=5.0, target_workforce_ratio=base + 0.25),
            Scenario("SoL 8", projection_sol=8.0, target_workforce_ratio=base + 0.25),
            Scenario("SoL 10", projection_sol=10.0, target_workforce_ratio=base + 0.25),
            Scenario("SoL 12", projection_sol=12.0, target_workforce_ratio=base + 0.25),
            Scenario("SoL 15", projection_sol=15.0, target_workforce_ratio=base + 0.25),
            Scenario("SoL 18", projection_sol=18.0, target_workforce_ratio=base + 0.25),
            Scenario("SoL 20", projection_sol=20.0, target_workforce_ratio=base + 0.25),
            Scenario("SoL 22", projection_sol=22.0, target_workforce_ratio=base + 0.25),
            Scenario("SoL 25", projection_sol=25.0, target_workforce_ratio=base + 0.25),
        ],
    }


def population_growth_sensitivity_scenarios(constants: PopGrowthConstants) -> dict[str, list[Scenario]]:
    groups = workforce_sensitivity_scenarios(constants)
    return {key: groups[key] for key in NET_SENSITIVITY_GROUP_KEYS}

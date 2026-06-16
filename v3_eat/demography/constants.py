from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .util import number_after


@dataclass(frozen=True)
class PopGrowthConstants:
    min_birthrate: float
    max_birthrate: float
    min_mortality: float
    max_mortality: float
    equilibrium_sol: float
    transition_sol: float
    growth_max_sol: float
    stable_sol: float
    transition_birthrate_mult: float
    max_growth_mortality_mult: float
    working_adult_ratio_base: float
    working_adult_ratio_skew_maximum: float
    pollution_target_divisor_base: float
    pollution_target_divisor_arable_land_mult: float
    pollution_change_speed: float
    pollution_max: float
    pollution_spread_to_neighbor: float

    @classmethod
    def from_game_root(cls, game_root: Path) -> "PopGrowthConstants":
        text = (game_root / "game" / "common" / "defines" / "00_defines.txt").read_text(
            encoding="utf-8-sig",
            errors="replace",
        )
        return cls.from_defines_text(text)

    @classmethod
    def from_defines_text(cls, text: str) -> "PopGrowthConstants":
        def at(name: str, default: float) -> float:
            return number_after(text, rf"@{re.escape(name)}\s*=", default)

        def define(name: str, default: float) -> float:
            return number_after(text, rf"\b{re.escape(name)}\s*=", default)

        return cls(
            min_birthrate=at("min_birthrate", 0.00060),
            max_birthrate=at("max_birthrate", 0.00450),
            min_mortality=at("min_mortality", 0.00045),
            max_mortality=at("max_mortality", 0.00550),
            equilibrium_sol=at("pop_growth_equilibrium_sol", 5.0),
            transition_sol=at("pop_growth_transition_sol", 10.0),
            growth_max_sol=at("pop_growth_max_sol", 15.0),
            stable_sol=at("pop_growth_stable_sol", 25.0),
            transition_birthrate_mult=at("transition_birthrate_mult", 1.0),
            max_growth_mortality_mult=at("max_growth_mortality_mult", 0.35),
            working_adult_ratio_base=define("WORKING_ADULT_RATIO_BASE", 0.25),
            working_adult_ratio_skew_maximum=define("WORKING_ADULT_RATIO_SKEW_MAXIMUM", 2.0),
            pollution_target_divisor_base=define("POLLUTION_TARGET_DIVISOR_BASE", 50.0),
            pollution_target_divisor_arable_land_mult=define("POLLUTION_TARGET_DIVISOR_ARABLE_LAND_MULT", 1.5),
            pollution_change_speed=define("POLLUTION_CHANGE_SPEED", 0.255),
            pollution_max=define("POLLUTION_MAX", 255.0),
            pollution_spread_to_neighbor=define("POLLUTION_SPREAD_TO_NEIGHBOR", 0.25),
        )

    @property
    def birthrate_at_transition(self) -> float:
        return self.max_birthrate * self.transition_birthrate_mult

    @property
    def rate_at_equilibrium(self) -> float:
        return (
            self.equilibrium_sol
            * ((self.birthrate_at_transition - self.max_birthrate) / self.transition_sol)
            + self.max_birthrate
        )

    @property
    def mortality_starving_slope(self) -> float:
        return (self.rate_at_equilibrium - self.max_mortality) / self.equilibrium_sol

    @property
    def birthrate_pretransition_slope(self) -> float:
        return (self.birthrate_at_transition - self.rate_at_equilibrium) / self.transition_sol

    @property
    def birthrate_at_growth_max(self) -> float:
        return (
            (self.growth_max_sol - self.transition_sol)
            * ((self.min_birthrate - self.birthrate_at_transition) / (self.stable_sol - self.transition_sol))
            + self.birthrate_at_transition
        )

    @property
    def mortality_at_growth_max(self) -> float:
        return self.birthrate_at_growth_max * self.max_growth_mortality_mult

    @property
    def mortality_equilibrium_to_growth_max_slope(self) -> float:
        return (self.mortality_at_growth_max - self.rate_at_equilibrium) / (
            self.growth_max_sol - self.equilibrium_sol
        )

    @property
    def mortality_equilibrium_to_growth_max_intercept(self) -> float:
        return -self.mortality_equilibrium_to_growth_max_slope * self.equilibrium_sol + self.rate_at_equilibrium

    @property
    def birthrate_transition_slope(self) -> float:
        return (self.min_birthrate - self.birthrate_at_transition) / (self.stable_sol - self.transition_sol)

    @property
    def birthrate_transition_intercept(self) -> float:
        return -self.birthrate_transition_slope * self.stable_sol + self.min_birthrate

    @property
    def mortality_growth_max_to_stable_slope(self) -> float:
        return (self.min_mortality - self.mortality_at_growth_max) / (self.stable_sol - self.growth_max_sol)

    @property
    def mortality_growth_max_to_stable_intercept(self) -> float:
        return -self.mortality_growth_max_to_stable_slope * self.stable_sol + self.min_mortality

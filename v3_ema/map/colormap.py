"""Colormaps for the resource choropleth, implemented with numpy (no matplotlib).

Two families:

1. **Named sequential maps** — viridis / magma / plasma / inferno (perceptual)
   and single-hue light→dark ramps (blues / greens / …). Sampled from the
   well-known matplotlib tables.

2. **Per-resource palettes** (`cmap=auto`, the default) — each resource gets a
   distinct, mnemonic hue (coal→charcoal, iron→steel-blue, sulfur→yellow,
   gold→amber, oil→aubergine, logging→forest-green, …) rendered as a light→dark
   ramp so "deeper = more", which is what the user asked for. Victoria 3's icon
   art is uniform sepia line-art, so it carries no usable per-resource color; the
   palette below is curated for distinctness + material mnemonics.

A "colormap" passed around the renderer is just an (N,3) float control-point
table; `colorize` interpolates it. `table_for` resolves the right table from the
`--cmap` argument plus the metric being drawn.
"""
from __future__ import annotations

import numpy as np

# fmt: off
_VIRIDIS = [
    (68, 1, 84), (72, 36, 117), (64, 67, 135), (52, 94, 141), (41, 120, 142),
    (32, 144, 140), (34, 167, 132), (68, 190, 112), (121, 209, 81),
    (189, 222, 38), (253, 231, 37),
]
_MAGMA = [
    (0, 0, 4), (24, 15, 62), (68, 15, 118), (114, 31, 129), (158, 47, 127),
    (205, 64, 113), (241, 96, 93), (253, 149, 103), (254, 201, 141),
    (253, 237, 176), (252, 253, 191),
]
_PLASMA = [
    (13, 8, 135), (62, 4, 156), (106, 0, 168), (143, 13, 164), (177, 42, 144),
    (203, 71, 119), (225, 100, 98), (242, 132, 75), (252, 166, 54),
    (252, 206, 37), (240, 249, 33),
]
_INFERNO = [
    (0, 0, 4), (22, 11, 57), (66, 10, 104), (106, 23, 110), (147, 38, 103),
    (188, 55, 84), (221, 81, 58), (243, 120, 25), (252, 165, 10),
    (246, 215, 70), (252, 255, 164),
]
_BLUES = [(247, 251, 255), (198, 219, 239), (107, 174, 214), (33, 113, 181), (8, 48, 107)]
_GREENS = [(247, 252, 245), (199, 233, 192), (116, 196, 118), (35, 139, 69), (0, 68, 27)]
_REDS = [(255, 245, 240), (252, 187, 161), (251, 106, 74), (203, 24, 29), (103, 0, 13)]
_ORANGES = [(255, 245, 235), (253, 208, 162), (253, 141, 60), (217, 72, 1), (127, 39, 4)]
_PURPLES = [(252, 251, 253), (218, 218, 235), (158, 154, 200), (106, 81, 163), (63, 0, 125)]
# Diverging red→white→green for the cross-version change map (red = decrease).
_DIVERGING = [(165, 0, 38), (215, 48, 39), (244, 165, 130), (247, 247, 247),
              (161, 215, 106), (49, 163, 84), (0, 104, 55)]
# fmt: on

_TABLES = {
    "viridis": _VIRIDIS, "magma": _MAGMA, "plasma": _PLASMA, "inferno": _INFERNO,
    "blues": _BLUES, "greens": _GREENS, "reds": _REDS, "oranges": _ORANGES,
    "purples": _PURPLES, "diverging": _DIVERGING,
}

NAMES = ["auto", "viridis", "magma", "plasma", "inferno",
         "blues", "greens", "reds", "oranges", "purples"]
DEFAULT = "auto"

# Curated per-resource dark endpoints (canonical building ids; gold_field folds
# into gold_mine — see metrics.RESOURCE_ALIASES). Each becomes a light→dark ramp.
RESOURCE_DARK: dict[str, tuple[int, int, int]] = {
    "building_coal_mine":         (38, 38, 38),     # coal — charcoal black
    "building_iron_mine":         (54, 92, 130),    # iron — steel blue
    "building_lead_mine":         (96, 88, 120),    # lead — slate purple-gray
    "building_sulfur_mine":       (196, 164, 22),   # sulfur — yellow
    "building_gold_mine":         (184, 128, 20),   # gold — amber (merged)
    "building_oil_rig":           (74, 52, 100),    # oil — aubergine purple
    "building_logging_camp":      (30, 110, 56),    # logging — forest green
    "building_rubber_plantation": (132, 142, 36),   # rubber — olive / lime
    "building_fishing_wharf":     (16, 138, 158),   # fishing — teal / cyan
    "building_whaling_station":   (28, 56, 120),    # whaling — deep navy
}

# Curated per-crop dark endpoints (arable_resources building ids). Distinct,
# mnemonic hues for the crop-distribution maps.
CROP_DARK: dict[str, tuple[int, int, int]] = {
    "building_wheat_farm":        (201, 162, 39),    # wheat — golden
    "building_rye_farm":          (168, 132, 47),    # rye — tan brown
    "building_rice_farm":         (58, 143, 90),     # rice — paddy green
    "building_maize_farm":        (214, 169, 47),    # maize — amber yellow
    "building_millet_farm":       (176, 154, 58),    # millet — khaki
    "building_livestock_ranch":   (156, 90, 60),     # livestock — russet
    "building_vineyard":          (125, 58, 92),     # vineyard — wine
    "building_cotton_plantation": (150, 140, 120),   # cotton — warm grey-tan
    "building_tobacco_plantation":(122, 90, 46),     # tobacco — brown
    "building_sugar_plantation":  (134, 179, 74),    # sugar — light green
    "building_banana_plantation": (168, 184, 50),    # banana — yellow-green
    "building_dye_plantation":    (74, 74, 138),     # dye — indigo
    "building_silk_plantation":   (154, 111, 154),   # silk — mauve
    "building_coffee_plantation": (90, 58, 38),      # coffee — dark brown
    "building_tea_plantation":    (90, 138, 58),     # tea — leaf green
    "building_opium_plantation":  (168, 58, 74),     # opium — poppy red
}

# Default named map for each aggregate metric when cmap=auto.
AGG_CMAP: dict[str, str] = {
    "arable_land": "greens",
    "total_capacity": "viridis",
    "capped_total": "viridis",
    "resource_kinds": "plasma",
}


def ramp_for_dark(dark: tuple[int, int, int]) -> list[list[float]]:
    """A light→dark single-hue ramp (4 stops) from a dark endpoint color.

    Tuned for strong depth contrast: the low end is already a saturated tint
    (not near-white) and the high end is pushed darker, so small differences in
    amount read clearly. Pair with the render-time gamma for low/mid spread.
    """
    d = np.asarray(dark, dtype=np.float64)
    white = np.array([255.0, 255.0, 255.0])
    c1 = white * 0.82 + d * 0.18
    c2 = white * 0.52 + d * 0.48
    c3 = white * 0.22 + d * 0.78
    c4 = d * 0.90
    return [c1.tolist(), c2.tolist(), c3.tolist(), c4.tolist()]


def as_table(spec) -> np.ndarray:
    """Resolve a colormap spec (name str, or (N,3) list/array) to a float table."""
    if isinstance(spec, str):
        return np.asarray(_TABLES.get(spec, _VIRIDIS), dtype=np.float64)
    return np.asarray(spec, dtype=np.float64)


def table_for(cmap_arg: str, metric_key: str, is_resource: bool, is_crop: bool = False) -> np.ndarray:
    """Pick the control-point table for a metric given the --cmap argument."""
    if cmap_arg and cmap_arg not in ("auto", "resource"):
        return as_table(cmap_arg)
    if is_crop:
        dark = CROP_DARK.get(metric_key)
        return as_table(ramp_for_dark(dark if dark is not None else (90, 140, 60)))
    if is_resource:
        dark = RESOURCE_DARK.get(metric_key)
        if dark is not None:
            return as_table(ramp_for_dark(dark))
        return as_table("viridis")
    return as_table(AGG_CMAP.get(metric_key, "viridis"))


def colorize(t: np.ndarray, spec, reverse: bool = False) -> np.ndarray:
    """Map normalized values t∈[0,1] (any shape) to RGB uint8 (shape + (3,))."""
    cps = as_table(spec)
    if reverse:
        cps = cps[::-1]
    n = len(cps)
    t = np.nan_to_num(np.clip(np.asarray(t, dtype=np.float64), 0.0, 1.0))
    pos = t * (n - 1)
    lo = np.floor(pos).astype(np.intp)
    hi = np.minimum(lo + 1, n - 1)
    frac = (pos - lo)[..., None]
    out = cps[lo] * (1.0 - frac) + cps[hi] * frac
    return np.rint(out).astype(np.uint8)


def sample_swatches(spec, k: int, reverse: bool = False) -> list[tuple[int, int, int]]:
    t = np.linspace(0.0, 1.0, max(k, 2))
    rgb = colorize(t, spec, reverse)
    return [tuple(int(c) for c in row) for row in rgb]

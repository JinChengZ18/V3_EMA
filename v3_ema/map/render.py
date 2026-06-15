"""Choropleth renderer: recolor game/map_data/provinces.png by per-state value.

Standard Paradox "indexed province color -> lookup-table recolor": every
province is a unique flat RGB color in provinces.png, so we build a 2**24-entry
LUT mapping each color to an output color, then index the whole image through it
in one vectorized numpy op. ProvinceIndex loads + downscales the bitmap once and
also precomputes per-state label anchors, so it's reused across every metric.
"""
from __future__ import annotations

import base64
import io
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ..model import GameData
from ..util.logging import get_logger
from . import colormap as cm
from .metrics import Metric

log = get_logger()

# Output palette for non-data pixels.
WATER = (176, 206, 230)        # seas, lakes, sea-states
LAND_NODATA = (224, 224, 224)  # land state with zero of this resource
BG = (248, 248, 248)           # province borders / unowned (anti-aliased pixels)
PANEL = (252, 250, 245)        # legend panel — warm parchment
INK = (54, 42, 30)             # text — sepia ink
BORDER_INK = (92, 76, 60)      # state/coast outline
GRID_INK = (120, 110, 95)      # reference graticule

_HEX = re.compile(r"x([0-9A-Fa-f]{6})")
_SWATCH_LABELS = {"nodata": "no data", "water": "water"}


def set_swatch_labels(nodata: str, water: str) -> None:
    _SWATCH_LABELS["nodata"] = nodata
    _SWATCH_LABELS["water"] = water


def _fmt_val(val: float) -> str:
    if val == int(val):
        return f"{int(val)}"
    return f"{val:.1f}"


def _has_cjk(s: str) -> bool:
    return any(ord(c) > 0x2E80 for c in s)


def _packed_keys(arr: np.ndarray) -> np.ndarray:
    return (
        (arr[:, :, 0].astype(np.uint32) << 16)
        | (arr[:, :, 1].astype(np.uint32) << 8)
        | arr[:, :, 2].astype(np.uint32)
    )


class FontBook:
    """Resolves period-appropriate fonts, preferring Victoria 3's own bundled
    faces (EB Garamond, Playfair Display, the branded ParadoxVictorian), falling
    back to a serif CJK (Noto Serif SC / SimSun) for Chinese, then system fonts.
    """

    def __init__(self, game_root: Path):
        self.gf = game_root / "game" / "fonts"
        self._cache: dict[tuple[str, int], ImageFont.ImageFont] = {}

    def _load(self, rels: list[str], size: int) -> ImageFont.ImageFont:
        for rel in rels:
            p = Path(rel) if (":" in rel or rel.startswith("/")) else self.gf / rel
            key = (str(p), size)
            if key in self._cache:
                return self._cache[key]
            try:
                f = ImageFont.truetype(str(p), size)
                self._cache[key] = f
                return f
            except OSError:
                continue
        return ImageFont.load_default()

    def victorian(self, size: int) -> ImageFont.ImageFont:
        return self._load([
            "ParadoxVictorian/ParadoxVictorian-Condensed.otf",
            "PlayfairDisplay/PlayfairDisplay-Bold.ttf",
            "EBGaramond/EBGaramond-SemiBold.ttf",
            "C:/Windows/Fonts/Georgia.ttf",
        ], size)

    def serif_cjk(self, size: int) -> ImageFont.ImageFont:
        return self._load([
            "NotoSerif/NotoSerifSC-SemiBold.otf",
            "NotoSerif/NotoSerifSC-Medium.otf",
            "C:/Windows/Fonts/simsun.ttc",
            "C:/Windows/Fonts/msyh.ttc",
        ], size)

    def num(self, size: int) -> ImageFont.ImageFont:
        return self._load([
            "EBGaramond/EBGaramond-SemiBold.ttf",
            "PlayfairDisplay/PlayfairDisplay-Bold.ttf",
            "C:/Windows/Fonts/Georgia.ttf",
        ], size)

    def for_text(self, text: str, size: int, role: str = "title") -> ImageFont.ImageFont:
        if _has_cjk(text):
            return self.serif_cjk(size)
        return self.victorian(size) if role == "title" else self.num(size)


@dataclass
class ProvinceIndex:
    """Reusable map index: state↔color, water colors, packed key image, and
    per-state label anchors (a central point guaranteed to sit inside the state)."""

    game_root: Path
    size: tuple[int, int]
    full_size: tuple[int, int]
    keys: np.ndarray                          # (H, W) uint32 color keys
    state_to_colors: dict[str, list[int]]
    land_colors: np.ndarray
    water_colors: np.ndarray
    anchors: dict[str, tuple[float, float, float]]   # state_id -> (x, y, area_px)
    country_of: dict[int, str] = field(default_factory=dict)   # province color -> 1836 owner tag
    country_types: dict[str, str] = field(default_factory=dict)  # tag -> country_type
    _fonts: FontBook | None = field(default=None, repr=False)
    _state_px: np.ndarray | None = field(default=None, repr=False)

    @property
    def fonts(self) -> FontBook:
        if self._fonts is None:
            self._fonts = FontBook(self.game_root)
        return self._fonts

    @classmethod
    def build(cls, game: GameData, game_root: Path, width: int | None = 2400) -> "ProvinceIndex":
        map_dir = game_root / "game" / "map_data"
        state_to_colors: dict[str, list[int]] = {}
        water: set[int] = set()
        for sid, s in game.state_regions.items():
            if s.is_sea:
                water.update(s.province_colors)
            elif s.province_colors:
                state_to_colors[sid] = list(s.province_colors)
        dm = map_dir / "default.map"
        if dm.exists():
            txt = dm.read_text(encoding="utf-8-sig", errors="replace")
            for block in ("sea_starts", "lakes"):
                m = re.search(block + r"\s*=\s*\{([^}]*)\}", txt, re.S)
                if m:
                    water.update(int(h, 16) for h in _HEX.findall(m.group(1)))

        im = Image.open(map_dir / "provinces.png").convert("RGB")
        full_size = im.size
        if width and width < im.width:
            h = round(im.height * width / im.width)
            im = im.resize((width, h), Image.NEAREST)
        keys = _packed_keys(np.asarray(im))

        land = [c for cols in state_to_colors.values() for c in cols]
        land_colors = np.fromiter(land, dtype=np.int64, count=len(land))
        anchors = cls._compute_anchors(keys, state_to_colors, land_colors)
        from .countries import load_country_types, load_start_ownership
        country_of = load_start_ownership(game_root)
        country_types = load_country_types(game_root)

        log.info(
            "ProvinceIndex: %d land states / %d land colors, %d water colors, "
            "image %dx%d (from %dx%d)",
            len(state_to_colors), len(land), len(water), im.width, im.height, *full_size,
        )
        return cls(
            game_root=game_root, size=im.size, full_size=full_size, keys=keys,
            state_to_colors=state_to_colors, land_colors=land_colors,
            water_colors=np.fromiter(water, dtype=np.int64, count=len(water)),
            anchors=anchors, country_of=country_of, country_types=country_types,
        )

    @staticmethod
    def _compute_anchors(keys, state_to_colors, land_colors):
        """Per-state label anchor = the area-weighted centroid of all the state's
        pixels if that point lands inside the state, else the centroid of the
        province nearest to it (always inside a real province, never in water).
        Single O(pixels) pass for per-province stats."""
        H, W = keys.shape
        flat = keys.ravel()
        if len(land_colors) == 0:
            return {}
        land_sorted = np.sort(land_colors)
        pos = np.clip(np.searchsorted(land_sorted, flat), 0, len(land_sorted) - 1)
        valid = land_sorted[pos] == flat
        cidx = pos[valid]
        coords = np.nonzero(valid)[0]
        xs = (coords % W).astype(np.float64)
        ys = (coords // W).astype(np.float64)
        ncol = len(land_sorted)
        area = np.bincount(cidx, minlength=ncol).astype(np.float64)
        sumx = np.bincount(cidx, weights=xs, minlength=ncol)
        sumy = np.bincount(cidx, weights=ys, minlength=ncol)
        safe = np.maximum(area, 1)
        cx = sumx / safe
        cy = sumy / safe
        col2idx = {int(c): i for i, c in enumerate(land_sorted)}

        two_pi = 2.0 * np.pi
        anchors: dict[str, tuple[float, float, float]] = {}
        for sid, cols in state_to_colors.items():
            idxs = [col2idx[c] for c in cols if c in col2idx]
            if not idxs:
                continue
            a = area[idxs]
            total = float(a.sum())
            if total <= 0:
                continue
            # X uses a CIRCULAR (angular) weighted mean so states straddling the
            # wrap_x antimeridian seam (e.g. STATE_CHUKOTKA, which has provinces
            # on both the far-left and far-right of the bitmap) get a centroid on
            # the state, not averaged out to mid-ocean. Y is a plain mean.
            ang = cx[idxs] * (two_pi / W)
            sc = float((np.cos(ang) * a).sum())
            ss = float((np.sin(ang) * a).sum())
            if sc == 0.0 and ss == 0.0:
                scx = float((cx[idxs] * a).sum() / total)
            else:
                scx = (np.arctan2(ss, sc) % two_pi) / two_pi * W
            scy = float((cy[idxs] * a).sum() / total)
            xi, yi = int(round(scx)) % W, int(round(scy))
            inside = (0 <= yi < H and int(keys[yi, xi]) in set(cols))
            if inside:
                ax, ay = scx, scy
            else:
                # nearest province centroid (wrap-aware distance in x)
                best, bestd = idxs[0], float("inf")
                for i in idxs:
                    dx = abs(float(cx[i]) - scx)
                    dx = min(dx, W - dx)
                    d = dx * dx + (float(cy[i]) - scy) ** 2
                    if d < bestd:
                        bestd, best = d, i
                ax, ay = float(cx[best]), float(cy[best])
            anchors[sid] = (ax, ay, total)
        return anchors

    def _state_id_pixels(self) -> np.ndarray:
        """(H,W) int32 state index per pixel (-1 = water / border / unowned)."""
        if self._state_px is None:
            lut = np.full(1 << 24, -1, dtype=np.int32)
            for i, cols in enumerate(self.state_to_colors.values()):
                lut[np.asarray(cols, dtype=np.int64)] = i
            self._state_px = lut[self.keys]
        return self._state_px

    def _base_lut(self) -> np.ndarray:
        lut = np.empty((1 << 24, 3), dtype=np.uint8)
        lut[:] = BG
        if len(self.water_colors):
            lut[self.water_colors] = WATER
        if len(self.land_colors):
            lut[self.land_colors] = LAND_NODATA
        return lut

    def render(
        self,
        metric: Metric,
        *,
        cmap: str = cm.DEFAULT,
        reverse: bool = False,
        clip_percentile: float = 99.0,
        log_scale: bool = False,
        gamma: float = 0.7,
        labels: bool = True,
        borders: bool = True,
        grid: bool = False,
        national_borders: bool = False,
        min_country_provinces: int = 8,
        country_filter: str = "civilized",
        label_min_area: float = 36.0,
    ) -> tuple[Image.Image, float]:
        """Recolor the map for one metric. Returns (image_without_legend, vmax)."""
        table = cm.table_for(cmap, metric.key, metric.is_resource, metric.is_crop)
        state_vals = {sid: v for sid, v in metric.values.items() if v > 0}
        if not state_vals:
            return self.compose({}, borders=borders, grid=grid,
                                national_borders=national_borders,
                                min_country_provinces=min_country_provinces,
                                country_filter=country_filter), 0.0

        v = np.asarray(list(state_vals.values()), dtype=np.float64)
        scale = np.log1p(v) if log_scale else v
        vmax = float(np.percentile(scale, clip_percentile)) if clip_percentile < 100 else float(scale.max())
        if vmax <= 0:
            vmax = float(scale.max()) or 1.0

        state_fill: dict[str, tuple[int, int, int]] = {}
        for sid, val in state_vals.items():
            s = (np.log1p(val) if log_scale else val) / vmax
            s = min(max(s, 0.0), 1.0) ** gamma      # gamma spreads low/mid for depth
            rgb = cm.colorize(np.array([s]), table, reverse)[0]
            state_fill[sid] = (int(rgb[0]), int(rgb[1]), int(rgb[2]))

        labels_text = {sid: _fmt_val(val) for sid, val in state_vals.items()} if labels else None
        img = self.compose(state_fill, labels_text=labels_text, min_area=label_min_area,
                           borders=borders, grid=grid, national_borders=national_borders,
                           min_country_provinces=min_country_provinces, country_filter=country_filter)
        legend_vmax = float(v.max()) if log_scale else vmax
        return img, legend_vmax

    def compose(
        self,
        state_fill: dict[str, tuple[int, int, int]],
        *,
        labels_text: dict[str, str] | None = None,
        min_area: float = 36.0,
        borders: bool = False,
        grid: bool = False,
        national_borders: bool = False,
        min_country_provinces: int = 8,
        country_filter: str = "civilized",
    ) -> Image.Image:
        """Paint a map from explicit per-state fill colors, with optional state
        outlines, national borders, reference grid, and value labels."""
        lut = self._base_lut()
        colors: list[int] = []
        rgbs: list[tuple[int, int, int]] = []
        for sid, rgb in state_fill.items():
            for c in self.state_to_colors.get(sid, ()):
                colors.append(c)
                rgbs.append(rgb)
        if colors:
            lut[np.asarray(colors, dtype=np.int64)] = np.asarray(rgbs, dtype=np.uint8)
        arr = lut[self.keys]
        if borders:
            arr = self._overlay_borders(arr)
        if grid:
            arr = self._overlay_grid(arr)
        if national_borders:
            arr = self._overlay_national_borders(arr, min_country_provinces, country_filter)
        img = Image.fromarray(arr, "RGB")
        if labels_text:
            self._draw_text_labels(img, labels_text, state_fill, min_area)
        return img

    def _overlay_national_borders(self, arr: np.ndarray, min_provinces: int,
                                  mode: str = "civilized") -> np.ndarray:
        """Draw 1836 national borders (thicker/darker than state outlines), only
        for countries passing the filter (`mode`) and owning >= min_provinces."""
        from .countries import significant_countries
        if not self.country_of:
            return arr
        sig = significant_countries(self.country_of, min_provinces,
                                    types=self.country_types, mode=mode)
        if not sig:
            return arr
        tag2id = {t: i for i, t in enumerate(sorted(sig))}
        lut = np.full(1 << 24, -1, dtype=np.int32)
        for color_int, tag in self.country_of.items():
            i = tag2id.get(tag)
            if i is not None:
                lut[color_int] = i
        cp = lut[self.keys]
        e = np.zeros(cp.shape, dtype=bool)
        e[:, :-1] |= cp[:, :-1] != cp[:, 1:]
        e[:-1, :] |= cp[:-1, :] != cp[1:, :]
        sigpx = cp >= 0
        touch = sigpx.copy()
        touch[:, :-1] |= sigpx[:, 1:]
        touch[:-1, :] |= sigpx[1:, :]
        e &= touch
        try:
            from scipy.ndimage import binary_dilation
            iters = max(1, round(self.size[0] / 2400))
            e = binary_dilation(e, iterations=iters)
        except Exception:
            pass
        arr = arr.copy()
        arr[e] = (38, 28, 20)
        return arr

    def _overlay_borders(self, arr: np.ndarray) -> np.ndarray:
        """Darken pixels on a state/coast boundary (state id differs from a
        right/down neighbor). Makes individual states easy to tell apart."""
        sp = self._state_id_pixels()
        e = np.zeros(sp.shape, dtype=bool)
        e[:, :-1] |= sp[:, :-1] != sp[:, 1:]
        e[:-1, :] |= sp[:-1, :] != sp[1:, :]
        # Only outline where at least one side is land (skip open-ocean seams).
        land = sp >= 0
        touch = land.copy()
        touch[:, :-1] |= land[:, 1:]
        touch[:-1, :] |= land[1:, :]
        e &= touch
        arr = arr.copy()
        arr[e] = BORDER_INK
        return arr

    def _overlay_grid(self, arr: np.ndarray, divisions: int = 12) -> np.ndarray:
        """Faint evenly-spaced reference grid. NOTE: a pixel grid, not a true
        geographic graticule (Victoria 3's map is a stylized projection)."""
        arr = arr.copy().astype(np.float32)
        H, W = arr.shape[:2]
        g = np.array(GRID_INK, dtype=np.float32)
        a = 0.28
        step_x = max(1, W // (divisions * 2))
        step_y = max(1, H // divisions)
        xs = np.arange(step_x, W, step_x)
        ys = np.arange(step_y, H, step_y)
        arr[:, xs, :] = arr[:, xs, :] * (1 - a) + g * a
        arr[ys, :, :] = arr[ys, :, :] * (1 - a) + g * a
        return np.rint(arr).astype(np.uint8)

    def _draw_text_labels(self, img, text_by_state, fill_by_state, min_area):
        d = ImageDraw.Draw(img)
        drawn = skipped = 0
        # Scale the label-size bounds with the image width so labels look the
        # same relative size at any resolution (a full-res 8192 export gets ~3.4x
        # the px of a 2400 one — without this the cap made full-res numbers tiny).
        k = self.size[0] / 2400.0
        for sid, text in text_by_state.items():
            anc = self.anchors.get(sid)
            if anc is None:
                continue
            x, y, area = anc
            if area < min_area:
                skipped += 1
                continue
            size = int(min(max(area ** 0.5 * 0.45, 9 * k), 30 * k))
            font = self.fonts.num(size)
            r, g, b = fill_by_state.get(sid, (200, 200, 200))
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            fg = (45, 35, 25) if lum > 140 else (255, 252, 246)
            halo = (255, 252, 246) if lum > 140 else (40, 32, 24)
            d.text((x, y), text, font=font, fill=fg, anchor="mm",
                   stroke_width=max(1, size // 9), stroke_fill=halo)
            drawn += 1
        if skipped:
            log.info("Labels: drew %d, skipped %d states too small at this width "
                     "(raise --width / use --full-res)", drawn, skipped)


def find_ocean_spot(base: Image.Image, bw: int, bh: int, avoid=None):
    """Top-left (x, y) for a bw×bh title box placed over the emptiest stretch of
    ocean (max WATER coverage), avoiding the `avoid` rect (the legend). V3-wiki
    style — the title sits in open sea rather than occluding land."""
    W, H = base.size
    sw = 480
    sh = max(1, round(H * sw / W))
    sm = np.asarray(base.convert("RGB").resize((sw, sh), Image.NEAREST)).astype(int)
    water = ((np.abs(sm[:, :, 0] - WATER[0]) < 26) & (np.abs(sm[:, :, 1] - WATER[1]) < 26)
             & (np.abs(sm[:, :, 2] - WATER[2]) < 26)).astype(np.int64)
    ii = np.zeros((sh + 1, sw + 1), np.int64)
    ii[1:, 1:] = water.cumsum(0).cumsum(1)
    wbw = max(1, min(round(bw * sw / W), sw - 1))
    wbh = max(1, min(round(bh * sh / H), sh - 1))
    if avoid:
        ax0, ay0, ax1, ay1 = (avoid[0] * sw / W, avoid[1] * sh / H, avoid[2] * sw / W, avoid[3] * sh / H)
    else:
        ax0 = ay0 = ax1 = ay1 = -1
    best, bestfrac = None, -1.0
    ystep, xstep = max(1, wbh // 3), max(1, wbw // 4)
    for y in range(0, sh - wbh + 1, ystep):
        for x in range(0, sw - wbw + 1, xstep):
            if avoid and not (x + wbw < ax0 or x > ax1 or y + wbh < ay0 or y > ay1):
                continue
            s = ii[y + wbh, x + wbw] - ii[y, x + wbw] - ii[y + wbh, x] + ii[y, x]
            frac = s / (wbw * wbh)
            if frac > bestfrac:
                bestfrac, best = frac, (x, y)
    if best is None or bestfrac < 0.55:
        return round(W * 0.30), round(H * 0.04)        # fallback: north ocean band
    return round(best[0] * W / sw), round(best[1] * H / sh)


def draw_legend(
    img: Image.Image,
    *,
    title: str,
    subtitle: str,
    table,
    vmax: float,
    fonts: FontBook,
    reverse: bool = False,
    diverging: bool = False,
) -> Image.Image:
    """Title placed in open ocean (white-outlined, no plaque — minimal occlusion,
    V3-wiki style) + a legend card in the bottom-left (gradient + ticks +
    swatches + version line). Version line uses EB Garamond (has the middot the
    ParadoxVictorian title font lacks)."""
    w, h = img.size
    base = img.convert("RGBA")
    md = ImageDraw.Draw(base)
    scale = w / 2400.0
    WHITE = (255, 255, 255, 255)

    def tw(s, f):
        b = md.textbbox((0, 0), s, font=f)
        return b[2] - b[0]

    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    accent = tuple(int(c) for c in table[-1]) if not diverging else (60, 120, 60)
    margin = max(12, round(w * 0.014))

    # ---- legend card bottom-left (sized first so the title can avoid it) ----
    ssize = int(min(max(round(15 * scale), 13), 26))     # a touch bigger than before
    cpad = int(min(max(round(15 * scale), 12), 26))
    gap = max(4, round(ssize * 0.5))
    bar_h = int(min(max(round(17 * scale), 14), 30))
    sw = ssize
    tyg = 3
    sb = fonts.num(ssize)
    nodata, water = _SWATCH_LABELS["nodata"], _SWATCH_LABELS["water"]
    swrow = sw + 6 + tw(nodata, sb) + round(ssize * 1.4) + sw + 6 + tw(water, sb)
    inner = max(swrow, round(265 * scale))
    cbw = inner + 2 * cpad
    cbh = cpad + bar_h + tyg + ssize + gap + sw + cpad
    cx0 = margin
    cy0 = h - cbh - margin
    bx0, bx1 = cx0 + cpad, cx0 + cpad + inner

    # ---- title in open ocean (white-outlined, smaller, no plaque) ----
    probe = fonts.for_text(title, 120)
    pw = max(1, tw(title, probe))
    big = int(min(max(round(120 * (w * 0.28) / pw), round(24 * scale)), round(w * 0.055)))
    tf = fonts.for_text(title, big)
    title_w = tw(title, tf)
    chip = round(big * 0.84)
    chip_gap = round(big * 0.30)
    sub_size = max(round(big * 0.36), round(12 * scale))
    sfb = fonts.num(sub_size)
    block_w = max(chip + chip_gap + title_w, tw(subtitle, sfb))
    block_h = big + round(big * 0.26) + sub_size
    tx0, ty0 = find_ocean_spot(base, block_w, block_h, (cx0, cy0, cx0 + cbw, cy0 + cbh))
    swd = max(2, round(big * 0.085))
    cyc = ty0 + (big - chip) // 2
    rr = max(2, chip // 6)
    if diverging:
        d.rounded_rectangle([tx0, cyc, tx0 + chip, cyc + chip], radius=rr, fill=(170, 45, 40, 255))
        d.rectangle([tx0 + chip // 2, cyc, tx0 + chip, cyc + chip], fill=(*accent, 255))
        d.rounded_rectangle([tx0, cyc, tx0 + chip, cyc + chip], radius=rr, outline=WHITE, width=swd)
    else:
        d.rounded_rectangle([tx0, cyc, tx0 + chip, cyc + chip], radius=rr, fill=(*accent, 255), outline=WHITE, width=swd)
    d.text((tx0 + chip + chip_gap, ty0), title, font=tf, fill=(28, 20, 12, 255),
           stroke_width=swd, stroke_fill=WHITE)
    d.text((tx0, ty0 + big + round(big * 0.20)), subtitle, font=sfb, fill=(46, 36, 26, 255),
           stroke_width=max(1, round(sub_size * 0.16)), stroke_fill=(255, 255, 255, 235))

    # ---- draw the legend card ----
    crad = max(8, cpad // 2)
    d.rounded_rectangle([cx0 + 3, cy0 + 4, cx0 + cbw + 3, cy0 + cbh + 4], radius=crad, fill=(35, 25, 15, 60))
    d.rounded_rectangle([cx0, cy0, cx0 + cbw, cy0 + cbh], radius=crad,
                        fill=(*PANEL, 238), outline=(150, 135, 110, 255), width=2)
    yy = cy0 + cpad
    grad = cm.colorize(np.linspace(0, 1, inner), table, reverse)
    ov.paste(Image.fromarray(np.repeat(grad[None, :, :], bar_h, axis=0), "RGB"), (bx0, yy))
    d.rectangle([bx0, yy, bx1, yy + bar_h], outline=(150, 135, 110, 255))
    yy += bar_h + tyg
    if diverging:
        d.text((bx0, yy), f"-{vmax:.0f}", font=sb, fill=(150, 30, 30, 255))
        d.text(((bx0 + bx1) // 2 - tw("0", sb) // 2, yy), "0", font=sb, fill=(*INK, 255))
        pl = f"+{vmax:.0f}"
        d.text((bx1 - tw(pl, sb), yy), pl, font=sb, fill=(30, 120, 50, 255))
    else:
        d.text((bx0, yy), "0", font=sb, fill=(*INK, 255))
        vl = f"{vmax:.0f}" if vmax >= 10 else f"{vmax:.2f}".rstrip("0").rstrip(".")
        d.text((bx1 - tw(vl, sb), yy), vl, font=sb, fill=(*INK, 255))
    yy += ssize + gap
    d.rectangle([bx0, yy, bx0 + sw, yy + sw], fill=(*LAND_NODATA, 255), outline=(170, 160, 145, 255))
    d.text((bx0 + sw + 6, yy + (sw - ssize) // 2), nodata, font=sb, fill=(96, 84, 70, 255))
    mx = bx0 + sw + 6 + tw(nodata, sb) + round(ssize * 1.4)
    d.rectangle([mx, yy, mx + sw, yy + sw], fill=(*WATER, 255), outline=(170, 160, 145, 255))
    d.text((mx + sw + 6, yy + (sw - ssize) // 2), water, font=sb, fill=(96, 84, 70, 255))

    return Image.alpha_composite(base, ov).convert("RGB")


# ---------------------------------------------------------------------------
# SVG export helpers (hybrid: high-res raster fill + crisp vector text/legend).
# Kept here so both the metric maps (writer) and the change maps (diff) can use
# them without a circular import.
# ---------------------------------------------------------------------------

_TITLE_FAM = "PdxVictorian, EBGaramond, Georgia, serif"
_BODY_FAM = "EBGaramond, Georgia, serif"
_FONT_CSS_CACHE: dict[str, str] = {}
_MEAS = ImageDraw.Draw(Image.new("RGB", (8, 8)))


def _xml(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _font_face_css(game_root: Path) -> str:
    """@font-face <style> embedding the game's Victorian fonts so SVG text
    renders identically to the PNG (the fonts aren't system-installed)."""
    key = str(game_root)
    if key in _FONT_CSS_CACHE:
        return _FONT_CSS_CACHE[key]
    gf = game_root / "game" / "fonts"
    faces = []
    for fam, rel, fmt in (
        ("PdxVictorian", "ParadoxVictorian/ParadoxVictorian-Condensed.otf", "opentype"),
        ("EBGaramond", "EBGaramond/EBGaramond-SemiBold.ttf", "truetype"),
    ):
        try:
            b64 = base64.b64encode((gf / rel).read_bytes()).decode("ascii")
        except OSError:
            continue
        mime = "font/otf" if fmt == "opentype" else "font/ttf"
        faces.append(f"@font-face{{font-family:'{fam}';src:url(data:{mime};base64,{b64}) "
                     f"format('{fmt}');}}")
    css = f"<defs><style>{''.join(faces)}</style></defs>" if faces else ""
    _FONT_CSS_CACHE[key] = css
    return css


def svg_legend(index: "ProvinceIndex", fill_img: Image.Image, title: str, subtitle: str,
               table, vmax: float, diverging: bool = False) -> str:
    """Vector chrome matching draw_legend: white-outlined title in open ocean +
    a bottom-left legend card."""
    w, h = fill_img.size
    fonts = index.fonts
    scale = w / 2400.0

    def tw(s, f):
        b = _MEAS.textbbox((0, 0), s, font=f)
        return b[2] - b[0]

    accent = tuple(int(c) for c in table[-1]) if not diverging else (60, 120, 60)
    margin = max(12, round(w * 0.014))
    ssize = int(min(max(round(15 * scale), 13), 26))
    cpad = int(min(max(round(15 * scale), 12), 26))
    gap = max(4, round(ssize * 0.5))
    bar_h = int(min(max(round(17 * scale), 14), 30))
    sw = ssize
    tyg = 3
    sb = fonts.num(ssize)
    nodata, water = _SWATCH_LABELS["nodata"], _SWATCH_LABELS["water"]
    swrow = sw + 6 + tw(nodata, sb) + round(ssize * 1.4) + sw + 6 + tw(water, sb)
    inner = max(swrow, round(265 * scale))
    cbw = inner + 2 * cpad
    cbh = cpad + bar_h + tyg + ssize + gap + sw + cpad
    cx0 = margin
    cy0 = h - cbh - margin
    bx0, bx1 = cx0 + cpad, cx0 + cpad + inner
    crad = max(8, cpad // 2)
    yy = cy0 + cpad
    by = yy
    yy += bar_h + tyg
    tick_b = yy + ssize * 0.82
    yy += ssize + gap
    sq_y = yy
    lbl_b = yy + (sw + ssize) / 2 - 1

    probe = fonts.for_text(title, 120)
    pw = max(1, tw(title, probe))
    big = int(min(max(round(120 * (w * 0.28) / pw), round(24 * scale)), round(w * 0.055)))
    tf = fonts.for_text(title, big)
    title_w = tw(title, tf)
    chip = round(big * 0.84)
    chip_gap = round(big * 0.30)
    sub_size = max(round(big * 0.36), round(12 * scale))
    sfb = fonts.num(sub_size)
    block_w = max(chip + chip_gap + title_w, tw(subtitle, sfb))
    block_h = big + round(big * 0.26) + sub_size
    tx0, ty0 = find_ocean_spot(fill_img, block_w, block_h, (cx0, cy0, cx0 + cbw, cy0 + cbh))
    swd = max(2, round(big * 0.085))
    cyc = ty0 + (big - chip) // 2
    rr = max(2, chip // 6)
    title_b = ty0 + big * 0.80
    sub_b = ty0 + big + round(big * 0.20) + sub_size * 0.80

    stops = "".join(
        f'<stop offset="{i/(len(table)-1):.3f}" stop-color="rgb({int(c[0])},{int(c[1])},{int(c[2])})"/>'
        for i, c in enumerate(table))
    p = [f'<defs><linearGradient id="lg" x1="0" x2="1">{stops}</linearGradient></defs>',
         f'<g font-family="{_BODY_FAM}">',
         f'<rect x="{cx0+3}" y="{cy0+4}" width="{cbw}" height="{cbh}" rx="{crad}" fill="rgb(35,25,15)" fill-opacity="0.24"/>',
         f'<rect x="{cx0}" y="{cy0}" width="{cbw}" height="{cbh}" rx="{crad}" fill="rgb(252,250,245)" fill-opacity="0.94" stroke="rgb(150,135,110)" stroke-width="2"/>',
         f'<rect x="{bx0}" y="{by}" width="{inner}" height="{bar_h}" fill="url(#lg)" stroke="rgb(150,135,110)"/>']
    if diverging:
        p.append(f'<text x="{bx0}" y="{tick_b:.1f}" font-size="{ssize}" fill="rgb(150,30,30)">-{vmax:.0f}</text>')
        p.append(f'<text x="{(bx0+bx1)//2}" y="{tick_b:.1f}" font-size="{ssize}" text-anchor="middle" fill="rgb(54,42,30)">0</text>')
        p.append(f'<text x="{bx1}" y="{tick_b:.1f}" font-size="{ssize}" text-anchor="end" fill="rgb(30,120,50)">+{vmax:.0f}</text>')
    else:
        vl = f"{vmax:.0f}" if vmax >= 10 else f"{vmax:.2f}".rstrip("0").rstrip(".")
        p.append(f'<text x="{bx0}" y="{tick_b:.1f}" font-size="{ssize}" fill="rgb(54,42,30)">0</text>')
        p.append(f'<text x="{bx1}" y="{tick_b:.1f}" font-size="{ssize}" text-anchor="end" fill="rgb(54,42,30)">{vl}</text>')
    mx = bx0 + sw + 6 + tw(nodata, sb) + round(ssize * 1.4)
    p.append(f'<rect x="{bx0}" y="{sq_y}" width="{sw}" height="{sw}" fill="rgb(224,224,224)" stroke="rgb(170,160,145)"/>')
    p.append(f'<text x="{bx0+sw+6}" y="{lbl_b:.1f}" font-size="{ssize}" fill="rgb(96,84,70)">{_xml(nodata)}</text>')
    p.append(f'<rect x="{mx}" y="{sq_y}" width="{sw}" height="{sw}" fill="rgb(176,206,230)" stroke="rgb(170,160,145)"/>')
    p.append(f'<text x="{mx+sw+6}" y="{lbl_b:.1f}" font-size="{ssize}" fill="rgb(96,84,70)">{_xml(water)}</text>')
    p.append("</g>")
    # ---- title in open ocean, white-outlined ----
    p.append(f'<g paint-order="stroke" stroke-linejoin="round" stroke="rgb(255,255,255)">')
    if diverging:
        p.append(f'<rect x="{tx0}" y="{cyc}" width="{chip//2}" height="{chip}" rx="{rr}" fill="rgb(170,45,40)" stroke="none"/>')
        p.append(f'<rect x="{tx0+chip//2}" y="{cyc}" width="{chip-chip//2}" height="{chip}" fill="rgb{accent}" stroke="none"/>')
        p.append(f'<rect x="{tx0}" y="{cyc}" width="{chip}" height="{chip}" rx="{rr}" fill="none" stroke-width="{swd}"/>')
    else:
        p.append(f'<rect x="{tx0}" y="{cyc}" width="{chip}" height="{chip}" rx="{rr}" fill="rgb{accent}" stroke-width="{swd}"/>')
    p.append(f'<text x="{tx0+chip+chip_gap}" y="{title_b:.1f}" font-size="{big}" font-family="{_TITLE_FAM}" fill="rgb(28,20,12)" stroke-width="{swd}">{_xml(title)}</text>')
    p.append(f'<text x="{tx0}" y="{sub_b:.1f}" font-size="{sub_size}" font-family="{_BODY_FAM}" fill="rgb(46,36,26)" stroke-width="{max(1,round(sub_size*0.16))}">{_xml(subtitle)}</text>')
    p.append("</g>")
    return "\n".join(p)


def svg_document(index: "ProvinceIndex", fill_img: Image.Image, labels: list, legend_svg: str) -> str:
    """Assemble the SVG: embedded fonts + raster fill + vector labels + legend."""
    w, hh = fill_img.size
    buf = io.BytesIO()
    fill_img.save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {hh}" width="{w}" height="{hh}">',
        _font_face_css(index.game_root),
        f'<image href="data:image/png;base64,{b64}" x="0" y="0" width="{w}" height="{hh}"/>',
        f'<g text-anchor="middle" paint-order="stroke" stroke-linejoin="round" font-family="{_BODY_FAM}">',
    ]
    for x, y, sz, text, fg, halo in labels:
        parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" dy="0.35em" font-size="{sz:.0f}" '
            f'fill="{fg}" stroke="{halo}" stroke-width="{max(1, sz/9):.1f}">{_xml(text)}</text>')
    parts.append("</g>")
    parts.append(legend_svg)
    parts.append("</svg>")
    return "\n".join(parts)

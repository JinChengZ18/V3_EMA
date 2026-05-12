"""Locate the Victoria 3 install directory.

V3_EMA used to require being placed inside the game folder (sibling to
`game/` and `launcher/`). That broke whenever Steam validated files or
patched the game and removed our project. Now V3_EMA can live anywhere
and locates the game via this resolver.

Resolution order (first hit wins):
    1. explicit `--game-root <path>` CLI arg
    2. `V3_GAME_ROOT` environment variable
    3. cached path at `<V3_EMA>/.game_root` (written automatically after a
       successful auto-detect or by `v3-ema config --game-root`)
    4. Steam library scan (libraryfolders.vdf + Windows registry)
    5. legacy walk-up: parents of the V3_EMA directory itself, in case the
       project is still installed inside the game root
    6. raise FileNotFoundError with help text
"""
from __future__ import annotations
import os
import re
from pathlib import Path

CACHE_FILENAME = ".game_root"


def _project_root() -> Path:
    """Directory containing the v3_ema/ package (i.e. the V3_EMA project root)."""
    return Path(__file__).resolve().parent.parent


def _cache_path() -> Path:
    return _project_root() / CACHE_FILENAME


def is_valid_game_root(p: Path) -> bool:
    """A real V3 install has the launcher json + the production_methods dir."""
    if p is None:
        return False
    p = Path(p)
    return (
        (p / "launcher" / "launcher-settings.json").exists()
        and (p / "game" / "common" / "production_methods").is_dir()
    )


def load_cached() -> Path | None:
    f = _cache_path()
    if not f.exists():
        return None
    try:
        text = f.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not text:
        return None
    p = Path(text)
    return p if is_valid_game_root(p) else None


def save_cached(path: Path) -> None:
    _cache_path().write_text(str(Path(path).resolve()), encoding="utf-8")


def clear_cached() -> bool:
    f = _cache_path()
    if f.exists():
        f.unlink()
        return True
    return False


def _steam_install_dirs() -> list[Path]:
    """Candidate Steam install directories — checks registry + common locations."""
    cands: list[Path] = []
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
                v, _ = winreg.QueryValueEx(k, "SteamPath")
                if v:
                    cands.append(Path(v))
        except (OSError, ImportError):
            pass
    cands.extend([
        Path(r"C:\Program Files (x86)\Steam"),
        Path(r"C:\Program Files\Steam"),
        Path.home() / ".steam" / "steam",
        Path.home() / ".local" / "share" / "Steam",
        Path.home() / "Library" / "Application Support" / "Steam",
    ])
    return [c for c in cands if c.exists()]


def steam_libraries() -> list[Path]:
    """Parse libraryfolders.vdf in each candidate Steam install to enumerate
    library paths the user has configured."""
    libs: list[Path] = []
    for steam in _steam_install_dirs():
        for vdf in (
            steam / "config" / "libraryfolders.vdf",
            steam / "steamapps" / "libraryfolders.vdf",
        ):
            if not vdf.exists():
                continue
            try:
                text = vdf.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for raw in re.findall(r'"path"\s+"([^"]+)"', text):
                # vdf escapes backslashes
                libs.append(Path(raw.replace("\\\\", "\\")))
    # dedupe while preserving order
    seen: set[str] = set()
    out: list[Path] = []
    for p in libs:
        s = str(p.resolve()) if p.exists() else str(p)
        if s not in seen:
            seen.add(s)
            out.append(p)
    return out


def auto_detect() -> Path | None:
    """Scan Steam libraries for a Victoria 3 install."""
    for lib in steam_libraries():
        candidate = lib / "steamapps" / "common" / "Victoria 3"
        if is_valid_game_root(candidate):
            return candidate
    # Last-ditch direct guesses for users without libraryfolders.vdf
    for direct in (
        Path(r"C:\Program Files (x86)\Steam\steamapps\common\Victoria 3"),
        Path(r"C:\Program Files\Steam\steamapps\common\Victoria 3"),
        Path.home() / ".steam" / "steam" / "steamapps" / "common" / "Victoria 3",
    ):
        if is_valid_game_root(direct):
            return direct
    return None


def _legacy_walk_up() -> Path | None:
    """If the project is installed inside the game dir (legacy layout),
    one of its ancestors is the game root."""
    proj = _project_root()
    for ancestor in (proj.parent, proj.parent.parent, proj.parent.parent.parent):
        if is_valid_game_root(ancestor):
            return ancestor
    return None


def find_game_root(explicit: Path | None = None) -> Path:
    """Resolve a V3 install path. See module docstring for the priority order.

    Successful auto-detect (step 4) writes the cache so the next run skips
    the scan. Explicit / env / legacy-walk-up paths are NOT auto-cached
    (call `save_cached` if you want to persist them).

    Raises FileNotFoundError if nothing works.
    """
    if explicit is not None:
        p = Path(explicit).resolve()
        if is_valid_game_root(p):
            return p
        raise FileNotFoundError(
            f"--game-root {explicit}: missing required files. "
            f"Expected `launcher/launcher-settings.json` and "
            f"`game/common/production_methods/` under that path."
        )

    env = os.environ.get("V3_GAME_ROOT")
    if env:
        p = Path(env).resolve()
        if is_valid_game_root(p):
            return p

    cached = load_cached()
    if cached is not None:
        return cached

    auto = auto_detect()
    if auto is not None:
        try:
            save_cached(auto)
        except OSError:
            pass   # cache failure is non-fatal
        return auto

    legacy = _legacy_walk_up()
    if legacy is not None:
        return legacy

    raise FileNotFoundError(
        "Could not locate Victoria 3 install. Try one of:\n"
        "  • python -m v3_ema config --game-root <path>     "
        "(saves to .game_root for next time)\n"
        "  • python -m v3_ema <cmd> --game-root <path>      "
        "(one-off override)\n"
        "  • set V3_GAME_ROOT=<path>                        "
        "(environment variable)\n"
        "Path should be the V3 install root containing `game/` and `launcher/`."
    )

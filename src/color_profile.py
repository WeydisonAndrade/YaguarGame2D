"""Poses de arco: RGB do corpo igual a trigger01.png.

Só recorta o fundo preto (alpha). Os PNGs originais em assets/player/bow*.png
permanecem a fonte; *_color_corrected.png é cópia usada no jogo.
F4 compara original × versão de jogo no mesmo cenário.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from src.config import BOW_GRADE_POSES, YAGUAR_COLOR_PROFILE

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
PLAYER_DIR = ASSETS_DIR / "player"

_USE_RAW_BOW = False
_REF_CACHE: dict | None = None


def using_raw_bow_color() -> bool:
    """True quando F4 pede o PNG original, sem o grade."""
    return _USE_RAW_BOW


def toggle_raw_bow_color() -> bool:
    """Alterna original × corrigido. Devolve o novo estado (True = original)."""
    global _USE_RAW_BOW
    _USE_RAW_BOW = not _USE_RAW_BOW
    return _USE_RAW_BOW


def corrected_path(pose: str) -> Path:
    return PLAYER_DIR / f"{pose}_color_corrected.png"


def _opaque(arr: np.ndarray) -> np.ndarray:
    return arr[..., 3] >= 40.0


def _skin_mask(arr: np.ndarray) -> np.ndarray:
    a = arr[..., 3] >= 200.0
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    mx = np.maximum(np.maximum(r, g), b)
    h = arr.shape[0]
    y = np.arange(h, dtype=np.int32)[:, None]
    torso = (y >= int(h * 0.20)) & (y <= int(h * 0.75))
    return a & torso & (mx >= 30.0) & (r > g) & (g >= b - 8.0) & ((r - b) > 12.0)


def _red_feather_mask(arr: np.ndarray) -> np.ndarray:
    """Penas vermelhas do cocar: não herdam o ganho da pele."""
    a = arr[..., 3] >= 80.0
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    h = arr.shape[0]
    y = np.arange(h, dtype=np.int32)[:, None]
    return a & (y < int(h * 0.32)) & (r > g + 10.0) & (r > b + 14.0) & (r > 48.0)


def _luma(rgb: np.ndarray) -> np.ndarray:
    return 0.3 * rgb[..., 0] + 0.59 * rgb[..., 1] + 0.11 * rgb[..., 2]


def _laplacian_var(arr: np.ndarray) -> float:
    a = arr[..., 3] >= 180.0
    lum = _luma(arr).astype(np.float32)
    interior = a.copy()
    interior[0, :] = False
    interior[-1, :] = False
    interior[:, 0] = False
    interior[:, -1] = False
    lap = lum[2:, 1:-1] + lum[:-2, 1:-1] + lum[1:-1, 2:] + lum[1:-1, :-2] - 4.0 * lum[1:-1, 1:-1]
    mask = interior[1:-1, 1:-1]
    if not np.any(mask):
        return 0.0
    return float(lap[mask].var())


def _combat_refs(profile: dict) -> dict:
    """Estatísticas de pele, nitidez e altura de attack + defend."""
    global _REF_CACHE
    if _REF_CACHE is not None:
        return _REF_CACHE
    skins = []
    for name in profile.get("ref_poses", ("attack", "defend")):
        path = PLAYER_DIR / f"{name}.png"
        if not path.is_file():
            continue
        arr = np.asarray(Image.open(path).convert("RGBA")).astype(np.float32)
        mask = _skin_mask(arr)
        if np.any(mask):
            skins.append(arr[mask][:, :3])
    if not skins:
        _REF_CACHE = {
            "skin_mean": np.array([90.0, 48.0, 22.0], dtype=np.float32),
            "skin_luma": 57.4,
            "sharp": _trigger_sharp_target(int(profile.get("target_height", 168))),
        }
        return _REF_CACHE
    pooled = np.concatenate(skins, axis=0)
    mean = pooled.mean(axis=0).astype(np.float32)
    _REF_CACHE = {
        "skin_mean": mean,
        "skin_luma": float(_luma(mean[None, None, :])[0, 0]),
        "sharp": _trigger_sharp_target(int(profile.get("target_height", 168))),
    }
    return _REF_CACHE


def _trigger_sharp_target(height: int) -> float:
    """Nitidez de trigger01.png reduzido à altura do sprite — a referência do arco."""
    path = PLAYER_DIR / "trigger01.png"
    if not path.is_file():
        return 15000.0
    im = Image.open(path).convert("RGB")
    nw = max(1, int(round(im.size[0] * height / im.size[1])))
    small = im.resize((nw, height), Image.Resampling.LANCZOS)
    small = small.filter(ImageFilter.UnsharpMask(radius=1.15, percent=130, threshold=2))
    arr = np.asarray(small.convert("RGBA")).astype(np.float32)
    lum = _luma(arr)
    arr[..., 3] = np.where(lum > 10.0, 255.0, 0.0)
    return max(float(_laplacian_var(arr)), 12000.0)


def _fit_height(img: Image.Image, height: int) -> Image.Image:
    w, h = img.size
    if h == height or height <= 0:
        return img
    nw = max(1, int(round(w * height / h)))
    return img.resize((nw, height), Image.Resampling.LANCZOS)


def _sharpen_to(img: Image.Image, target: float) -> Image.Image:
    """Unsharp no RGB até a nitidez das poses de combate, sem mexer no alpha."""
    arr = np.asarray(img.convert("RGBA")).astype(np.float32)
    cur = _laplacian_var(arr)
    if target * 0.92 <= cur <= target * 1.22:
        return img
    rgb = img.convert("RGB")
    alpha = img.getchannel("A")
    best = img
    best_d = abs(cur - target)
    for percent in (80, 110, 130, 150, 170, 200):
        sharp = rgb.filter(ImageFilter.UnsharpMask(radius=1.15, percent=percent, threshold=5))
        merged = sharp.convert("RGBA")
        merged.putalpha(alpha)
        var = _laplacian_var(np.asarray(merged).astype(np.float32))
        dist = abs(var - target)
        if dist < best_d:
            best, best_d = merged, dist
        if target * 0.92 <= var <= target * 1.22:
            return merged
    return best


def _lock_skin_luma(img: Image.Image, target: float) -> Image.Image:
    """Reescala o RGB opaco para a pele ter o mesmo brilho de attack/defend."""
    arr = np.asarray(img.convert("RGBA")).astype(np.float32)
    skin = _skin_mask(arr)
    opaque = _opaque(arr)
    if np.count_nonzero(skin) < 80:
        return img
    rgb = arr[..., :3]
    scale = float(target) / max(float(_luma(rgb)[skin].mean()), 1.0)
    if abs(scale - 1.0) < 0.02:
        return img
    rgb = np.clip(rgb * scale, 0.0, 255.0)
    rgb[..., 1] = np.minimum(rgb[..., 1], rgb[..., 0])
    out = arr.copy()
    out[..., 0] = np.where(opaque, rgb[..., 0], arr[..., 0])
    out[..., 1] = np.where(opaque, rgb[..., 1], arr[..., 1])
    out[..., 2] = np.where(opaque, rgb[..., 2], arr[..., 2])
    return Image.fromarray(np.round(out).astype(np.uint8), "RGBA")


def apply_yaguar_grade(
    img: Image.Image,
    profile: dict | None = None,
    *,
    gains: np.ndarray | None = None,
    match_size: bool = False,
    match_sharpness: bool = False,
) -> Image.Image:
    """Não pinta o corpo. O RGB opaco de trigger01/bow permanece igual.

    Só devolve RGBA e, se pedido, ajusta a altura do sprite.
    """
    p = profile or YAGUAR_COLOR_PROFILE
    src = img.convert("RGBA")
    if match_size:
        src = _fit_height(src, int(p.get("target_height", 168)))
    return src


def prepare_bow_color_grades(force: bool = False) -> None:
    """Copia as poses de arco para *_color_corrected.png sem mudar o RGB."""
    PLAYER_DIR.mkdir(parents=True, exist_ok=True)
    for pose in BOW_GRADE_POSES:
        src = PLAYER_DIR / f"{pose}.png"
        dest = corrected_path(pose)
        if not src.is_file():
            continue
        if dest.exists() and not force:
            continue
        apply_yaguar_grade(Image.open(src), match_size=True).save(dest, "PNG")
    arrow = PLAYER_DIR / "arrow.png"
    arrow_dest = PLAYER_DIR / "arrow_color_corrected.png"
    if arrow.is_file() and (force or not arrow_dest.exists()):
        apply_yaguar_grade(Image.open(arrow)).save(arrow_dest, "PNG")

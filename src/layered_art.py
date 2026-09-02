"""Camadas visuais derivadas da pintura existente + recortes com chroma.

Não sobrescreve forest1/forest2/player. Gera PNGs com alpha em pastas novas.
Se a fonte gerada faltar, o jogo continua com o strip atual.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageEnhance, ImageFilter

from src.config import SCREEN_HEIGHT, SCREEN_WIDTH

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
PARALLAX_DIR = ASSETS_DIR / "parallax"
GEN_INBOX = Path(
    r"C:\Users\weydi\.cursor\projects\c-Users-weydi-Desktop-Yaguar-O-Guardiao-da-Floresta\assets"
)

BG_MOUNTAIN_FAR = ASSETS_DIR / "backgrounds" / "mountain" / "far" / "bg_mountain_far_01.png"
BG_MOUNTAIN_MID = ASSETS_DIR / "backgrounds" / "mountain" / "mid" / "bg_mountain_mid_01.png"
ENV_CAVE_ENTRANCE = ASSETS_DIR / "backgrounds" / "cave" / "env_cave_entrance_01.png"
PLAT_GROUND_01 = ASSETS_DIR / "gameplay" / "platforms" / "plat_mountain_ground_01.png"
PLAT_GROUND_02 = ASSETS_DIR / "gameplay" / "platforms" / "plat_mountain_ground_02.png"
PLAT_LEDGE = ASSETS_DIR / "gameplay" / "platforms" / "plat_mountain_ledge_01.png"
PLAT_EDGE = ASSETS_DIR / "gameplay" / "platforms" / "plat_mountain_edge_01.png"
PLAT_CAVE_FLOOR = ASSETS_DIR / "gameplay" / "platforms" / "plat_cave_floor_01.png"
FG_LEAVES = ASSETS_DIR / "foreground" / "mountain" / "fg_mountain_leaves_01.png"
FG_ROOT = ASSETS_DIR / "foreground" / "mountain" / "fg_mountain_root_01.png"
FG_VINE = ASSETS_DIR / "foreground" / "mountain" / "fg_mountain_vine_01.png"
FG_MIST = ASSETS_DIR / "foreground" / "mountain" / "fg_mountain_mist_01.png"
BG_TRANS_VM = ASSETS_DIR / "backgrounds" / "transitions" / "bg_trans_vines_mountain_01.png"
BG_MID_FENDAS_VINES = ASSETS_DIR / "backgrounds" / "gaps" / "bg_mid_fendas_vines_01.png"
VINE_SEG_01 = ASSETS_DIR / "gameplay" / "vines" / "segments" / "vine_segment_01.png"
VINE_SEG_02 = ASSETS_DIR / "gameplay" / "vines" / "segments" / "vine_segment_02.png"
VINE_SEG_LEAF = ASSETS_DIR / "gameplay" / "vines" / "segments" / "vine_segment_leaf.png"
VINE_ANCHOR_BRANCH = ASSETS_DIR / "gameplay" / "vines" / "anchors" / "vine_anchor_branch_01.png"
VINE_ANCHOR_ROOT = ASSETS_DIR / "gameplay" / "vines" / "anchors" / "vine_anchor_root_01.png"
VINE_ANCHOR_ROCK = ASSETS_DIR / "gameplay" / "vines" / "anchors" / "vine_anchor_rock_01.png"
VINE_ANCHOR_CEILING = ASSETS_DIR / "gameplay" / "vines" / "anchors" / "vine_anchor_ceiling_01.png"
VINE_MOSS_TUFT = ASSETS_DIR / "gameplay" / "vines" / "segments" / "vine_moss_tuft_01.png"
ENV_CLIFF_COVER = ASSETS_DIR / "backgrounds" / "vines" / "env_cliff_cover_left.png"

LAYER_OUTPUTS = (
    BG_MOUNTAIN_FAR,
    BG_MOUNTAIN_MID,
    ENV_CAVE_ENTRANCE,
    PLAT_GROUND_01,
    PLAT_GROUND_02,
    PLAT_LEDGE,
    PLAT_EDGE,
    PLAT_CAVE_FLOOR,
    FG_LEAVES,
    FG_ROOT,
    FG_VINE,
    FG_MIST,
    BG_TRANS_VM,
    BG_MID_FENDAS_VINES,
    VINE_SEG_01,
    VINE_SEG_02,
    VINE_SEG_LEAF,
    VINE_ANCHOR_BRANCH,
    VINE_ANCHOR_ROOT,
    VINE_ANCHOR_ROCK,
    VINE_ANCHOR_CEILING,
    VINE_MOSS_TUFT,
    ENV_CLIFF_COVER,
)


def _cover_crop(src: Image.Image, tw: int, th: int) -> Image.Image:
    """Escala no modo cover e recorta o centro no tamanho alvo."""
    sw, sh = src.size
    scale = max(tw / sw, th / sh)
    size = (max(tw, int(round(sw * scale))), max(th, int(round(sh * scale))))
    resized = src.resize(size, Image.Resampling.LANCZOS)
    x0 = max(0, (resized.width - tw) // 2)
    y0 = max(0, (resized.height - th) // 2)
    return resized.crop((x0, y0, x0 + tw, y0 + th))


def _save(path: Path, img: Image.Image) -> Path:
    """Grava o PNG, criando a pasta de destino se ainda não existir."""
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG")
    return path


def chroma_key_magenta(im: Image.Image, hard: float = 88.0, soft: float = 48.0) -> Image.Image:
    """Remove magenta de chroma (#FF00FF e vizinhos) e faz despill nas bordas."""
    rgba = np.asarray(im.convert("RGBA"))
    rgb = rgba[..., :3].astype(np.float32)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    dist = np.sqrt((r - 255.0) ** 2 + (g - 0.0) ** 2 + (b - 255.0) ** 2)
    mag = np.minimum(r, b) - g
    keyed = (dist < hard) | ((r > 150) & (b > 130) & (g < 95) & (mag > 42))
    fringe = (mag > 28) & (r > 90) & (b > 70) & (g < r - 12)
    edge = ((dist < hard + soft) | fringe) & ~keyed
    alpha = rgba[..., 3].astype(np.float32)
    alpha = np.where(keyed, 0.0, alpha)
    fade = np.clip((dist - hard) / max(1.0, soft), 0.0, 1.0)
    mag_fade = np.clip(1.0 - (mag - 28.0) / 70.0, 0.0, 1.0)
    alpha = np.where(edge, alpha * np.minimum(fade, mag_fade), alpha)
    spill = np.clip(mag / 55.0, 0.0, 1.0) * (alpha > 8)
    g2 = np.minimum(255.0, g + spill * np.maximum(0.0, np.minimum(r, b) - g) * 0.75)
    r2 = r - spill * np.maximum(0.0, r - g2) * 0.55
    b2 = b - spill * np.maximum(0.0, b - g2) * 0.55
    out = np.empty_like(rgba)
    out[..., 0] = np.clip(r2, 0, 255).astype(np.uint8)
    out[..., 1] = np.clip(g2, 0, 255).astype(np.uint8)
    out[..., 2] = np.clip(b2, 0, 255).astype(np.uint8)
    out[..., 3] = np.clip(alpha, 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def chroma_key_black(im: Image.Image, luma_cut: float = 16.0) -> Image.Image:
    """Fundo preto de letterbox → alpha, sem comer casca escura com verde."""
    rgba = np.asarray(im.convert("RGBA"))
    rgb = rgba[..., :3].astype(np.float32)
    luma = 0.3 * rgb[..., 0] + 0.59 * rgb[..., 1] + 0.11 * rgb[..., 2]
    greenish = rgb[..., 1] > rgb[..., 0] + 8
    keyed = (luma < luma_cut) & ~greenish & (rgba[..., 3] > 0)
    alpha = rgba[..., 3].astype(np.float32)
    alpha = np.where(keyed, 0.0, alpha)
    rgba = rgba.copy()
    rgba[..., 3] = np.clip(alpha, 0, 255).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def _autocrop(im: Image.Image, pad: int = 2) -> Image.Image:
    """Corta o retângulo opaco da imagem, com uma margem extra em pixels."""
    bbox = im.getbbox()
    if not bbox:
        return im
    x0, y0, x1, y1 = bbox
    x0 = max(0, x0 - pad)
    y0 = max(0, y0 - pad)
    x1 = min(im.width, x1 + pad)
    y1 = min(im.height, y1 + pad)
    return im.crop((x0, y0, x1, y1))


def _fit_height(im: Image.Image, height: int, max_width: int | None = None) -> Image.Image:
    """Redimensiona pela altura; se passar de max_width, limita pela largura."""
    if im.height == 0:
        return im
    scale = height / im.height
    nw = max(1, int(round(im.width * scale)))
    nh = height
    if max_width is not None and nw > max_width:
        scale = max_width / im.width
        nw = max_width
        nh = max(1, int(round(im.height * scale)))
    return im.resize((nw, nh), Image.Resampling.LANCZOS)


def _hfade(width: int, height: int, fade: int, reverse: bool = False) -> Image.Image:
    """Máscara horizontal suave para costurar duas pinturas lado a lado."""
    fade = max(1, min(width, fade))
    row = []
    for x in range(width):
        if reverse:
            t = min(1.0, (width - 1 - x) / fade) if x > width - fade else 1.0
        else:
            t = min(1.0, x / fade) if x < fade else 1.0
        s = t * t * (3 - 2 * t)
        row.append(int(255 * s))
    img = Image.new("L", (width, 1))
    img.putdata(row)
    return img.resize((width, height), Image.Resampling.BILINEAR)


def _vfade(width: int, height: int, top: int, bottom: int) -> Image.Image:
    """Máscara vertical: some no topo e/ou na base para colar recortes sem corte seco."""
    mask = Image.new("L", (width, height), 255)
    px = mask.load()
    top = max(1, min(height, top))
    bottom = max(1, min(height, bottom))
    for y in range(height):
        if y < top:
            t = y / top
            a = int(255 * (t * t * (3 - 2 * t)))
        elif y > height - 1 - bottom:
            t = (height - 1 - y) / bottom
            a = int(255 * (t * t * (3 - 2 * t)))
        else:
            a = 255
        for x in range(width):
            px[x, y] = a
    return mask


def _irregular_hmask(width: int, height: int, fade_lo: int, fade_hi: int) -> Image.Image:
    """Fade horizontal com onda, para a junta não virar uma linha reta."""
    fade_lo = max(8, min(width, fade_lo))
    fade_hi = max(fade_lo, min(width, fade_hi))
    mask = Image.new("L", (width, height))
    px = mask.load()
    span = fade_hi - fade_lo
    for y in range(height):
        wave = 0.5 + 0.5 * math.sin(y * 0.027) * 0.72 + 0.18 * math.sin(y * 0.011 + 1.3)
        fade = int(fade_lo + span * max(0.0, min(1.0, wave)))
        fade = max(8, min(width, fade))
        for x in range(width):
            if x >= fade:
                px[x, y] = 255
            else:
                u = x / fade
                px[x, y] = int(255 * (u * u * (3.0 - 2.0 * u)))
    return mask


def _find_gen(name: str) -> Path | None:
    """Procura o recorte gerado no pacote do jogo ou na caixa de entrada do Cursor."""
    for root in (ASSETS_DIR, GEN_INBOX):
        path = root / name
        if path.is_file():
            return path
    return None


def _process_cutout(name: str, height: int, max_width: int | None = None) -> Image.Image | None:
    """Remove o magenta, corta o vazio e encaixa o recorte na altura pedida."""
    src = _find_gen(name)
    if src is None:
        return None
    keyed = chroma_key_magenta(Image.open(src))
    keyed = _autocrop(keyed, pad=4)
    if keyed.getbbox() is None:
        return None
    return _fit_height(keyed, height, max_width=max_width)


def _build_mountain_far() -> None:
    """Gera o fundo distante da montanha a partir de forest_far/forest2."""
    src = PARALLAX_DIR / "forest_far.png"
    if not src.is_file():
        src = PARALLAX_DIR / "forest2.png"
    if not src.is_file():
        return
    raw = Image.open(src).convert("RGB")
    # Corta o muro de pedra jogável; fica só floresta/névoa distante.
    cut_h = int(raw.height * 0.78)
    far = raw.crop((0, 0, raw.width, cut_h))
    far = _cover_crop(far, SCREEN_WIDTH * 2, SCREEN_HEIGHT)
    far = ImageEnhance.Color(far).enhance(0.72)
    far = ImageEnhance.Contrast(far).enhance(0.78)
    far = ImageEnhance.Brightness(far).enhance(1.08)
    far = far.filter(ImageFilter.GaussianBlur(radius=1.6))
    out = far.convert("RGBA")
    out.putalpha(_vfade(out.width, out.height, 0, 90))
    _save(BG_MOUNTAIN_FAR, out)


def _build_mountain_mid() -> None:
    """Gera o plano médio da montanha com chroma magenta e preto."""
    src = PARALLAX_DIR / "forest_mid.png"
    if not src.is_file():
        return
    keyed = chroma_key_magenta(Image.open(src))
    keyed = chroma_key_black(keyed, luma_cut=14)
    keyed = _autocrop(keyed, pad=2)
    if keyed.getbbox() is None:
        return
    mid = _fit_height(keyed, SCREEN_HEIGHT, max_width=SCREEN_WIDTH + 280)
    mid = ImageEnhance.Contrast(mid).enhance(1.06)
    _save(BG_MOUNTAIN_MID, mid)


def _build_cave_entrance() -> None:
    """Gera o recorte da boca da caverna, se o PNG de chroma existir."""
    cut = _process_cutout("env_cave_entrance_01.png", SCREEN_HEIGHT, max_width=SCREEN_WIDTH + 80)
    if cut is None:
        return
    _save(ENV_CAVE_ENTRANCE, cut)


def _feather_top(im: Image.Image, fade: int) -> Image.Image:
    """Suaviza o topo de uma faixa de chão para colar sobre o fundo."""
    im = im.convert("RGBA")
    mask = _vfade(im.width, im.height, fade, 0)
    alpha = im.split()[-1]
    im.putalpha(ImageChops.multiply(alpha, mask))
    return im


def _build_terrain() -> None:
    """Recorta faixas de chão, borda e piso de caverna a partir do foreground."""
    wall_src = PARALLAX_DIR / "forest_fg.png"
    forest2 = PARALLAX_DIR / "forest2.png"
    if wall_src.is_file():
        keyed = chroma_key_magenta(Image.open(wall_src))
        keyed = chroma_key_black(keyed, luma_cut=12)
        w, h = keyed.size
        ground = keyed.crop((0, int(h * 0.62), w, h))
        ground = _autocrop(ground)
        if ground.getbbox():
            g1 = ground.resize((SCREEN_WIDTH, max(72, int(ground.height * SCREEN_WIDTH / max(1, ground.width)))), Image.Resampling.LANCZOS)
            g1 = _feather_top(g1, 28)
            _save(PLAT_GROUND_01, g1)
            ledge = ground.crop((0, 0, max(8, ground.width // 3), ground.height))
            ledge = ledge.resize((340, 86), Image.Resampling.LANCZOS)
            _save(PLAT_LEDGE, _feather_top(ledge, 18))
            edge = ground.crop((max(0, ground.width - ground.width // 4), 0, ground.width, ground.height))
            edge = edge.resize((220, 96), Image.Resampling.LANCZOS)
            _save(PLAT_EDGE, _feather_top(edge, 16))
    if forest2.is_file():
        raw = Image.open(forest2).convert("RGBA")
        w, h = raw.size
        strip = raw.crop((0, int(h * 0.72), w, h))
        strip = strip.resize((SCREEN_WIDTH, 118), Image.Resampling.LANCZOS)
        strip = _feather_top(strip, 26)
        _save(PLAT_GROUND_02, strip)
        cave = ImageEnhance.Color(strip).enhance(0.55)
        cave = ImageEnhance.Brightness(cave).enhance(0.72)
        cave = ImageEnhance.Contrast(cave).enhance(1.08)
        _save(PLAT_CAVE_FLOOR, cave)


def _build_foreground() -> None:
    """Gera folhas, cipó, raiz e névoa de primeiro plano."""
    fg_src = PARALLAX_DIR / "forest_fg.png"
    mid_src = PARALLAX_DIR / "forest_mid.png"
    if fg_src.is_file():
        keyed = chroma_key_magenta(Image.open(fg_src))
        keyed = chroma_key_black(keyed, luma_cut=12)
        w, h = keyed.size
        hang = keyed.crop((0, 0, w, int(h * 0.48)))
        hang = _autocrop(hang)
        if hang.getbbox():
            hang = hang.resize((SCREEN_WIDTH, max(80, int(hang.height * SCREEN_WIDTH / max(1, hang.width)))), Image.Resampling.LANCZOS)
            _save(FG_VINE, hang)
            leaves = hang.crop((0, 0, hang.width // 2, min(hang.height, 160)))
            _save(FG_LEAVES, leaves)
    if mid_src.is_file():
        keyed = chroma_key_magenta(Image.open(mid_src))
        keyed = chroma_key_black(keyed, luma_cut=14)
        w, h = keyed.size
        root = keyed.crop((0, int(h * 0.55), int(w * 0.42), h))
        root = _autocrop(root)
        if root.getbbox():
            root = _fit_height(root, 210, max_width=360)
            _save(FG_ROOT, root)
    mist = Image.new("RGBA", (SCREEN_WIDTH + 200, 140), (0, 0, 0, 0))
    px = mist.load()
    rng = np.random.default_rng(7)
    for _ in range(14):
        cx = int(rng.integers(40, mist.width - 40))
        cy = int(rng.integers(20, mist.height - 20))
        rw = int(rng.integers(80, 220))
        rh = int(rng.integers(28, 70))
        shade = int(rng.integers(186, 214))
        for y in range(max(0, cy - rh), min(mist.height, cy + rh)):
            for x in range(max(0, cx - rw), min(mist.width, cx + rw)):
                nx = (x - cx) / rw
                ny = (y - cy) / rh
                d = nx * nx + ny * ny
                if d < 1.0:
                    a = int(22 * (1.0 - d) ** 2)
                    r, g, b, oa = px[x, y]
                    px[x, y] = (shade, shade + 8, shade + 4, min(255, oa + a))
    _save(FG_MIST, mist)


def _build_transition() -> None:
    """Monta a faixa de passagem cipó → montanha, com junta irregular."""
    vines = PARALLAX_DIR / "forest_vines.jpg"
    mountain = PARALLAX_DIR / "forest2.png"
    if not vines.is_file() or not mountain.is_file():
        return
    left = _cover_crop(Image.open(vines).convert("RGB"), 520, SCREEN_HEIGHT)
    right = _cover_crop(Image.open(mountain).convert("RGB"), 520, SCREEN_HEIGHT)
    right = ImageEnhance.Color(right).enhance(0.7)
    right = ImageEnhance.Brightness(right).enhance(0.9)
    canvas = Image.new("RGB", (840, SCREEN_HEIGHT), (22, 36, 28))
    canvas.paste(left, (0, 0))
    overlay = right.convert("RGBA")
    overlay.putalpha(_irregular_hmask(overlay.width, overlay.height, 140, 280))
    canvas.paste(overlay, (320, 0), overlay)
    canvas = ImageEnhance.Color(canvas).enhance(0.86)
    _save(BG_TRANS_VM, canvas.convert("RGB"))


def _hide_climber(img: Image.Image) -> Image.Image:
    """Tapa a silhueta de um personagem que veio baked na pintura das fendas."""
    w, h = img.size
    x0, y0, x1, y1 = 18, max(0, int(h * 0.22)), min(w, 175), min(h, int(h * 0.48))
    if x1 <= x0 + 8 or y1 <= y0 + 8:
        return img
    src_x0 = min(w - 2, max(x1 + 8, 190))
    src_x1 = min(w, src_x0 + (x1 - x0))
    patch = img.crop((src_x0, y0, src_x1, y1))
    if patch.size[0] < 8:
        return img
    patch = patch.resize((x1 - x0, y1 - y0), Image.Resampling.LANCZOS).filter(ImageFilter.SMOOTH)
    out = img.copy()
    out.paste(patch, (x0, y0))
    return out


def _build_midground() -> None:
    """Dois painéis de vale+cipó (2048×600) para o plano médio das fendas."""
    fendas = PARALLAX_DIR / "forest_fendas_far.png"
    vines = PARALLAX_DIR / "forest_vines.jpg"
    if not fendas.is_file():
        return
    left = _cover_crop(Image.open(fendas).convert("RGB"), SCREEN_WIDTH, SCREEN_HEIGHT)
    right = ImageEnhance.Color(left).enhance(0.78)
    right = ImageEnhance.Brightness(right).enhance(0.9)
    right = ImageEnhance.Contrast(right).enhance(0.94)
    if vines.is_file():
        cave = _cover_crop(Image.open(vines).convert("RGB"), SCREEN_WIDTH, SCREEN_HEIGHT)
        ceiling = cave.crop((0, 0, SCREEN_WIDTH, 260)).convert("RGBA")
        ceiling.putalpha(_vfade(ceiling.width, ceiling.height, 0, 90))
        right_rgba = right.convert("RGBA")
        right_rgba.paste(ceiling, (0, 0), ceiling)
        right = right_rgba.convert("RGB")
    width = SCREEN_WIDTH * 2
    canvas = Image.new("RGB", (width, SCREEN_HEIGHT), (22, 36, 28))
    canvas.paste(left, (0, 0))
    canvas.paste(right, (SCREEN_WIDTH, 0))
    blend = 300
    x0 = SCREEN_WIDTH - blend
    seam_l = canvas.crop((x0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
    seam_r = right.crop((0, 0, blend, SCREEN_HEIGHT))
    mask = _hfade(blend, SCREEN_HEIGHT, blend)
    canvas.paste(Image.composite(seam_r, seam_l, mask), (x0, 0))
    _save(BG_MID_FENDAS_VINES, canvas)


def _process_vine_tile(name: str, target_w: int, tile_h: int) -> Image.Image | None:
    """Recorta um segmento de cipó na largura do tile, com chroma magenta."""
    src = _find_gen(name)
    if src is None:
        return None
    keyed = chroma_key_magenta(Image.open(src))
    cut = _autocrop(keyed, pad=2)
    if cut.getbbox() is None or cut.width < 4:
        return None
    scale = target_w / cut.width
    nw = target_w
    nh = max(tile_h, int(round(cut.height * scale)))
    cut = cut.resize((nw, nh), Image.Resampling.LANCZOS)
    if nh > tile_h + 4:
        y0 = max(0, (nh - tile_h) // 2)
        cut = cut.crop((0, y0, nw, y0 + tile_h))
    return cut


def _build_vine_cutouts() -> None:
    """Gera segmentos, âncoras e tufo de musgo usados nas trepadeiras jogáveis."""
    segs = (
        ("vine_liana_01.png", VINE_SEG_01, 20, 96),
        ("vine_liana_02.png", VINE_SEG_02, 18, 96),
    )
    for name, dest, tw, th in segs:
        cut = _process_vine_tile(name, tw, th)
        if cut is None:
            fallback = "vine_segment_01.png" if dest == VINE_SEG_01 else "vine_segment_02.png"
            cut = _process_vine_tile(fallback, tw, th)
        if cut is not None:
            _save(dest, cut)
    tuft = _process_cutout("vine_moss_tuft_01.png", 32, max_width=44)
    if tuft is None:
        tuft = _process_cutout("vine_segment_leaf.png", 36, max_width=48)
    if tuft is not None:
        _save(VINE_SEG_LEAF, tuft)
        _save(VINE_MOSS_TUFT, tuft)
    ceiling = _process_cutout("vine_anchor_ceiling_01.png", 72, max_width=150)
    if ceiling is not None:
        _save(VINE_ANCHOR_CEILING, ceiling)
    mapping = (
        ("vine_anchor_branch_01.png", VINE_ANCHOR_BRANCH, 78, 160),
        ("vine_anchor_root_01.png", VINE_ANCHOR_ROOT, 78, 160),
        ("vine_anchor_rock_01.png", VINE_ANCHOR_ROCK, 72, 150),
    )
    for name, dest, height, max_w in mapping:
        cut = _process_cutout(name, height, max_width=max_w)
        if cut is not None:
            _save(dest, cut)
    cliff = _process_cutout("env_cliff_cover_left.png", 420, max_width=280)
    if cliff is not None:
        _save(ENV_CLIFF_COVER, cliff)


def _sources() -> list[Path]:
    """Lista as pinturas de origem cuja data decide se as camadas precisam ser refeitas."""
    names = (
        "forest2.png",
        "forest_far.png",
        "forest_mid.png",
        "forest_fg.png",
        "forest_fendas_far.png",
        "forest_vines.jpg",
    )
    out = [PARALLAX_DIR / n for n in names]
    out.append(Path(__file__))
    for name in (
        "vine_liana_01.png",
        "vine_liana_02.png",
        "vine_moss_tuft_01.png",
        "vine_anchor_ceiling_01.png",
        "env_cliff_cover_left.png",
        "env_cave_entrance_01.png",
        "vine_segment_01.png",
        "vine_segment_02.png",
        "vine_segment_leaf.png",
        "vine_anchor_branch_01.png",
        "vine_anchor_root_01.png",
        "vine_anchor_rock_01.png",
    ):
        found = _find_gen(name)
        if found is not None:
            out.append(found)
    return [p for p in out if p.is_file()]


def build_world_layers() -> list[Path]:
    """Reconstrói todas as camadas derivadas e devolve os caminhos que existem."""
    _build_mountain_far()
    _build_mountain_mid()
    _build_cave_entrance()
    _build_terrain()
    _build_foreground()
    _build_transition()
    _build_midground()
    _build_vine_cutouts()
    return [p for p in LAYER_OUTPUTS if p.is_file()]


def ensure_world_layers(force: bool = False) -> list[Path]:
    """Reconstrói as camadas só se alguma origem for mais nova que o PNG gerado."""
    sources = _sources()
    existing = [p for p in LAYER_OUTPUTS if p.is_file()]
    if not force and existing and sources:
        newest_src = max(p.stat().st_mtime for p in sources)
        oldest_out = min(p.stat().st_mtime for p in existing)
        if oldest_out >= newest_src and len(existing) >= 12:
            return existing
    return build_world_layers()


if __name__ == "__main__":
    paths = ensure_world_layers(force=True)
    for path in paths:
        print(path.relative_to(ASSETS_DIR))

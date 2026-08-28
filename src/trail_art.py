"""Pintura das fendas e o mundo contínuo da travessia floresta → clareira."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageStat

from src.config import (
    CROSSING_BLEND_PX,
    CROSSING_OVERHANG_PX,
    FOREST_FAR_GROUND_SRC_Y,
    GROUND_Y,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TRAIL_DRAW_Y,
    TRAIL_ORIGIN_X,
    TRAIL_WORLD_WIDTH,
)

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
PARALLAX_DIR = ASSETS_DIR / "parallax"
TRAIL_PATH = PARALLAX_DIR / "forest_trail.png"
CROSSING_PATH = PARALLAX_DIR / "forest_crossing.png"

PLAY_SOURCES = (
    PARALLAX_DIR / "forest_fendas_clean.png",
    PARALLAX_DIR / "forest_fendas.jpg",
    PARALLAX_DIR / "forest_fendas.png",
)
FOREST_NEAR = PARALLAX_DIR / "forest1.png"
FOREST_FAR = PARALLAX_DIR / "forest_far.png"


def _first_file(candidates: tuple[Path, ...]) -> Path | None:
    return next((p for p in candidates if p.is_file()), None)


def _cover_crop(src: Image.Image, tw: int, th: int) -> Image.Image:
    sw, sh = src.size
    scale = max(tw / sw, th / sh)
    size = (max(tw, int(round(sw * scale))), max(th, int(round(sh * scale))))
    resized = src.resize(size, Image.Resampling.LANCZOS)
    x0 = max(0, (resized.width - tw) // 2)
    y0 = max(0, (resized.height - th) // 2)
    return resized.crop((x0, y0, x0 + tw, y0 + th))


def _cover_align_ground(
    src: Image.Image,
    tw: int,
    th: int,
    ground_src_y: int,
    ground_dst_y: int,
) -> Image.Image:
    """Cover uniforme (sem distorcer) alinhando a linha do chão ao collider."""
    sw, sh = src.size
    scale = max(tw / sw, th / sh)
    nw, nh = int(round(sw * scale)), int(round(sh * scale))
    resized = src.resize((nw, nh), Image.Resampling.LANCZOS)
    gy = int(round(ground_src_y * scale))
    y0 = gy - ground_dst_y
    x0 = 0 if nw <= tw else 0
    x0 = max(0, min(max(0, nw - tw), x0))
    y0 = max(0, min(max(0, nh - th), y0))
    if nw < tw or nh < th:
        canvas = Image.new("RGB", (tw, th), (22, 36, 28))
        canvas.paste(resized, ((tw - nw) // 2, (th - nh) // 2))
        return canvas
    return resized.crop((x0, y0, x0 + tw, y0 + th))


def _hide_baked_ui(img: Image.Image) -> Image.Image:
    """Tapa a placa DESAFIO se a fonte ainda tiver o texto pintado."""
    w, h = img.size
    box_w, box_h = min(w, 340), min(h, 78)
    patch = img.crop((min(w - 1, 380), 0, min(w, 720), box_h))
    patch = patch.resize((box_w, box_h), Image.Resampling.LANCZOS).filter(ImageFilter.SMOOTH)
    out = img.copy()
    out.paste(patch, (0, 0))
    return out


def _gradient_mask(width: int, height: int, fade: int, top_fade: int) -> Image.Image:
    """Alpha: entra pela esquerda e pelo topo, para a pintura não cortar em linha."""
    fade = max(1, min(width, fade))
    top_fade = max(1, min(height, top_fade))
    hx = Image.new("L", (width, 1))
    hx.putdata([
        int(255 * (t * t * (3 - 2 * t))) if x < fade else 255
        for x in range(width)
        for t in (min(1.0, x / fade),)
    ])
    vx = Image.new("L", (1, height))
    vx.putdata([
        int(255 * (t * t * (3 - 2 * t))) if y < top_fade else 255
        for y in range(height)
        for t in (min(1.0, y / top_fade),)
    ])
    return ImageChops.multiply(
        hx.resize((width, height), Image.Resampling.BILINEAR),
        vx.resize((width, height), Image.Resampling.BILINEAR),
    )


def _overhang_mask(width: int, height: int, hold: int) -> Image.Image:
    """Opaco no começo (ainda floresta) e some para a direita sobre o penhasco."""
    hold = max(0, min(width - 1, hold))
    fade = max(1, width - hold)
    row = []
    for x in range(width):
        if x <= hold:
            row.append(255)
        else:
            t = (x - hold) / fade
            s = t * t * (3 - 2 * t)
            row.append(int(255 * (1.0 - s)))
    img = Image.new("L", (width, 1))
    img.putdata(row)
    return img.resize((width, height), Image.Resampling.BILINEAR)


def _harmonize_trail(trail: Image.Image, forest: Image.Image) -> Image.Image:
    """Aproxima temperatura e exposição da clareira à floresta, sem copiar estrutura."""
    sample = forest.resize((64, 64), Image.Resampling.BOX)
    mean = ImageStat.Stat(sample).mean
    veil = Image.new("RGB", trail.size, tuple(int(c) for c in mean[:3]))
    cooled = ImageEnhance.Color(trail).enhance(0.86)
    cooled = ImageEnhance.Contrast(cooled).enhance(0.92)
    cooled = ImageEnhance.Brightness(cooled).enhance(1.05)
    return Image.blend(cooled, veil, 0.16)


def build_trail_art() -> Path:
    play_src = _first_file(PLAY_SOURCES)
    if play_src is None:
        raise FileNotFoundError(
            "Este asset não existe atualmente no projeto: parallax/forest_fendas.jpg"
        )
    raw_play = Image.open(play_src).convert("RGB")
    play = _cover_crop(raw_play, SCREEN_WIDTH, SCREEN_HEIGHT)
    if play_src.name != "forest_fendas_clean.png":
        play = _hide_baked_ui(play)
    PARALLAX_DIR.mkdir(parents=True, exist_ok=True)
    play.save(TRAIL_PATH, "PNG")
    return TRAIL_PATH


def ensure_trail_art(force: bool = False) -> Path:
    play_src = _first_file(PLAY_SOURCES)
    if play_src is None:
        raise FileNotFoundError(
            "Este asset não existe atualmente no projeto: parallax/forest_fendas.jpg"
        )
    if not force and TRAIL_PATH.is_file():
        with Image.open(TRAIL_PATH) as im:
            ready = im.size == (SCREEN_WIDTH, SCREEN_HEIGHT) and im.mode == "RGB"
        if ready and TRAIL_PATH.stat().st_mtime >= play_src.stat().st_mtime:
            return TRAIL_PATH
    return build_trail_art()


def build_crossing_world() -> Path:
    """Monta o strip 2048×600: floresta contínua + clareira fundida, sem costura vertical."""
    ensure_trail_art()
    if not FOREST_NEAR.is_file():
        raise FileNotFoundError("Este asset não existe atualmente no projeto: parallax/forest1.png")

    near = Image.open(FOREST_NEAR).convert("RGB")
    left = _cover_crop(near, SCREEN_WIDTH, SCREEN_HEIGHT)

    world = Image.new("RGB", (TRAIL_WORLD_WIDTH, SCREEN_HEIGHT), (22, 36, 28))

    if FOREST_FAR.is_file():
        far = Image.open(FOREST_FAR).convert("RGB")
        far_strip = _cover_align_ground(
            far,
            TRAIL_WORLD_WIDTH,
            SCREEN_HEIGHT,
            FOREST_FAR_GROUND_SRC_Y,
            GROUND_Y,
        )
        world.paste(far_strip, (0, 0))
    else:
        world.paste(left, (0, 0))
        world.paste(left, (SCREEN_WIDTH, 0))

    world.paste(left, (0, 0))

    trail = Image.open(TRAIL_PATH).convert("RGB")
    trail = _harmonize_trail(trail, left)
    overlay = trail.convert("RGBA")
    overlay.putalpha(_gradient_mask(
        overlay.width,
        overlay.height,
        CROSSING_BLEND_PX,
        max(48, TRAIL_DRAW_Y // 3),
    ))
    world.paste(overlay, (TRAIL_ORIGIN_X, TRAIL_DRAW_Y), overlay)

    hang_w = CROSSING_OVERHANG_PX
    hang_hold = 80
    src_x = max(0, left.width - hang_w)
    hanging = left.crop((src_x, 0, left.width, left.height)).convert("RGBA")
    hanging.putalpha(_overhang_mask(hanging.width, hanging.height, hang_hold))
    world.paste(hanging, (TRAIL_ORIGIN_X - hang_hold, 0), hanging)

    PARALLAX_DIR.mkdir(parents=True, exist_ok=True)
    world.save(CROSSING_PATH, "PNG")
    return CROSSING_PATH


def _crossing_sources() -> list[Path]:
    play = _first_file(PLAY_SOURCES)
    out = [FOREST_NEAR, FOREST_FAR, TRAIL_PATH, Path(__file__), Path(__file__).with_name("config.py")]
    if play is not None:
        out.append(play)
    return [p for p in out if p.is_file()]


def ensure_crossing_world(force: bool = False) -> Path:
    ensure_trail_art(force=force)
    sources = _crossing_sources()
    code_mtime = Path(__file__).stat().st_mtime
    if not force and CROSSING_PATH.is_file() and sources:
        with Image.open(CROSSING_PATH) as im:
            ready = im.size == (TRAIL_WORLD_WIDTH, SCREEN_HEIGHT) and im.mode == "RGB"
        newest = max([p.stat().st_mtime for p in sources] + [code_mtime])
        if ready and CROSSING_PATH.stat().st_mtime >= newest:
            return CROSSING_PATH
    return build_crossing_world()

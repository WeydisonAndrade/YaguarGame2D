"""Pintura das fendas e o mundo contínuo: floresta → clareira → areia."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageStat

from src.config import (
    CROSSING_BLEND_PX,
    CROSSING_OVERHANG_PX,
    FOREST_WORLD_WIDTH,
    SAND_ART_GROUND_Y,
    SAND_ORIGIN_X,
    SAND_PLATFORMS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TRAIL_ART_GROUND_Y,
    TRAIL_DRAW_Y,
    TRAIL_ORIGIN_X,
    TRAIL_PLATFORMS,
)

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
PARALLAX_DIR = ASSETS_DIR / "parallax"
TRAIL_PATH = PARALLAX_DIR / "forest_trail.png"
CROSSING_PATH = PARALLAX_DIR / "forest_crossing.png"
SAND_PATH = PARALLAX_DIR / "forest_sand_fendas.png"

PLAY_SOURCES = (
    PARALLAX_DIR / "forest_fendas_clean.png",
    PARALLAX_DIR / "forest_fendas.jpg",
    PARALLAX_DIR / "forest_fendas.png",
)
FOREST_NEAR = PARALLAX_DIR / "forest1.png"
FOREST_FAR = PARALLAX_DIR / "forest_far.png"
FENDAS_FAR = PARALLAX_DIR / "forest_fendas_far.png"


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
    """Opaco no começo (ainda o bioma anterior) e some para a direita."""
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


def _harmonize_sand(sand: Image.Image, trail: Image.Image) -> Image.Image:
    """A areia esquenta o chão, mas o dossel não troca de quadro."""
    sample = trail.resize((64, 64), Image.Resampling.BOX)
    mean = ImageStat.Stat(sample).mean
    veil = Image.new("RGB", sand.size, tuple(int(c) for c in mean[:3]))
    graded = ImageEnhance.Color(sand).enhance(0.9)
    graded = ImageEnhance.Contrast(graded).enhance(0.96)
    return Image.blend(graded, veil, 0.12)


def _feather(im: Image.Image, pad: int = 16) -> Image.Image:
    """Suaviza as bordas de um recorte para colar como prop, sem corte quadrado."""
    im = im.convert("RGBA")
    w, h = im.size
    pad = max(1, min(pad, w // 2, h // 2))
    mask = Image.new("L", (w, h), 255)
    px = mask.load()
    for y in range(h):
        for x in range(w):
            d = min(x, y, w - 1 - x, h - 1 - y)
            if d < pad:
                px[x, y] = int(255 * (d / pad))
    alpha = im.split()[-1]
    im.putalpha(ImageChops.multiply(alpha, mask))
    return im


def _hfade(width: int, height: int, fade: int, reverse: bool = False) -> Image.Image:
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


def _shift_to_ground(src: Image.Image, art_ground_y: int) -> Image.Image:
    """Desce a pintura até o chão jogável, sem esticar árvore nem preencher com cor chapada."""
    src = src.convert("RGB")
    if src.size != (SCREEN_WIDTH, SCREEN_HEIGHT):
        src = _cover_crop(src, SCREEN_WIDTH, SCREEN_HEIGHT)
    dy = TRAIL_ART_GROUND_Y - art_ground_y
    if dy == 0:
        return src
    canvas = src.copy()
    if dy > 0:
        sky = src.crop((0, 0, src.width, min(24, src.height)))
        sky = sky.resize((src.width, dy), Image.Resampling.BILINEAR)
        canvas = Image.new("RGB", src.size)
        canvas.paste(sky, (0, 0))
        canvas.paste(src, (0, dy))
    return canvas


def _blur_horizontal_band(world: Image.Image, y: int, x0: int, x1: int, radius: float = 4.5) -> None:
    """Esconde o lábio horizontal da pintura deslocada — blur curto, sem smear."""
    band = 28
    y0 = max(0, y - band)
    y1 = min(world.height, y + band)
    if x1 - x0 < 8 or y1 - y0 < 8:
        return
    strip = world.crop((x0, y0, x1, y1))
    blur = strip.filter(ImageFilter.GaussianBlur(radius))
    h = strip.height
    cy = y - y0
    col = Image.new("L", (1, h))
    col.putdata([
        int(170 * max(0.0, 1.0 - abs(i - cy) / max(1.0, band)))
        for i in range(h)
    ])
    mask = col.resize(strip.size, Image.Resampling.BILINEAR)
    world.paste(Image.composite(blur, strip, mask), (x0, y0))


def _hang_previous(world: Image.Image, dest_x: int, hang_w: int, hang_hold: int) -> None:
    """A copa do trecho anterior atravessa a junta — um galho, não um espelho."""
    hang_w = min(hang_w, dest_x)
    if hang_w < 8:
        return
    hanging = world.crop((dest_x - hang_w, 0, dest_x, SCREEN_HEIGHT)).convert("RGBA")
    hanging.putalpha(_overhang_mask(hanging.width, hanging.height, hang_hold))
    world.paste(hanging, (dest_x - hang_hold, 0), hanging)


def _load_valley() -> Image.Image | None:
    src = FENDAS_FAR if FENDAS_FAR.is_file() else None
    if src is None:
        return None
    valley = _cover_crop(Image.open(src).convert("RGB"), SCREEN_WIDTH, SCREEN_HEIGHT)
    valley = ImageEnhance.Contrast(valley).enhance(0.78)
    valley = ImageEnhance.Color(valley).enhance(0.9)
    valley = ImageEnhance.Brightness(valley).enhance(1.06)
    return valley


def _dress_approach(world: Image.Image, forest: Image.Image) -> None:
    """Pedras extras e névoa crescente: floresta → terreno irregular → borda."""
    start = 700
    span = TRAIL_ORIGIN_X - start
    if span <= 0:
        return
    forest_part = world.crop((start, 0, TRAIL_ORIGIN_X, SCREEN_HEIGHT))
    mist = ImageEnhance.Color(forest_part).enhance(0.88)
    mist = ImageEnhance.Brightness(mist).enhance(1.07)
    mask = _hfade(span, SCREEN_HEIGHT, span)
    dressed = Image.composite(mist, forest_part, mask)
    world.paste(dressed, (start, 0))

    props = (
        ((410, 400, 560, 508), 680, 398, 0.94),
        ((668, 388, 830, 508), 798, 392, 1.08),
        ((250, 428, 340, 518), 910, 418, 0.82),
        ((740, 430, 860, 520), 860, 428, 0.9),
    )
    for box, dx, dy, scale in props:
        x0, y0, x1, y1 = box
        if x1 > forest.width or y1 > forest.height:
            continue
        chip = forest.crop((x0, y0, x1, y1))
        if scale != 1.0:
            nw = max(8, int(chip.width * scale))
            nh = max(8, int(chip.height * scale))
            chip = chip.resize((nw, nh), Image.Resampling.LANCZOS)
        chip = _feather(chip, pad=max(10, min(chip.width, chip.height) // 6))
        world.paste(chip, (dx, dy), chip)


def _open_to_valley(world: Image.Image, valley: Image.Image) -> None:
    """O vale começa a aparecer entre as árvores, antes da primeira fenda."""
    start = 760
    span = TRAIL_ORIGIN_X - start
    if span <= 0:
        return
    forest_part = world.crop((start, 0, TRAIL_ORIGIN_X, SCREEN_HEIGHT))
    valley_part = valley.crop((0, 0, span, SCREEN_HEIGHT))
    mask = _hfade(span, SCREEN_HEIGHT, span)
    mask = mask.point(lambda a: int(a * 0.42))
    blended = Image.composite(valley_part, forest_part, mask)
    world.paste(blended, (start, 0))


def _accent_ledges(world: Image.Image, platforms=TRAIL_PLATFORMS) -> None:
    """Clareia a grama e escurece o lábio — silhueta jogável, sem contorno de HUD."""
    for x, y, w, _h in platforms:
        top = max(0, y - 10)
        lip = min(SCREEN_HEIGHT, y + 8)
        if w < 8 or lip <= top:
            continue
        grass = world.crop((x, top, x + w, lip))
        grass = ImageEnhance.Brightness(grass).enhance(1.16)
        grass = ImageEnhance.Color(grass).enhance(1.08)
        world.paste(grass, (x, top))
        shade_top = min(SCREEN_HEIGHT, y + 6)
        shade_bot = min(SCREEN_HEIGHT, y + 26)
        if shade_bot > shade_top:
            shade = world.crop((x, shade_top, x + w, shade_bot))
            shade = ImageEnhance.Brightness(shade).enhance(0.78)
            world.paste(shade, (x, shade_top))


def _haze_gaps(world: Image.Image, valley: Image.Image | None) -> None:
    """Névoa nos vãos: quanto mais fundo o vale, menor o contraste."""
    plats = list(TRAIL_PLATFORMS)
    for prev, nxt in zip(plats, plats[1:]):
        gx0 = prev[0] + prev[2]
        gx1 = nxt[0]
        if gx1 - gx0 < 12:
            continue
        gap = world.crop((gx0, 0, gx1, SCREEN_HEIGHT))
        if valley is not None:
            vx = min(valley.width, max(0, gx0 - TRAIL_ORIGIN_X))
            vw = min(valley.width - vx, gx1 - gx0)
            if vw > 0:
                far = valley.crop((vx, 0, vx + vw, SCREEN_HEIGHT))
                far = ImageEnhance.Contrast(far).enhance(0.7)
                gap = Image.blend(gap, far, 0.28)
        gap = ImageEnhance.Contrast(gap).enhance(0.86)
        gap = ImageEnhance.Brightness(gap).enhance(1.05)
        world.paste(gap, (gx0, 0))


def _paste_play_art(
    world: Image.Image,
    art: Image.Image,
    dest_x: int,
    *,
    hang_w: int,
    hang_hold: int,
    fade: int,
    top_fade: int,
) -> None:
    """Cola a pintura na proporção original, com fade e copa do vizinho por cima."""
    _hang_previous(world, dest_x, hang_w, hang_hold)
    overlay = art.convert("RGBA")
    overlay.putalpha(_gradient_mask(overlay.width, overlay.height, fade, top_fade))
    world.paste(overlay, (dest_x, TRAIL_DRAW_Y), overlay)
    _blur_horizontal_band(world, TRAIL_DRAW_Y, dest_x, dest_x + art.width)


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


def _append_sand(world: Image.Image, valley: Image.Image | None, trail_ref: Image.Image) -> None:
    """Continua a clareira com a areia, sem esticar nem copiar copa."""
    if not SAND_PATH.is_file():
        raise FileNotFoundError(
            "Este asset não existe atualmente no projeto: parallax/forest_sand_fendas.png"
        )
    if valley is not None:
        world.paste(valley, (SAND_ORIGIN_X, 0))

    sand = _cover_crop(Image.open(SAND_PATH).convert("RGB"), SCREEN_WIDTH, SCREEN_HEIGHT)
    sand = _shift_to_ground(sand, SAND_ART_GROUND_Y)
    sand = _harmonize_sand(sand, trail_ref)
    _paste_play_art(
        world,
        sand,
        SAND_ORIGIN_X,
        hang_w=min(140, CROSSING_OVERHANG_PX),
        hang_hold=48,
        fade=min(CROSSING_BLEND_PX + 40, sand.width // 2),
        top_fade=128,
    )


def build_crossing_world() -> Path:
    """Monta o strip contínuo: floresta + vale + clareira + areia, sem tiling."""
    ensure_trail_art()
    if not FOREST_NEAR.is_file():
        raise FileNotFoundError("Este asset não existe atualmente no projeto: parallax/forest1.png")

    near = Image.open(FOREST_NEAR).convert("RGB")
    left = _cover_crop(near, SCREEN_WIDTH, SCREEN_HEIGHT)
    valley = _load_valley()

    world = Image.new("RGB", (FOREST_WORLD_WIDTH, SCREEN_HEIGHT), (22, 36, 28))
    if valley is not None:
        world.paste(valley, (TRAIL_ORIGIN_X, 0))
        world.paste(valley, (SAND_ORIGIN_X, 0))
    world.paste(left, (0, 0))
    _dress_approach(world, left)
    if valley is not None:
        _open_to_valley(world, valley)

    trail = Image.open(TRAIL_PATH).convert("RGB")
    trail = _harmonize_trail(trail, left)
    _paste_play_art(
        world,
        trail,
        TRAIL_ORIGIN_X,
        hang_w=CROSSING_OVERHANG_PX,
        hang_hold=80,
        fade=CROSSING_BLEND_PX,
        top_fade=max(88, TRAIL_DRAW_Y // 2),
    )

    _accent_ledges(world, TRAIL_PLATFORMS)
    _haze_gaps(world, valley)
    _append_sand(world, valley, trail)
    _accent_ledges(world, SAND_PLATFORMS)

    PARALLAX_DIR.mkdir(parents=True, exist_ok=True)
    world.save(CROSSING_PATH, "PNG")
    return CROSSING_PATH


def _crossing_sources() -> list[Path]:
    play = _first_file(PLAY_SOURCES)
    out = [FOREST_NEAR, FOREST_FAR, FENDAS_FAR, TRAIL_PATH, SAND_PATH, Path(__file__), Path(__file__).with_name("config.py")]
    if play is not None:
        out.append(play)
    return [p for p in out if p.is_file()]


def ensure_crossing_world(force: bool = False) -> Path:
    from src.layered_art import ensure_world_layers

    ensure_world_layers(force=force)
    ensure_trail_art(force=force)
    sources = _crossing_sources()
    code_mtime = Path(__file__).stat().st_mtime
    if not force and CROSSING_PATH.is_file() and sources:
        with Image.open(CROSSING_PATH) as im:
            ready = im.size == (FOREST_WORLD_WIDTH, SCREEN_HEIGHT) and im.mode == "RGB"
        newest = max([p.stat().st_mtime for p in sources] + [code_mtime])
        if ready and CROSSING_PATH.stat().st_mtime >= newest:
            return CROSSING_PATH
    return build_crossing_world()

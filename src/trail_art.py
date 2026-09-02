"""Pintura das fendas e o mundo contínuo: floresta → clareira → areia.

O erro de 'duas imagens unidas' vinha de colar a clareira deslocada (céu no meio
da tela), tapar o topo com um vale de outra pintura e empilhar fades. Aqui cada
clareira é a própria arte, reenquadrada no chão jogável, e a junta é só um
crossfade curto entre dois quadros completos.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageStat

from src.config import (
    FOREST_WORLD_WIDTH,
    GROUND_Y,
    SAND_ART_GROUND_Y,
    SAND_ORIGIN_X,
    SAND_PLATFORMS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
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
FENDAS_FAR = PARALLAX_DIR / "forest_fendas_far.png"

# No PNG 1536×1024 da clareira, o lábio da grama (medida na arte).
TRAIL_SRC_GROUND_Y = 457


def _first_file(candidates: tuple[Path, ...]) -> Path | None:
    """Devolve o primeiro caminho da lista que existe em disco."""
    return next((p for p in candidates if p.is_file()), None)


def _cover_crop(src: Image.Image, tw: int, th: int) -> Image.Image:
    """Escala a pintura no modo cover e recorta o centro no tamanho alvo."""
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


def _hfade(width: int, height: int, fade: int, reverse: bool = False) -> Image.Image:
    """Máscara horizontal suave (ease in-out): entra pela esquerda, ou pela direita se reverse."""
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


def _frame_to_ground(src: Image.Image, src_ground_y: int) -> Image.Image:
    """Uma pintura só: céu no topo da tela, chão na linha jogável, largura da colisão.

    Estica só na vertical o bastante para o lábio da grama cair em GROUND_Y.
    Não cola segundo quadro, não deixa faixa preta, não desloca o céu para o meio.
    """
    src = src.convert("RGB")
    scale_x = SCREEN_WIDTH / src.width
    nh = max(1, int(round(src.height * scale_x)))
    scaled = src.resize((SCREEN_WIDTH, nh), Image.Resampling.LANCZOS)
    gy = max(1, int(round(src_ground_y * scale_x)))
    scale_y = GROUND_Y / gy
    fitted = scaled.resize(
        (SCREEN_WIDTH, max(SCREEN_HEIGHT, int(round(scaled.height * scale_y)))),
        Image.Resampling.LANCZOS,
    )
    return fitted.crop((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))


def _match_edge(art: Image.Image, neighbor: Image.Image) -> Image.Image:
    """Ajuste leve de exposição na junta, sem véu cinza em cima da clareira inteira."""
    if neighbor.width < 8 or neighbor.height < 8:
        return art
    sample_n = neighbor.resize((32, 32), Image.Resampling.BOX)
    sample_a = art.crop((0, 0, min(80, art.width), art.height)).resize((32, 32), Image.Resampling.BOX)
    mn = ImageStat.Stat(sample_n).mean
    ma = ImageStat.Stat(sample_a).mean
    veil = Image.new("RGB", art.size, tuple(int(c) for c in mn[:3]))
    strength = min(0.22, sum(abs(a - b) for a, b in zip(mn[:3], ma[:3])) / 700.0)
    graded = Image.blend(art, veil, strength)
    mask = _hfade(art.width, art.height, min(160, art.width // 3), reverse=True)
    return Image.composite(graded, art, mask)


def _crossfade(world: Image.Image, art: Image.Image, dest_x: int, fade: int) -> None:
    """Cola o quadro completo e mistura só a costura, com pixels reais dos dois lados."""
    fade = max(24, min(fade, dest_x, art.width, world.width - dest_x))
    prev = world.crop((dest_x - fade, 0, dest_x, SCREEN_HEIGHT))
    sample = art.crop((0, 0, min(70, art.width), art.height)).resize((32, 32), Image.Resampling.BOX)
    mean = ImageStat.Stat(sample).mean
    veil = Image.new("RGB", prev.size, tuple(int(c) for c in mean[:3]))
    outgoing = Image.blend(prev, veil, 0.34)
    outgoing = ImageEnhance.Color(outgoing).enhance(0.86)
    outgoing = ImageEnhance.Brightness(outgoing).enhance(0.90)
    out_mask = _hfade(prev.width, prev.height, prev.width)
    world.paste(Image.composite(outgoing, prev, out_mask), (dest_x - fade, 0))

    prev = world.crop((dest_x - fade, 0, dest_x, SCREEN_HEIGHT))
    art = _match_edge(art.convert("RGB"), prev)
    world.paste(art, (dest_x, 0))

    mix = min(20, fade)
    left = world.crop((dest_x - mix, 0, dest_x, SCREEN_HEIGHT))
    right = world.crop((dest_x, 0, dest_x + mix, SCREEN_HEIGHT))
    world.paste(Image.blend(left, right, 0.42), (dest_x - mix, 0))
    world.paste(Image.blend(right, left, 0.42), (dest_x, 0))

    x0 = dest_x - fade
    x1 = dest_x + fade
    strip = world.crop((x0, 0, x1, SCREEN_HEIGHT))
    blur = strip.filter(ImageFilter.GaussianBlur(3.6))
    w, h = strip.size
    cx = dest_x - x0
    hx = Image.new("L", (w, 1))
    hx.putdata([
        int(210 * max(0.0, 1.0 - abs(i - cx) / max(1.0, fade)))
        for i in range(w)
    ])
    mask = hx.resize((w, h), Image.Resampling.BILINEAR)
    world.paste(Image.composite(blur, strip, mask), (x0, 0))


def _load_valley() -> Image.Image | None:
    """Carrega o vale distante usado só no fundo das fendas, não como céu da clareira."""
    if not FENDAS_FAR.is_file():
        return None
    valley = _cover_crop(Image.open(FENDAS_FAR).convert("RGB"), SCREEN_WIDTH, SCREEN_HEIGHT)
    valley = ImageEnhance.Contrast(valley).enhance(0.78)
    valley = ImageEnhance.Color(valley).enhance(0.9)
    valley = ImageEnhance.Brightness(valley).enhance(1.06)
    return valley


def _haze_gaps(world: Image.Image, valley: Image.Image | None, platforms=TRAIL_PLATFORMS) -> None:
    """Névoa nos vãos da clareira e da areia; o vale se repete se o mundo for mais largo."""
    plats = list(platforms)
    for prev, nxt in zip(plats, plats[1:]):
        gx0 = prev[0] + prev[2]
        gx1 = nxt[0]
        if gx1 - gx0 < 12:
            continue
        gap = world.crop((gx0, 0, gx1, SCREEN_HEIGHT))
        if valley is not None and valley.width > 0:
            remaining = gx1 - gx0
            ox = 0
            while remaining > 0:
                vx = (gx0 + ox) % valley.width
                vw = min(valley.width - vx, remaining)
                far = valley.crop((vx, 0, vx + vw, SCREEN_HEIGHT))
                far = ImageEnhance.Contrast(far).enhance(0.7)
                piece = gap.crop((ox, 0, ox + vw, SCREEN_HEIGHT))
                gap.paste(Image.blend(piece, far, 0.18), (ox, 0))
                ox += vw
                remaining -= vw
        gap = ImageEnhance.Contrast(gap).enhance(0.92)
        world.paste(gap, (gx0, 0))


def build_trail_art() -> Path:
    """Gera forest_trail.png: a clareira inteira, chão alinhado, céu da própria pintura."""
    play_src = _first_file(PLAY_SOURCES)
    if play_src is None:
        raise FileNotFoundError(
            "Este asset não existe atualmente no projeto: parallax/forest_fendas.jpg"
        )
    raw = Image.open(play_src).convert("RGB")
    if play_src.name == "forest_fendas_clean.png":
        play = _frame_to_ground(raw, TRAIL_SRC_GROUND_Y)
    else:
        play = _cover_crop(raw, SCREEN_WIDTH, SCREEN_HEIGHT)
        play = _hide_baked_ui(play)
        play = _frame_to_ground(play, int(SCREEN_HEIGHT * 0.44))
    PARALLAX_DIR.mkdir(parents=True, exist_ok=True)
    play.save(TRAIL_PATH, "PNG")
    return TRAIL_PATH


def ensure_trail_art(force: bool = False) -> Path:
    """Reconstrói a pintura da clareira só se o arquivo estiver ausente ou desatualizado."""
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


def _append_sand(world: Image.Image) -> None:
    """A areia é o quadro seguinte: mesma altura de chão, crossfade na junta."""
    if not SAND_PATH.is_file():
        raise FileNotFoundError(
            "Este asset não existe atualmente no projeto: parallax/forest_sand_fendas.png"
        )
    sand = Image.open(SAND_PATH).convert("RGB")
    if sand.size != (SCREEN_WIDTH, SCREEN_HEIGHT):
        sand = _cover_crop(sand, SCREEN_WIDTH, SCREEN_HEIGHT)
    sand = _frame_to_ground(sand, SAND_ART_GROUND_Y)
    _crossfade(world, sand, SAND_ORIGIN_X, 88)


def build_crossing_world() -> Path:
    """Monta o strip: três telas completas, juntas em crossfade, sem carimbo de vale no céu."""
    ensure_trail_art(force=True)
    if not FOREST_NEAR.is_file():
        raise FileNotFoundError("Este asset não existe atualmente no projeto: parallax/forest1.png")

    left = _cover_crop(Image.open(FOREST_NEAR).convert("RGB"), SCREEN_WIDTH, SCREEN_HEIGHT)
    valley = _load_valley()
    trail = Image.open(TRAIL_PATH).convert("RGB")

    world = Image.new("RGB", (FOREST_WORLD_WIDTH, SCREEN_HEIGHT), (22, 36, 28))
    world.paste(left, (0, 0))
    _crossfade(world, trail, TRAIL_ORIGIN_X, 110)
    _haze_gaps(world, valley, TRAIL_PLATFORMS)
    _append_sand(world)
    _haze_gaps(world, valley, SAND_PLATFORMS)

    PARALLAX_DIR.mkdir(parents=True, exist_ok=True)
    world.save(CROSSING_PATH, "PNG")
    return CROSSING_PATH


def _crossing_sources() -> list[Path]:
    """Arquivos cuja data manda reconstruir o strip da travessia."""
    play = _first_file(PLAY_SOURCES)
    out = [
        FOREST_NEAR,
        FENDAS_FAR,
        TRAIL_PATH,
        SAND_PATH,
        Path(__file__),
        Path(__file__).with_name("config.py"),
    ]
    if play is not None:
        out.append(play)
    return [p for p in out if p.is_file()]


def ensure_crossing_world(force: bool = False) -> Path:
    """Garante forest_crossing.png no tamanho do mundo; reconstrói se a arte ou o código mudou."""
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

"""Gerador profissional de sprites 2D (Pillow + Pygame).

Pipeline:
  1. Desenha em alta resolução (supersampling 4x) com camadas RGBA.
  2. Aplica gradientes, auras e sombreamento.
  3. Reduz com interpolação LANCZOS (antialiasing).
  4. Converte para Surface SRCALPHA e grava PNG transparente em assets/.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

import pygame
from PIL import Image, ImageDraw, ImageFilter

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
SCALE = 4


# ---------------------------------------------------------------------------
# Paletas
# ---------------------------------------------------------------------------
SKIN_LIGHT = (224, 176, 132, 255)
SKIN_MID = (194, 138, 96, 255)
SKIN_SHADOW = (132, 82, 52, 255)
PAINT_RED = (176, 28, 32, 255)
PAINT_DARK = (110, 12, 18, 255)
GOLD = (218, 168, 52, 255)
GOLD_DEEP = (156, 104, 24, 255)
FEATHER_RED = (168, 36, 36, 255)
WOOD = (122, 74, 38, 255)
WOOD_DARK = (78, 44, 22, 255)
STONE = (176, 178, 186, 255)
STONE_EDGE = (92, 96, 104, 255)

BEAST_DARK = (28, 16, 28, 255)
BEAST_MID = (52, 28, 54, 255)
BEAST_PURPLE = (108, 42, 128, 255)
CORRUPT_RED = (220, 28, 36, 255)

ONCA_BLACK = (12, 10, 14, 255)
ONCA_BODY = (22, 18, 26, 255)
ONCA_NEON = (148, 64, 220, 255)
ONCA_CRIMSON = (196, 16, 38, 255)

MAP_FUR = (78, 52, 34, 255)
MAP_FUR_DARK = (42, 30, 22, 255)
MAP_FUR_GRAY = (92, 84, 74, 255)
MAP_EYE = (220, 18, 24, 255)

LEAF = (46, 168, 72, 255)
LEAF_DARK = (22, 98, 48, 255)
LEAF_LIGHT = (118, 214, 96, 255)
HERB_GOLD = (240, 196, 64, 255)


# ---------------------------------------------------------------------------
# Núcleo gráfico
# ---------------------------------------------------------------------------
def _lerp(a: float, b: float, t: float) -> float:
    """Interpolação linear entre a e b."""
    return a + (b - a) * t


def _lerp_rgba(c0: tuple, c1: tuple, t: float) -> tuple[int, int, int, int]:
    t = max(0.0, min(1.0, t))
    return tuple(int(_lerp(c0[i], c1[i], t)) for i in range(4))


def _blank(w: int, h: int) -> Image.Image:
    """Canvas transparente na resolução de trabalho (w*SCALE × h*SCALE)."""
    return Image.new("RGBA", (w * SCALE, h * SCALE), (0, 0, 0, 0))


def _px(value: float) -> int:
    return int(round(value * SCALE))


def _composite(base: Image.Image, *layers: Image.Image) -> Image.Image:
    out = base.copy()
    for layer in layers:
        if layer is not None:
            out = Image.alpha_composite(out, layer)
    return out


def _finish(img: Image.Image, w: int, h: int) -> Image.Image:
    """Antialiasing por blur leve + interpolação LANCZOS na redução."""
    smoothed = img.filter(ImageFilter.GaussianBlur(radius=0.45))
    return smoothed.resize((w, h), Image.Resampling.LANCZOS)


def _soft_mask_ellipse(size: tuple[int, int], bbox: tuple[int, int, int, int], blur: float = 0.8) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).ellipse(bbox, fill=255)
    if blur > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(radius=blur * SCALE / 2))
    return mask


def _soft_mask_polygon(size: tuple[int, int], points: list[tuple[int, int]], blur: float = 0.6) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).polygon(points, fill=255)
    if blur > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(radius=blur * SCALE / 2))
    return mask


def _vertical_gradient(size: tuple[int, int], c0: tuple, c1: tuple, bbox: tuple[int, int, int, int] | None = None) -> Image.Image:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    pixels = layer.load()
    x0, y0, x1, y1 = bbox if bbox else (0, 0, size[0], size[1])
    h = max(1, y1 - y0)
    for y in range(max(0, y0), min(size[1], y1)):
        color = _lerp_rgba(c0, c1, (y - y0) / h)
        for x in range(max(0, x0), min(size[0], x1)):
            pixels[x, y] = color
    return layer


def _radial_gradient(size: tuple[int, int], center: tuple[int, int], radius: float, inner: tuple, outer: tuple) -> Image.Image:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    pixels = layer.load()
    cx, cy = center
    r = max(1.0, radius)
    x0 = max(0, int(cx - r))
    y0 = max(0, int(cy - r))
    x1 = min(size[0], int(cx + r) + 1)
    y1 = min(size[1], int(cy + r) + 1)
    for y in range(y0, y1):
        dy = y - cy
        for x in range(x0, x1):
            dx = x - cx
            t = math.hypot(dx, dy) / r
            if t <= 1.0:
                # smoothstep para falloff mais orgânico
                t = t * t * (3.0 - 2.0 * t)
                pixels[x, y] = _lerp_rgba(inner, outer, t)
    return layer


def _fill_masked(size: tuple[int, int], fill: Image.Image, mask: Image.Image) -> Image.Image:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    layer.paste(fill, (0, 0), mask)
    return layer


def _ellipse_layer(size: tuple[int, int], bbox: tuple, top: tuple, bottom: tuple, blur: float = 0.7) -> Image.Image:
    mask = _soft_mask_ellipse(size, bbox, blur)
    fill = _vertical_gradient(size, top, bottom, bbox)
    return _fill_masked(size, fill, mask)


def _polygon_layer(size: tuple[int, int], points: list[tuple[int, int]], top: tuple, bottom: tuple, blur: float = 0.55) -> Image.Image:
    mask = _soft_mask_polygon(size, points, blur)
    ys = [p[1] for p in points]
    bbox = (min(p[0] for p in points), min(ys), max(p[0] for p in points), max(ys))
    fill = _vertical_gradient(size, top, bottom, bbox)
    return _fill_masked(size, fill, mask)


def _glow(size: tuple[int, int], mask: Image.Image, color: tuple, blur: float, strength: float = 1.0) -> Image.Image:
    tint = Image.new("RGBA", size, color)
    colored = _fill_masked(size, tint, mask)
    blurred = colored.filter(ImageFilter.GaussianBlur(radius=blur * SCALE))
    if strength >= 1.0:
        return blurred
    faded = Image.new("RGBA", size, (0, 0, 0, 0))
    return Image.blend(faded, blurred, max(0.0, min(1.0, strength)))


def _shadow(size: tuple[int, int], cx: int, cy: int, rw: int, rh: int) -> Image.Image:
    return _radial_gradient(
        size,
        (cx, cy),
        max(rw, rh),
        (0, 0, 0, 110),
        (0, 0, 0, 0),
    )


def _to_pygame(img: Image.Image) -> pygame.Surface:
    raw = pygame.image.fromstring(img.tobytes(), img.size, "RGBA")
    surf = pygame.Surface(img.size, pygame.SRCALPHA)
    surf.blit(raw, (0, 0))
    return surf


def _save(img: Image.Image, filename: str) -> None:
    """Grava PNG com canal alpha em assets/."""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    path = ASSETS_DIR / filename
    surf = _to_pygame(img)
    # Grava via Pillow para preservar alpha com fidelidade
    view = pygame.image.tostring(surf, "RGBA")
    Image.frombytes("RGBA", surf.get_size(), view).save(path, "PNG")


# ---------------------------------------------------------------------------
# player.png — Guerreiro Yáguar 64x64
# ---------------------------------------------------------------------------
def _make_feather(length: int, width: int, tip: tuple, base: tuple) -> Image.Image:
    feather = Image.new("RGBA", (width, length), (0, 0, 0, 0))
    mask = Image.new("L", (width, length), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.polygon(
        [
            (width // 2, 0),
            (width - 1, int(length * 0.42)),
            (int(width * 0.62), length - 1),
            (int(width * 0.38), length - 1),
            (1, int(length * 0.42)),
        ],
        fill=255,
    )
    mask = mask.filter(ImageFilter.GaussianBlur(radius=0.9))
    fill = _vertical_gradient((width, length), tip, base)
    feather.paste(fill, (0, 0), mask)
    shaft = ImageDraw.Draw(feather)
    shaft.line([(width // 2, 3), (width // 2, length - 4)], fill=(90, 50, 20, 160), width=max(1, width // 12))
    return feather


def _stamp_rotated(dest: Image.Image, sprite: Image.Image, attach: tuple[int, int], angle: float) -> Image.Image:
    """Cola um sprite rotacionado em torno da base (caule da pena)."""
    pad = max(sprite.size) * 2 + 8
    canvas = Image.new("RGBA", (pad, pad), (0, 0, 0, 0))
    cx, cy = pad // 2, pad // 2
    canvas.paste(sprite, (cx - sprite.width // 2, cy - sprite.height), sprite)
    rotated = canvas.rotate(-angle, resample=Image.Resampling.BICUBIC, center=(cx, cy))
    tmp = Image.new("RGBA", dest.size, (0, 0, 0, 0))
    tmp.paste(rotated, (attach[0] - cx, attach[1] - cy), rotated)
    return Image.alpha_composite(dest, tmp)


def create_player() -> Image.Image:
    """Placeholder 64×64 do guerreiro (usado se o sprite artesanal não existir)."""
    w = h = 64
    size = (w * SCALE, h * SCALE)
    img = _blank(w, h)
    img = _composite(img, _shadow(size, _px(31), _px(59), _px(15), _px(5)))

    # Cocar em leque (atrás da cabeça)
    headdress = Image.new("RGBA", size, (0, 0, 0, 0))
    attach = (_px(31), _px(16))
    feather_specs = (
        (_px(22), _px(6), GOLD, GOLD_DEEP, -68),
        (_px(25), _px(7), FEATHER_RED, GOLD_DEEP, -42),
        (_px(28), _px(7), GOLD, FEATHER_RED, -18),
        (_px(30), _px(8), FEATHER_RED, GOLD, 0),
        (_px(28), _px(7), GOLD, FEATHER_RED, 18),
        (_px(25), _px(7), FEATHER_RED, GOLD_DEEP, 42),
        (_px(22), _px(6), GOLD, GOLD_DEEP, 68),
    )
    for length, width, tip, base, angle in feather_specs:
        headdress = _stamp_rotated(headdress, _make_feather(length, width, tip, base), attach, angle)
    img = _composite(img, headdress)

    # Lança
    img = _composite(
        img,
        _polygon_layer(
            size,
            [(_px(45), _px(14)), (_px(48), _px(16)), (_px(40), _px(58)), (_px(37), _px(56))],
            WOOD,
            WOOD_DARK,
            blur=0.35,
        ),
        _polygon_layer(
            size,
            [(_px(46), _px(8)), (_px(58), _px(4)), (_px(50), _px(18)), (_px(44), _px(14))],
            STONE,
            STONE_EDGE,
            blur=0.3,
        ),
    )

    # Corpo
    img = _composite(
        img,
        _ellipse_layer(size, (_px(23), _px(45), _px(30), _px(58)), SKIN_MID, SKIN_SHADOW, blur=0.55),
        _ellipse_layer(size, (_px(32), _px(45), _px(39), _px(58)), SKIN_MID, SKIN_SHADOW, blur=0.55),
        _ellipse_layer(size, (_px(21), _px(41), _px(42), _px(50)), (96, 52, 30, 255), (58, 30, 16, 255), blur=0.6),
        _ellipse_layer(size, (_px(21), _px(27), _px(42), _px(47)), SKIN_LIGHT, SKIN_SHADOW, blur=0.85),
        _ellipse_layer(size, (_px(15), _px(29), _px(24), _px(45)), SKIN_MID, SKIN_SHADOW, blur=0.6),
        _ellipse_layer(size, (_px(39), _px(27), _px(50), _px(43)), SKIN_LIGHT, SKIN_SHADOW, blur=0.6),
    )

    # Colar
    necklace = Image.new("RGBA", size, (0, 0, 0, 0))
    nd = ImageDraw.Draw(necklace)
    nd.arc((_px(23), _px(30), _px(40), _px(42)), 10, 170, fill=GOLD, width=_px(1.2))
    necklace = necklace.filter(ImageFilter.GaussianBlur(radius=0.25 * SCALE))
    img = _composite(img, necklace)

    # Cabeça
    img = _composite(
        img,
        _ellipse_layer(size, (_px(22), _px(14), _px(41), _px(34)), SKIN_LIGHT, SKIN_SHADOW, blur=0.8),
        _radial_gradient(size, (_px(27), _px(24)), _px(5), (232, 176, 136, 80), (232, 176, 136, 0)),
    )

    paint = Image.new("RGBA", size, (0, 0, 0, 0))
    p = ImageDraw.Draw(paint)
    p.line([(_px(24), _px(22)), (_px(29), _px(25))], fill=PAINT_RED, width=_px(1.4))
    p.line([(_px(39), _px(22)), (_px(34), _px(25))], fill=PAINT_RED, width=_px(1.4))
    p.line([(_px(25), _px(27)), (_px(29), _px(26))], fill=PAINT_DARK, width=_px(1.1))
    p.line([(_px(38), _px(27)), (_px(34), _px(26))], fill=PAINT_DARK, width=_px(1.1))
    p.arc((_px(24), _px(18), _px(39), _px(28)), 200, 340, fill=PAINT_RED, width=_px(1.2))
    paint = paint.filter(ImageFilter.GaussianBlur(radius=0.28 * SCALE))
    img = _composite(img, paint)

    eyes = Image.new("RGBA", size, (0, 0, 0, 0))
    ed = ImageDraw.Draw(eyes)
    ed.ellipse((_px(26), _px(21), _px(29), _px(24)), fill=(26, 16, 12, 255))
    ed.ellipse((_px(34), _px(21), _px(37), _px(24)), fill=(26, 16, 12, 255))
    img = _composite(img, eyes)

    band = _ellipse_layer(size, (_px(23), _px(13), _px(40), _px(18)), GOLD, GOLD_DEEP, blur=0.35)
    img = _composite(img, band)
    return _finish(img, w, h)


# ---------------------------------------------------------------------------
# enemy_beast.png — Anta/Javali Corrompido 48x48
# ---------------------------------------------------------------------------
def create_enemy_beast() -> Image.Image:
    """Placeholder da besta corrompida."""
    w = h = 48
    size = (w * SCALE, h * SCALE)
    img = _blank(w, h)
    img = _composite(img, _shadow(size, _px(23), _px(43), _px(15), _px(5)))
    img = _composite(img, _radial_gradient(size, (_px(25), _px(24)), _px(19), (130, 24, 150, 60), (30, 0, 50, 0)))

    img = _composite(
        img,
        _ellipse_layer(size, (_px(6), _px(17), _px(38), _px(38)), BEAST_MID, BEAST_DARK, blur=0.95),
        _ellipse_layer(size, (_px(12), _px(11), _px(30), _px(24)), (86, 40, 102, 255), BEAST_DARK, blur=0.75),
        _ellipse_layer(size, (_px(27), _px(15), _px(44), _px(31)), BEAST_MID, BEAST_DARK, blur=0.7),
        _ellipse_layer(size, (_px(37), _px(20), _px(48), _px(29)), (74, 38, 70, 255), BEAST_DARK, blur=0.45),
    )

    for box in (
        (_px(11), _px(33), _px(16), _px(44)),
        (_px(18), _px(34), _px(23), _px(45)),
        (_px(26), _px(33), _px(31), _px(44)),
        (_px(32), _px(34), _px(37), _px(45)),
    ):
        img = _composite(img, _ellipse_layer(size, box, BEAST_MID, BEAST_DARK, blur=0.35))

    img = _composite(
        img,
        _polygon_layer(
            size,
            [(_px(41), _px(26)), (_px(47), _px(33)), (_px(40), _px(28))],
            (236, 226, 208, 255),
            (168, 156, 138, 255),
            blur=0.2,
        ),
    )

    veins = Image.new("RGBA", size, (0, 0, 0, 0))
    vd = ImageDraw.Draw(veins)
    vd.line([(_px(14), _px(22)), (_px(23), _px(26)), (_px(20), _px(33))], fill=(168, 78, 210, 170), width=_px(1.15))
    vd.line([(_px(18), _px(16)), (_px(27), _px(19))], fill=(140, 56, 186, 140), width=_px(0.9))
    img = _composite(img, veins.filter(ImageFilter.GaussianBlur(radius=0.35 * SCALE)))

    eye_box = (_px(33), _px(17), _px(40), _px(23))
    eye_mask = _soft_mask_ellipse(size, eye_box, blur=0.25)
    img = _composite(
        img,
        _glow(size, eye_mask, (255, 36, 48, 230), blur=2.4, strength=1.0),
        _ellipse_layer(size, eye_box, CORRUPT_RED, (80, 0, 10, 255), blur=0.2),
        _ellipse_layer(size, (_px(35), _px(18), _px(38), _px(21)), (255, 180, 170, 220), (255, 80, 80, 0), blur=0.15),
    )
    return _finish(img, w, h)


# ---------------------------------------------------------------------------
# boss_onca.png — Espírito da Onça Negra 80x80
# ---------------------------------------------------------------------------
def create_boss_onca() -> Image.Image:
    """Placeholder da onça (fallback; o jogo usa assets/onca/)."""
    w = h = 80
    size = (w * SCALE, h * SCALE)
    img = _blank(w, h)
    img = _composite(img, _shadow(size, _px(42), _px(71), _px(22), _px(6)))
    img = _composite(img, _radial_gradient(size, (_px(44), _px(40)), _px(32), (88, 18, 150, 42), (10, 0, 20, 0)))

    # Cauda em elipses encadeadas
    tail_boxes = (
        (_px(10), _px(40), _px(22), _px(50)),
        (_px(6), _px(30), _px(18), _px(42)),
        (_px(8), _px(20), _px(18), _px(32)),
        (_px(12), _px(14), _px(20), _px(24)),
    )
    for box in tail_boxes:
        img = _composite(img, _ellipse_layer(size, box, ONCA_BODY, ONCA_BLACK, blur=0.55))

    img = _composite(
        img,
        _ellipse_layer(size, (_px(18), _px(32), _px(64), _px(58)), ONCA_BODY, ONCA_BLACK, blur=1.05),
        _ellipse_layer(size, (_px(20), _px(36), _px(42), _px(56)), (40, 30, 50, 255), ONCA_BLACK, blur=0.75),
        _ellipse_layer(size, (_px(50), _px(20), _px(74), _px(44)), ONCA_BODY, ONCA_BLACK, blur=0.8),
        _ellipse_layer(size, (_px(62), _px(28), _px(77), _px(40)), (38, 30, 44, 255), ONCA_BLACK, blur=0.45),
        _polygon_layer(size, [(_px(54), _px(22)), (_px(52), _px(10)), (_px(61), _px(18))], ONCA_BODY, ONCA_BLACK, blur=0.3),
        _polygon_layer(size, [(_px(64), _px(20)), (_px(69), _px(9)), (_px(73), _px(21))], ONCA_BLACK, ONCA_BODY, blur=0.3),
        _polygon_layer(size, [(_px(55), _px(18)), (_px(54), _px(13)), (_px(59), _px(18))], (92, 40, 140, 200), (40, 16, 60, 0), blur=0.2),
    )

    for box in (
        (_px(24), _px(50), _px(32), _px(68)),
        (_px(34), _px(52), _px(42), _px(70)),
        (_px(48), _px(51), _px(56), _px(68)),
        (_px(56), _px(48), _px(63), _px(64)),
    ):
        img = _composite(img, _ellipse_layer(size, box, ONCA_BODY, ONCA_BLACK, blur=0.4))

    paws = Image.new("RGBA", size, (0, 0, 0, 0))
    pd = ImageDraw.Draw(paws)
    for bx, by in ((_px(25), _px(66)), (_px(35), _px(68)), (_px(49), _px(66)), (_px(57), _px(62))):
        pd.polygon([(bx, by), (bx + _px(2), by + _px(7)), (bx + _px(4), by)], fill=(232, 224, 214, 235))
        pd.polygon([(bx + _px(4), by), (bx + _px(6), by + _px(8)), (bx + _px(8), by)], fill=(240, 232, 220, 235))
        pd.polygon([(bx + _px(7), by + _px(1)), (bx + _px(10), by + _px(6)), (bx + _px(11), by)], fill=(220, 210, 200, 220))
    img = _composite(img, paws.filter(ImageFilter.GaussianBlur(radius=0.22 * SCALE)))

    spots = Image.new("RGBA", size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(spots)
    for box in (
        (_px(28), _px(38), _px(34), _px(43)),
        (_px(38), _px(34), _px(45), _px(40)),
        (_px(46), _px(42), _px(52), _px(47)),
    ):
        sd.ellipse(box, fill=(90, 36, 150, 90))
    img = _composite(img, spots.filter(ImageFilter.GaussianBlur(radius=0.5 * SCALE)))

    back_light = _ellipse_layer(size, (_px(22), _px(32), _px(58), _px(42)), (150, 70, 220, 70), (20, 0, 40, 0), blur=1.1)
    img = _composite(img, back_light)

    for box in ((_px(60), _px(25), _px(66), _px(30)), (_px(67), _px(26), _px(72), _px(31))):
        emask = _soft_mask_ellipse(size, box, blur=0.18)
        img = _composite(
            img,
            _glow(size, emask, (255, 20, 46, 230), blur=1.7, strength=0.92),
            _ellipse_layer(size, box, ONCA_CRIMSON, (70, 0, 14, 255), blur=0.18),
        )
    return _finish(img, w, h)


# ---------------------------------------------------------------------------
# boss_mapinguari.png — Mapinguari 128x128
# ---------------------------------------------------------------------------
def _fur_tufts(size: tuple[int, int], rng: random.Random) -> Image.Image:
    fur = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(fur)
    for _ in range(220):
        x = rng.randint(_px(28), _px(100))
        y = rng.randint(_px(22), _px(108))
        rw = rng.randint(_px(3), _px(9))
        rh = rng.randint(_px(6), _px(14))
        tone = rng.choice((MAP_FUR, MAP_FUR_DARK, MAP_FUR_GRAY, (64, 48, 36, 220)))
        draw.ellipse((x, y, x + rw, y + rh), fill=tone)
    return fur.filter(ImageFilter.GaussianBlur(radius=0.55 * SCALE))


def create_boss_mapinguari() -> Image.Image:
    """Placeholder do Mapinguari (fallback; o jogo usa assets/mapinguari/)."""
    w = h = 128
    size = (w * SCALE, h * SCALE)
    rng = random.Random(13)
    img = _blank(w, h)
    img = _composite(img, _shadow(size, _px(64), _px(118), _px(36), _px(10)))

    haze = _radial_gradient(size, (_px(64), _px(70)), _px(58), (40, 10, 10, 40), (0, 0, 0, 0))
    img = _composite(img, haze)

    # Braços
    img = _composite(
        img,
        _ellipse_layer(size, (_px(8), _px(48), _px(36), _px(108)), MAP_FUR, MAP_FUR_DARK, blur=1.1),
        _ellipse_layer(size, (_px(92), _px(48), _px(120), _px(108)), MAP_FUR, MAP_FUR_DARK, blur=1.1),
    )

    # Tronco denso
    torso = _ellipse_layer(size, (_px(30), _px(38), _px(98), _px(112)), MAP_FUR, MAP_FUR_DARK, blur=1.2)
    img = _composite(img, torso, _fur_tufts(size, rng))

    # Cabeça
    head = _ellipse_layer(size, (_px(40), _px(10), _px(88), _px(52)), MAP_FUR_GRAY, MAP_FUR_DARK, blur=1.0)
    img = _composite(img, head)

    # Olho único
    socket = _ellipse_layer(size, (_px(52), _px(22), _px(76), _px(44)), (30, 16, 12, 255), (10, 6, 6, 255), blur=0.5)
    eye_mask = _soft_mask_ellipse(size, (_px(55), _px(25), _px(73), _px(41)), blur=0.25)
    img = _composite(
        img,
        socket,
        _glow(size, eye_mask, (255, 30, 30, 230), blur=2.8, strength=0.95),
        _ellipse_layer(size, (_px(55), _px(25), _px(73), _px(41)), MAP_EYE, (90, 0, 8, 255), blur=0.3),
        _ellipse_layer(size, (_px(60), _px(29), _px(66), _px(35)), (255, 220, 210, 255), (255, 180, 160, 200), blur=0.15),
    )

    # Boca vertical no peito
    mouth_pts = [(_px(57), _px(56)), (_px(71), _px(56)), (_px(76), _px(84)), (_px(64), _px(100)), (_px(52), _px(84))]
    mouth = _polygon_layer(size, mouth_pts, (18, 4, 4, 255), (6, 1, 1, 255), blur=0.4)
    gums = _polygon_layer(
        size,
        [(_px(59), _px(60)), (_px(69), _px(60)), (_px(72), _px(82)), (_px(64), _px(92)), (_px(56), _px(82))],
        (90, 16, 16, 230),
        (40, 6, 6, 230),
        blur=0.3,
    )
    img = _composite(img, mouth, gums)

    teeth = Image.new("RGBA", size, (0, 0, 0, 0))
    td = ImageDraw.Draw(teeth)
    for x in range(_px(58), _px(71), _px(4)):
        td.polygon([(x, _px(60)), (x + _px(2), _px(70)), (x + _px(4), _px(60))], fill=(240, 232, 214, 245))
        td.polygon([(x, _px(90)), (x + _px(2), _px(80)), (x + _px(4), _px(90))], fill=(236, 226, 208, 245))
    teeth = teeth.filter(ImageFilter.GaussianBlur(radius=0.22 * SCALE))
    img = _composite(img, teeth)

    # Garras nas mãos
    for origin in ((_px(14), _px(100)), (_px(102), _px(100))):
        ox, oy = origin
        claw = _polygon_layer(
            size,
            [(ox, oy), (ox + _px(8), oy + _px(14)), (ox + _px(4), oy)],
            (220, 210, 190, 255),
            (140, 130, 110, 255),
            blur=0.25,
        )
        img = _composite(img, claw)

    return _finish(img, w, h)


# ---------------------------------------------------------------------------
# herb.png — Erva medicinal 32x32
# ---------------------------------------------------------------------------
def create_herb() -> Image.Image:
    """Ícone da erva medicinal 32×32."""
    w = h = 32
    size = (w * SCALE, h * SCALE)
    img = _blank(w, h)

    aura = _radial_gradient(size, (_px(16), _px(17)), _px(14), (240, 210, 80, 70), (80, 180, 90, 0))
    img = _composite(img, aura)

    stem = _polygon_layer(
        size,
        [(_px(15), _px(16)), (_px(17), _px(16)), (_px(17), _px(28)), (_px(15), _px(28))],
        LEAF_DARK,
        (40, 70, 30, 255),
        blur=0.25,
    )
    img = _composite(img, stem)

    leaves = [
        [(_px(16), _px(18)), (_px(6), _px(10)), (_px(14), _px(8)), (_px(18), _px(16))],
        [(_px(16), _px(18)), (_px(26), _px(9)), (_px(20), _px(6)), (_px(15), _px(15))],
        [(_px(16), _px(20)), (_px(10), _px(24)), (_px(16), _px(12)), (_px(22), _px(24))],
    ]
    tones = ((LEAF_LIGHT, LEAF), (LEAF, LEAF_DARK), (LEAF_LIGHT, LEAF_DARK))
    for pts, (top, bottom) in zip(leaves, tones):
        img = _composite(img, _polygon_layer(size, pts, top, bottom, blur=0.45))

    bud_mask = _soft_mask_ellipse(size, (_px(13), _px(12), _px(19), _px(18)), blur=0.25)
    img = _composite(
        img,
        _glow(size, bud_mask, (255, 220, 80, 200), blur=1.4, strength=0.85),
        _ellipse_layer(size, (_px(13), _px(12), _px(19), _px(18)), HERB_GOLD, GOLD_DEEP, blur=0.3),
    )
    return _finish(img, w, h)


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------
SPRITE_BUILDERS = {
    "player.png": create_player,
    "enemy_beast.png": create_enemy_beast,
    "boss_onca.png": create_boss_onca,
    "boss_mapinguari.png": create_boss_mapinguari,
    "herb.png": create_herb,
}


def generate_assets() -> dict[str, pygame.Surface]:
    """Gera (ou regrava) os placeholders PNG e devolve um cache em Surfaces.

    Os sprites artesanais em assets/player, onca e mapinguari não passam por aqui:
    este gerador só cobre player.png, bosses de fallback, besta e erva.
    """
    pygame.init()
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    loaded: dict[str, pygame.Surface] = {}
    for filename, builder in SPRITE_BUILDERS.items():
        sprite = builder()
        _save(sprite, filename)
        loaded[filename] = _to_pygame(sprite)
    return loaded


if __name__ == "__main__":
    generate_assets()
    print(f"Sprites gerados em: {ASSETS_DIR}")

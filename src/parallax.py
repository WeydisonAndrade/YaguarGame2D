"""Cenário em camadas com parallax a partir da arte da aldeia amazônica."""

from __future__ import annotations

from pathlib import Path

import pygame
from PIL import Image

from src.config import SCREEN_HEIGHT, SCREEN_WIDTH

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
PARALLAX_DIR = ASSETS_DIR / "parallax"

MAGENTA = (255, 0, 255)
KNOCKOUT_TOLERANCE = 70
EDGE_SOFTNESS = 28

# fator: quanto a camada se desloca com o foco (0 = quase fixo)
LAYER_SPECS = (
    ("forest_far.png", 0.16, False, False),
    ("forest_fg.png", 1.00, True, True),
)


def _knockout_magenta(src: Path, dest: Path) -> None:
    img = Image.open(src).convert("RGBA")
    pixels = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            dist = ((r - MAGENTA[0]) ** 2 + (g - MAGENTA[1]) ** 2 + (b - MAGENTA[2]) ** 2) ** 0.5
            if dist <= KNOCKOUT_TOLERANCE:
                pixels[x, y] = (r, g, b, 0)
            elif dist <= KNOCKOUT_TOLERANCE + EDGE_SOFTNESS:
                fade = (dist - KNOCKOUT_TOLERANCE) / EDGE_SOFTNESS
                pixels[x, y] = (r, g, b, int(a * fade))
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "PNG")


def prepare_parallax_layers(force: bool = False) -> None:
    """Garante PNGs com alpha em assets/parallax a partir das artes geradas."""
    sources = [
        Path(r"C:\Users\weydi\.cursor\projects\c-Users-weydi-Desktop-Nova-pasta\assets"),
        ASSETS_DIR,
    ]
    PARALLAX_DIR.mkdir(parents=True, exist_ok=True)

    for filename, _factor, needs_key, _front in LAYER_SPECS:
        dest = PARALLAX_DIR / filename
        if dest.exists() and not force:
            continue
        source = next((root / filename for root in sources if (root / filename).exists()), None)
        if source is None:
            continue
        if needs_key:
            _knockout_magenta(source, dest)
        else:
            Image.open(source).convert("RGB").save(dest, "PNG")


class ParallaxBackground:
    def __init__(self) -> None:
        prepare_parallax_layers()
        extra_w = int(SCREEN_WIDTH * 0.55)
        extra_h = 90
        target = (SCREEN_WIDTH + extra_w, SCREEN_HEIGHT + extra_h)

        self.back: list[tuple[pygame.Surface, float]] = []
        self.front: list[tuple[pygame.Surface, float]] = []

        for filename, factor, _key, is_front in LAYER_SPECS:
            path = PARALLAX_DIR / filename
            if not path.exists():
                continue
            raw = pygame.image.load(str(path)).convert_alpha()
            scaled = pygame.transform.smoothscale(raw, target)
            (self.front if is_front else self.back).append((scaled, factor))

        self._veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self._veil.fill((32, 10, 40))

    def _offset(self, surf: pygame.Surface, factor: float, focus: tuple[float, float]) -> tuple[int, int]:
        nx = max(-0.5, min(0.5, (focus[0] / SCREEN_WIDTH) - 0.5))
        ny = max(-0.5, min(0.5, (focus[1] / SCREEN_HEIGHT) - 0.5))
        slack_x = surf.get_width() - SCREEN_WIDTH
        slack_y = surf.get_height() - SCREEN_HEIGHT
        x = int(-slack_x * 0.5 - nx * slack_x * factor)
        y = int(-slack_y * 0.5 - ny * slack_y * factor)
        x = max(-slack_x, min(0, x))
        y = max(-slack_y, min(0, y))
        return x, y

    def draw_back(self, screen: pygame.Surface, focus: tuple[float, float]) -> None:
        for surf, factor in self.back:
            screen.blit(surf, self._offset(surf, factor, focus))

    def draw_front(self, screen: pygame.Surface, focus: tuple[float, float]) -> None:
        for surf, factor in self.front:
            screen.blit(surf, self._offset(surf, factor, focus))

    def draw_corrupt_veil(self, screen: pygame.Surface) -> None:
        screen.blit(self._veil, (0, 0), special_flags=pygame.BLEND_MULT)

    def draw_world(self, screen: pygame.Surface, focus: tuple[float, float], corrupt: bool = False) -> None:
        self.draw_back(screen, focus)
        if corrupt:
            screen.blit(self._veil, (0, 0), special_flags=pygame.BLEND_MULT)
        self.draw_front(screen, focus)

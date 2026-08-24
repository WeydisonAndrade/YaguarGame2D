"""Fundo de floresta: uma pintura por vez, com vento, névoa e folhas."""

from __future__ import annotations

import math
import random
from pathlib import Path

import pygame

from src.config import SCREEN_HEIGHT, SCREEN_WIDTH

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
PARALLAX_DIR = ASSETS_DIR / "parallax"

SCENE_FILES = (
    "forest1.png",
    "forest2.png",
)

COVER_PAD_X = 1.14
COVER_PAD_Y = 1.10
PARALLAX_FACTOR = 0.12

LEAF_COLORS = (
    (62, 110, 48),
    (92, 138, 52),
    (138, 118, 48),
    (48, 86, 42),
    (168, 140, 64),
    (36, 72, 38),
)


def _cover_scale(raw: pygame.Surface, tw: int, th: int) -> pygame.Surface:
    rw, rh = raw.get_width(), raw.get_height()
    scale = max(tw / rw, th / rh)
    size = (max(tw, int(round(rw * scale))), max(th, int(round(rh * scale))))
    return pygame.transform.smoothscale(raw, size)


def _make_leaf(color: tuple[int, int, int], size: int) -> pygame.Surface:
    surf = pygame.Surface((size * 2 + 4, size + 6), pygame.SRCALPHA)
    pygame.draw.ellipse(surf, (*color, 220), (2, 2, size * 2, size))
    dark = (max(0, color[0] - 30), max(0, color[1] - 30), max(0, color[2] - 24), 180)
    pygame.draw.line(surf, dark, (2, size // 2 + 2), (size * 2, size // 2 + 2), 1)
    return surf


def _make_mist(width: int, height: int, alpha: int) -> pygame.Surface:
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    for _ in range(18):
        rw = random.randint(int(width * 0.18), int(width * 0.42))
        rh = random.randint(int(height * 0.35), height)
        x = random.randint(-40, width - 40)
        y = random.randint(-20, height - rh // 2)
        shade = random.randint(186, 220)
        pygame.draw.ellipse(surf, (shade, shade + 8, shade + 6, alpha), (x, y, rw, rh))
    return surf


class ParallaxBackground:
    def __init__(self) -> None:
        target = (
            int(SCREEN_WIDTH * COVER_PAD_X),
            int(SCREEN_HEIGHT * COVER_PAD_Y),
        )
        self.scenes: list[pygame.Surface] = []
        for filename in SCENE_FILES:
            path = PARALLAX_DIR / filename
            if not path.exists():
                continue
            raw = pygame.image.load(str(path)).convert()
            self.scenes.append(_cover_scale(raw, *target))

        if not self.scenes:
            fallback = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            fallback.fill((18, 32, 22))
            self.scenes.append(fallback)

        self.index = 0
        self.time = 0.0
        self._veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self._veil.fill((32, 10, 40))
        self._rays = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._mist_layers = (
            (_make_mist(SCREEN_WIDTH + 280, 150, 22), 0.28, 90),
            (_make_mist(SCREEN_WIDTH + 340, 120, 16), 0.18, 210),
            (_make_mist(SCREEN_WIDTH + 260, 90, 14), 0.34, 380),
        )
        self._leaf_stamps = [_make_leaf(c, s) for c, s in zip(LEAF_COLORS, (7, 9, 6, 8, 10, 7))]
        self.leaves = [self._spawn_leaf(random.uniform(0, SCREEN_HEIGHT)) for _ in range(22)]
        self.motes = [self._spawn_mote() for _ in range(28)]

    def _spawn_leaf(self, y: float | None = None) -> dict:
        return {
            "x": random.uniform(-20, SCREEN_WIDTH + 20),
            "y": random.uniform(-40, SCREEN_HEIGHT) if y is None else y,
            "vx": random.uniform(-0.35, 0.55),
            "vy": random.uniform(0.35, 1.05),
            "rot": random.uniform(0, 360),
            "spin": random.uniform(-2.4, 2.4),
            "phase": random.uniform(0, math.tau),
            "stamp": random.choice(self._leaf_stamps),
        }

    def _spawn_mote(self) -> dict:
        return {
            "x": random.uniform(0, SCREEN_WIDTH),
            "y": random.uniform(0, SCREEN_HEIGHT),
            "phase": random.uniform(0, math.tau),
            "speed": random.uniform(0.25, 0.7),
            "size": random.choice((1, 1, 2)),
            "tone": random.choice(((210, 190, 110), (170, 210, 140), (230, 220, 170))),
        }

    def use_scene(self, index: int) -> None:
        self.index = max(0, min(index, len(self.scenes) - 1))

    def update(self, dt: float = 1 / 60) -> None:
        self.time += dt
        wind = math.sin(self.time * 0.55)
        for leaf in self.leaves:
            leaf["phase"] += dt * 1.6
            leaf["x"] += leaf["vx"] + wind * 0.45 + math.sin(leaf["phase"]) * 0.55
            leaf["y"] += leaf["vy"]
            leaf["rot"] += leaf["spin"]
            if leaf["y"] > SCREEN_HEIGHT + 16 or leaf["x"] < -30 or leaf["x"] > SCREEN_WIDTH + 30:
                leaf.update(self._spawn_leaf(-18))
        for mote in self.motes:
            mote["phase"] += dt * mote["speed"]
            mote["y"] -= dt * 10 * mote["speed"]
            mote["x"] += math.sin(mote["phase"] * 1.3) * 0.28 + wind * 0.2
            if mote["y"] < -8:
                mote["y"] = SCREEN_HEIGHT + 8
                mote["x"] = random.uniform(0, SCREEN_WIDTH)

    def _current(self) -> pygame.Surface:
        return self.scenes[self.index]

    def _offset(self, surf: pygame.Surface, factor: float, focus: tuple[float, float]) -> tuple[int, int]:
        nx = max(-0.5, min(0.5, (focus[0] / SCREEN_WIDTH) - 0.5))
        ny = max(-0.5, min(0.5, (focus[1] / SCREEN_HEIGHT) - 0.5))
        slack_x = surf.get_width() - SCREEN_WIDTH
        slack_y = surf.get_height() - SCREEN_HEIGHT
        wind_x = math.sin(self.time * 0.32) * min(16, max(0, slack_x) * 0.28)
        wind_y = math.sin(self.time * 0.21 + 0.8) * min(9, max(0, slack_y) * 0.32)
        x = int(-slack_x * 0.5 - nx * slack_x * factor + wind_x)
        y = int(-slack_y * 0.5 - ny * slack_y * factor + wind_y)
        if slack_x > 0:
            x = max(-slack_x, min(0, x))
        else:
            x = 0
        if slack_y > 0:
            y = max(-slack_y, min(0, y))
        else:
            y = 0
        return x, y

    def draw_back(self, screen: pygame.Surface, focus: tuple[float, float]) -> None:
        surf = self._current()
        screen.blit(surf, self._offset(surf, PARALLAX_FACTOR, focus))
        self._draw_godrays(screen)
        self._draw_mist(screen)
        self._draw_motes(screen)
        self._draw_leaves(screen)

    def _draw_godrays(self, screen: pygame.Surface) -> None:
        self._rays.fill((0, 0, 0, 0))
        t = self.time
        for i, base in enumerate((160, 390, 620, 850)):
            sway = math.sin(t * 0.18 + i * 0.9) * 36
            pulse = 0.55 + 0.45 * math.sin(t * 0.35 + i)
            alpha = int(12 + 11 * pulse)
            top = base + sway
            pygame.draw.polygon(
                self._rays,
                (255, 232, 176, alpha),
                (
                    (top, -30),
                    (top + 78, -30),
                    (top + 168 + sway * 0.25, SCREEN_HEIGHT),
                    (top - 56 + sway * 0.25, SCREEN_HEIGHT),
                ),
            )
        screen.blit(self._rays, (0, 0))

    def _draw_mist(self, screen: pygame.Surface) -> None:
        for mist, speed, y in self._mist_layers:
            span = mist.get_width()
            x = -int((self.time * (18 + speed * 40)) % span)
            screen.blit(mist, (x, y))
            screen.blit(mist, (x + span, y))

    def _draw_motes(self, screen: pygame.Surface) -> None:
        layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for mote in self.motes:
            flicker = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(mote["phase"] * 2.4))
            alpha = int(50 + 110 * flicker)
            pygame.draw.circle(
                layer,
                (*mote["tone"], alpha),
                (int(mote["x"]), int(mote["y"])),
                mote["size"],
            )
        screen.blit(layer, (0, 0))

    def _draw_leaves(self, screen: pygame.Surface) -> None:
        for leaf in self.leaves:
            stamp = pygame.transform.rotate(leaf["stamp"], leaf["rot"])
            screen.blit(stamp, stamp.get_rect(center=(int(leaf["x"]), int(leaf["y"]))))

    def draw_front(self, screen: pygame.Surface, focus: tuple[float, float]) -> None:
        return

    def draw_corrupt_veil(self, screen: pygame.Surface) -> None:
        screen.blit(self._veil, (0, 0), special_flags=pygame.BLEND_MULT)

    def draw_world(self, screen: pygame.Surface, focus: tuple[float, float], corrupt: bool = False) -> None:
        self.draw_back(screen, focus)
        if corrupt:
            self.draw_corrupt_veil(screen)

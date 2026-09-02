"""Sequências cinemáticas: introdução da Fase I e entrada do Mapinguari."""

from __future__ import annotations

from pathlib import Path

import pygame

from src.config import (
    BOSS_CINEMATIC_CAPTIONS,
    BOSS_CINEMATIC_FILES,
    BOSS_CINEMATIC_FOLDER,
    BOSS_CINEMATIC_KICKER,
    BOSS_CINEMATIC_PANS,
    SAND_CINEMATIC_CAPTIONS,
    SAND_CINEMATIC_FILES,
    SAND_CINEMATIC_FOLDER,
    SAND_CINEMATIC_KICKER,
    SAND_CINEMATIC_PANS,
    CINEMATIC_CAPTIONS,
    CINEMATIC_FADE_FRAMES,
    CINEMATIC_FILES,
    CINEMATIC_HOLD_FRAMES,
    CINEMATIC_PANS,
    CINEMATIC_ZOOM,
    COLOR_GOLD_BRIGHT,
    COLOR_GOLD_LEAF,
    COLOR_INK,
    COLOR_PARCHMENT,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from src.ui import blit_centered, load_font

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"

_TITLE_FONTS = (
    "palatinolinotype",
    "palatino",
    "georgia",
    "garamond",
    "constantia",
    "cambria",
    "timesnewroman",
    "serif",
)
_BODY_FONTS = (
    "georgia",
    "garamond",
    "constantia",
    "cambria",
    "palatinolinotype",
    "timesnewroman",
    "serif",
)

_frame_cache: dict[str, list[pygame.Surface]] = {}


def _cover_scale(raw: pygame.Surface, tw: int, th: int) -> pygame.Surface:
    """Escala a pintura para cobrir a área sem distorcer (modo cover)."""
    rw, rh = raw.get_width(), raw.get_height()
    if rw <= 0 or rh <= 0:
        return raw
    scale = max(tw / rw, th / rh)
    size = (max(tw, int(round(rw * scale))), max(th, int(round(rh * scale))))
    return pygame.transform.smoothscale(raw, size)


def load_cinematic_frames(folder: str, files: tuple[str, ...]) -> list[pygame.Surface]:
    """Carrega e redimensiona os PNGs uma vez por pasta; lista vazia se faltarem."""
    cached = _frame_cache.get(folder)
    if cached is not None:
        return cached

    target = (
        int(SCREEN_WIDTH * CINEMATIC_ZOOM),
        int(SCREEN_HEIGHT * CINEMATIC_ZOOM),
    )
    frames: list[pygame.Surface] = []
    directory = ASSETS_DIR / folder
    for name in files:
        path = directory / name
        if not path.is_file():
            continue
        raw = pygame.image.load(str(path)).convert()
        frames.append(_cover_scale(raw, *target))
    _frame_cache[folder] = frames
    return frames


class CinematicSequence:
    """Avança os quadros com Ken Burns, crossfade e legendas."""

    def __init__(
        self,
        folder: str = "cinematic_animation",
        files: tuple[str, ...] | None = None,
        captions: tuple[str, ...] | None = None,
        pans: tuple[tuple[float, float], ...] | None = None,
        kicker: str = "FASE I  ·  O CORAÇÃO DA FLORESTA",
    ) -> None:
        self.files = files or CINEMATIC_FILES
        self.captions = captions or CINEMATIC_CAPTIONS
        self.pans = pans or CINEMATIC_PANS
        self.kicker = kicker
        self.frames = load_cinematic_frames(folder, self.files)
        self.index = 0
        self.timer = 0
        self.done = len(self.frames) == 0
        self.font_caption = load_font(_TITLE_FONTS, 22)
        self.font_hint = load_font(_BODY_FONTS, 14)
        self.letter_h = 56

    @classmethod
    def intro(cls) -> "CinematicSequence":
        return cls()

    @classmethod
    def mapinguari(cls) -> "CinematicSequence":
        return cls(
            folder=BOSS_CINEMATIC_FOLDER,
            files=BOSS_CINEMATIC_FILES,
            captions=BOSS_CINEMATIC_CAPTIONS,
            pans=BOSS_CINEMATIC_PANS,
            kicker=BOSS_CINEMATIC_KICKER,
        )

    @classmethod
    def sand(cls) -> "CinematicSequence":
        return cls(
            folder=SAND_CINEMATIC_FOLDER,
            files=SAND_CINEMATIC_FILES,
            captions=SAND_CINEMATIC_CAPTIONS,
            pans=SAND_CINEMATIC_PANS,
            kicker=SAND_CINEMATIC_KICKER,
        )

    @property
    def shot_count(self) -> int:
        return len(self.frames)

    def skip(self) -> None:
        """Encerra a sequência (Espaço / clique / fim do último quadro)."""
        self.done = True

    def advance(self) -> None:
        """Pula para o próximo quadro; no último, marca como concluída."""
        if self.done or not self.frames:
            self.done = True
            return
        if self.index >= len(self.frames) - 1:
            self.done = True
            return
        self.index += 1
        self.timer = 0

    def update(self) -> None:
        if self.done or not self.frames:
            self.done = True
            return
        self.timer += 1
        last = self.index >= len(self.frames) - 1
        limit = CINEMATIC_HOLD_FRAMES + CINEMATIC_FADE_FRAMES
        if self.timer < limit:
            return
        if last:
            self.done = True
            return
        self.index += 1
        self.timer = 0

    def _ken_burns_blit(self, screen: pygame.Surface, frame: pygame.Surface, t: float, pan: tuple[float, float]) -> None:
        """Recorta uma janela que caminha e amplia sobre a pintura."""
        t = max(0.0, min(1.0, t))
        fw, fh = frame.get_width(), frame.get_height()
        max_ox = max(0, fw - SCREEN_WIDTH)
        max_oy = max(0, fh - SCREEN_HEIGHT)
        ox = int((0.5 + pan[0] * (t - 0.5)) * max_ox)
        oy = int((0.5 + pan[1] * (t - 0.5)) * max_oy)
        ox = max(0, min(max_ox, ox))
        oy = max(0, min(max_oy, oy))
        screen.blit(frame, (0, 0), pygame.Rect(ox, oy, SCREEN_WIDTH, SCREEN_HEIGHT))

    def _pan_at(self, index: int) -> tuple[float, float]:
        if not self.pans:
            return (0.0, 0.0)
        return self.pans[index % len(self.pans)]

    def _hold_progress(self) -> float:
        return min(1.0, self.timer / max(1, CINEMATIC_HOLD_FRAMES))

    def _fade_alpha(self) -> int:
        """0 durante o hold; 0–255 na janela de crossfade."""
        if self.timer <= CINEMATIC_HOLD_FRAMES:
            return 0
        span = max(1, CINEMATIC_FADE_FRAMES)
        return int(255 * min(1.0, (self.timer - CINEMATIC_HOLD_FRAMES) / span))

    def draw(self, screen: pygame.Surface) -> None:
        if not self.frames:
            screen.fill(COLOR_INK)
            return

        t = self._hold_progress()
        pan = self._pan_at(self.index)
        self._ken_burns_blit(screen, self.frames[self.index], t, pan)

        fade = self._fade_alpha()
        last = self.index >= len(self.frames) - 1
        if fade > 0:
            if last:
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                overlay.fill(COLOR_INK)
                overlay.set_alpha(fade)
                screen.blit(overlay, (0, 0))
            else:
                nxt = self.frames[self.index + 1]
                temp = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                self._ken_burns_blit(temp, nxt, 0.0, self._pan_at(self.index + 1))
                temp.set_alpha(fade)
                screen.blit(temp, (0, 0))

        pygame.draw.rect(screen, COLOR_INK, (0, 0, SCREEN_WIDTH, self.letter_h))
        pygame.draw.rect(screen, COLOR_INK, (0, SCREEN_HEIGHT - self.letter_h, SCREEN_WIDTH, self.letter_h))
        pygame.draw.line(screen, COLOR_GOLD_LEAF, (48, self.letter_h), (SCREEN_WIDTH - 48, self.letter_h), 1)
        pygame.draw.line(
            screen,
            COLOR_GOLD_LEAF,
            (48, SCREEN_HEIGHT - self.letter_h),
            (SCREEN_WIDTH - 48, SCREEN_HEIGHT - self.letter_h),
            1,
        )

        kicker = self.font_hint.render(self.kicker, True, COLOR_GOLD_LEAF)
        blit_centered(screen, kicker, (SCREEN_WIDTH // 2, self.letter_h // 2))

        caption = self.captions[self.index] if self.index < len(self.captions) else ""
        if caption:
            band = pygame.Surface((SCREEN_WIDTH, 78), pygame.SRCALPHA)
            band.fill((12, 8, 6, 170))
            screen.blit(band, (0, SCREEN_HEIGHT - self.letter_h - 78))
            text = self.font_caption.render(caption, True, COLOR_PARCHMENT)
            blit_centered(screen, text, (SCREEN_WIDTH // 2, SCREEN_HEIGHT - self.letter_h - 44))

        hint = self.font_hint.render("ESPAÇO  pular    ·    clique  avançar", True, COLOR_GOLD_BRIGHT)
        blit_centered(screen, hint, (SCREEN_WIDTH // 2, SCREEN_HEIGHT - self.letter_h // 2))

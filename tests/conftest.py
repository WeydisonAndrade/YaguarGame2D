"""Ambiente headless para a pirâmide de testes (Pygame sem janela real)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from src.config import SCREEN_HEIGHT, SCREEN_WIDTH  # noqa: E402


class FakeKeys:
    """Teclado mínimo: só as teclas passadas no construtor estão pressionadas."""

    def __init__(self, *pressed: int) -> None:
        self._pressed = set(pressed)

    def __getitem__(self, key: int) -> bool:
        return key in self._pressed


@pytest.fixture(scope="session", autouse=True)
def pygame_session():
    """Um display dummy para convert_alpha, fontes e mixer."""
    pygame.mixer.pre_init(44100, -16, 2, 1024)
    pygame.init()
    pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    yield
    pygame.quit()


@pytest.fixture(autouse=True)
def reset_physics_world():
    from src.config import PLATFORMS, SCREEN_WIDTH
    from src.entities import set_physics_world

    set_physics_world(PLATFORMS, SCREEN_WIDTH, allow_pits=False)
    yield
    set_physics_world(PLATFORMS, SCREEN_WIDTH, allow_pits=False)


@pytest.fixture
def game():
    """Sessão completa já na partida, com fase recém-resetada."""
    from src.game import Game
    from src.game_states import PlayingState

    session = Game()
    session.reset_level()
    session.change_state(PlayingState())
    return session

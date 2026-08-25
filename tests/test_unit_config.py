"""Base da pirâmide: constantes da Fase 1 e arquivos de asset necessários."""

from __future__ import annotations

from pathlib import Path

from src.config import (
    ONCA_WAVE_TOTAL,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TOTAL_HERBS_TO_COLLECT,
    VICTORY_PROGRESS_MAX,
)

ASSETS = Path(__file__).resolve().parents[1] / "assets"

REQUIRED_IMAGES = (
    "player/idle.png",
    "player/run1.png",
    "player/run2.png",
    "player/crouch.png",
    "player/jump.png",
    "player/attack.png",
    "player/defend.png",
    "onca/idle.png",
    "onca/claw.png",
    "onca/bite.png",
    "mapinguari/idle.png",
    "mapinguari/attack.png",
    "mapinguari/throw.png",
    "tree_trunk.png",
    "herb.png",
    "parallax/forest1.png",
    "parallax/forest2.png",
    "cinematic_animation/img01.png",
    "cinematic_animation/img06.png",
)


def test_janela_e_metas_da_fase_1():
    assert SCREEN_WIDTH == 1024
    assert SCREEN_HEIGHT == 600
    assert TOTAL_HERBS_TO_COLLECT == 3
    assert ONCA_WAVE_TOTAL == 3
    assert VICTORY_PROGRESS_MAX == 3


def test_sprites_essenciais_existem_no_pacote():
    missing = [name for name in REQUIRED_IMAGES if not (ASSETS / name).is_file()]
    assert missing == []

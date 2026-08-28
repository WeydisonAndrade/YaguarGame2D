"""Base da pirâmide: constantes da Fase 1 e arquivos de asset necessários."""

from __future__ import annotations

from pathlib import Path

from src.config import (
    ONCA_WAVE_KINDS,
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
    "cinematic_animation/epic_music01.mp3",
    "battleBoss/imgBattle01.png",
    "battleBoss/imgBaattle07.png",
)


def test_janela_e_metas_da_fase_1():
    assert SCREEN_WIDTH == 1024
    assert SCREEN_HEIGHT == 600
    assert TOTAL_HERBS_TO_COLLECT == 3
    assert ONCA_WAVE_TOTAL == 3
    assert ONCA_WAVE_KINDS == ("normal", "pantera", "espectral")
    assert VICTORY_PROGRESS_MAX == 3


def test_sprites_essenciais_existem_no_pacote():
    from src.trail_art import ensure_crossing_world, ensure_trail_art

    ensure_trail_art()
    ensure_crossing_world()
    missing = [name for name in REQUIRED_IMAGES if not (ASSETS / name).is_file()]
    assert missing == []
    assert (ASSETS / "parallax" / "forest_fendas.jpg").is_file()
    assert (ASSETS / "parallax" / "forest_fendas_clean.png").is_file()
    assert (ASSETS / "parallax" / "forest_trail.png").is_file()
    assert (ASSETS / "parallax" / "forest_crossing.png").is_file()


def test_clareira_e_pintura_estatica():
    from PIL import Image

    from src.trail_art import TRAIL_PATH, ensure_trail_art

    ensure_trail_art()
    play = Image.open(TRAIL_PATH)
    assert play.mode == "RGB"
    assert play.size == (SCREEN_WIDTH, SCREEN_HEIGHT)


def test_mundo_da_travessia_e_continuo():
    from PIL import Image

    from src.config import TRAIL_ORIGIN_X, TRAIL_WORLD_WIDTH
    from src.trail_art import CROSSING_PATH, ensure_crossing_world

    ensure_crossing_world()
    world = Image.open(CROSSING_PATH)
    assert world.mode == "RGB"
    assert world.size == (TRAIL_WORLD_WIDTH, SCREEN_HEIGHT)
    # A costura não pode ser um corte vertical de cor sólida.
    seam = TRAIL_ORIGIN_X
    left = list(world.getpixel((seam - 8, 80)))
    right = list(world.getpixel((seam + 8, 80)))
    delta = sum(abs(a - b) for a, b in zip(left, right))
    assert delta < 90

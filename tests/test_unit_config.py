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
    "player/bow.png",
    "player/bow_quiver.png",
    "player/bow_nock.png",
    "player/bow_color_corrected.png",
    "player/bow_quiver_color_corrected.png",
    "player/bow_nock_color_corrected.png",
    "player/arrow.png",
    "onca/idle.png",
    "onca/claw.png",
    "onca/bite.png",
    "onca/pintada.png",
    "mapinguari/idle.png",
    "mapinguari/attack.png",
    "mapinguari/throw.png",
    "tree_trunk.png",
    "herb.png",
    "parallax/forest1.png",
    "parallax/forest2.png",
    "parallax/mapinguari_arena.png",
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
    assert (ASSETS / "parallax" / "forest_sand_fendas.png").is_file()


def test_clareira_e_pintura_estatica():
    from PIL import Image

    from src.trail_art import TRAIL_PATH, ensure_trail_art

    ensure_trail_art()
    play = Image.open(TRAIL_PATH)
    assert play.mode == "RGB"
    assert play.size == (SCREEN_WIDTH, SCREEN_HEIGHT)


def test_mundo_da_travessia_e_continuo():
    from PIL import Image

    from src.config import FOREST_WORLD_WIDTH, TRAIL_ORIGIN_X
    from src.trail_art import CROSSING_PATH, ensure_crossing_world

    ensure_crossing_world()
    world = Image.open(CROSSING_PATH)
    assert world.mode == "RGB"
    assert world.size == (FOREST_WORLD_WIDTH, SCREEN_HEIGHT)
    # A costura não pode ser um corte vertical de cor sólida.
    seam = TRAIL_ORIGIN_X
    left = list(world.getpixel((seam - 8, 80)))
    right = list(world.getpixel((seam + 8, 80)))
    delta = sum(abs(a - b) for a, b in zip(left, right))
    assert delta < 90


def test_travessia_nao_repete_a_floresta_da_arena():
    """O trecho à direita não é uma cópia lado a lado de forest1."""
    from PIL import Image

    from src.config import FOREST_WORLD_WIDTH
    from src.trail_art import CROSSING_PATH, ensure_crossing_world

    ensure_crossing_world()
    world = Image.open(CROSSING_PATH)
    a = world.getpixel((180, 360))
    b = world.getpixel((180 + SCREEN_WIDTH, 360))
    delta = sum(abs(x - y) for x, y in zip(a, b))
    assert delta > 40
    assert world.size[0] == FOREST_WORLD_WIDTH


def test_mundo_da_travessia_termina_na_areia():
    from PIL import Image

    from src.config import FOREST_WORLD_WIDTH, SAND_ORIGIN_X, SAND_WORLD_WIDTH, TRAIL_WORLD_WIDTH
    from src.trail_art import CROSSING_PATH, ensure_crossing_world

    ensure_crossing_world()
    world = Image.open(CROSSING_PATH)
    assert world.size == (SAND_WORLD_WIDTH, SCREEN_HEIGHT)
    assert FOREST_WORLD_WIDTH == SAND_WORLD_WIDTH
    assert SAND_ORIGIN_X == TRAIL_WORLD_WIDTH
    seam = SAND_ORIGIN_X
    left = list(world.getpixel((seam - 8, 80)))
    right = list(world.getpixel((seam + 8, 80)))
    delta = sum(abs(a - b) for a, b in zip(left, right))
    assert delta < 110


def _opaque_paper_pixels(path: Path, luma_min: float = 220) -> int:
    from PIL import Image

    img = Image.open(path).convert("RGBA")
    px = img.load()
    width, height = img.size
    count = 0
    for y in range(height):
        for x in range(width):
            r, g, b, a = px[x, y]
            if a <= 80:
                continue
            luma = 0.3 * r + 0.59 * g + 0.11 * b
            sat = max(r, g, b) - min(r, g, b)
            if luma >= luma_min and sat < 30:
                count += 1
    return count


def test_mapinguari_throw_sem_fundo_branco_nos_bracos():
    """O oco entre os braços e o tronco arremessado não pode ser papel branco."""
    assert _opaque_paper_pixels(ASSETS / "mapinguari" / "throw.png") < 20
    assert _opaque_paper_pixels(ASSETS / "tree_trunk.png") < 20

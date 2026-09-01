"""Pipeline de assets: camadas e manifesto."""
from __future__ import annotations

from pathlib import Path

import pygame
from PIL import Image

from src.config import FOREST_WORLD_WIDTH, GROUND_Y, SCREEN_WIDTH, TRAIL_ORIGIN_X
from src.layered_art import BG_MID_FENDAS_VINES, ENV_CAVE_ENTRANCE, chroma_key_magenta, ensure_world_layers

ASSETS = Path(__file__).resolve().parents[1] / "assets"


def test_camadas_derivadas_existem_com_alpha():
    ensure_world_layers()
    cave = Image.open(ENV_CAVE_ENTRANCE)
    assert cave.mode == "RGBA"
    assert cave.size[1] <= 620
    bands = cave.split()
    assert bands[-1].getextrema()[0] == 0
    mid = Image.open(BG_MID_FENDAS_VINES)
    assert mid.size == (2048, 600)


def test_chroma_magenta_gera_alpha():
    src = Image.new("RGB", (32, 32), (255, 0, 255))
    src.putpixel((16, 16), (60, 80, 40))
    out = chroma_key_magenta(src)
    assert out.mode == "RGBA"
    assert out.getpixel((0, 0))[3] == 0
    assert out.getpixel((16, 16))[3] > 200


def test_manifesto_e_checagem_silenciosa_fora_de_debug():
    from src.asset_registry import load_manifest, warn_missing_assets

    items = load_manifest()
    assert any(i.get("asset_id") == "env_cave_entrance_01" for i in items)
    assert warn_missing_assets(False) == []


def test_pose_da_lanca_sem_halo_branco():
    from src.player_anim import PLAYER_DIR, prepare_player_sprites

    prepare_player_sprites()
    img = Image.open(PLAYER_DIR / "attack.png").convert("RGBA")
    w, h = img.size
    px = img.load()
    halo = 0
    neighbors = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 40:
                continue
            edge = False
            for dx, dy in neighbors:
                nx, ny = x + dx, y + dy
                if nx < 0 or ny < 0 or nx >= w or ny >= h or px[nx, ny][3] < 18:
                    edge = True
                    break
            if not edge:
                continue
            luma = 0.3 * r + 0.59 * g + 0.11 * b
            sat = max(r, g, b) - min(r, g, b)
            if luma >= 200 and sat <= 22:
                halo += 1
    assert halo == 0


def test_poses_de_arco_sem_halo_branco():
    from src.player_anim import PLAYER_DIR, prepare_player_sprites

    prepare_player_sprites()
    neighbors = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))
    for name in ("bow.png", "bow_quiver.png", "bow_nock.png"):
        img = Image.open(PLAYER_DIR / name).convert("RGBA")
        w, h = img.size
        px = img.load()
        halo = 0
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                if a < 40:
                    continue
                edge = False
                for dx, dy in neighbors:
                    nx, ny = x + dx, y + dy
                    if nx < 0 or ny < 0 or nx >= w or ny >= h or px[nx, ny][3] < 18:
                        edge = True
                        break
                if not edge:
                    continue
                luma = 0.3 * r + 0.59 * g + 0.11 * b
                sat = max(r, g, b) - min(r, g, b)
                if luma >= 200 and sat <= 22:
                    halo += 1
        assert halo == 0, f"{name} ainda tem halo branco ({halo} px)"


def test_flecha_isolada_tem_alpha_e_e_horizontal():
    from src.player_anim import PLAYER_DIR, prepare_arrow_sprite

    prepare_arrow_sprite(force=True)
    img = Image.open(PLAYER_DIR / "arrow.png").convert("RGBA")
    w, h = img.size
    assert 5 <= h <= 8
    assert 40 <= w <= 100
    assert w > h * 3
    bands = img.split()
    assert bands[-1].getextrema()[0] == 0
    assert bands[-1].getextrema()[1] == 255


def test_pose_de_pulo_nao_muda_hurtbox():
    from src.entities import YaguarPlayer

    player = YaguarPlayer(200, GROUND_Y)
    box = player.hurtbox.copy()
    player._set_pose("jump")
    assert player.hurtbox.size == box.size
    assert player.rect.midbottom[1] == GROUND_Y


def test_parallax_carrega_camadas_sem_quebrar_cena():
    from src.parallax import ParallaxBackground

    bg = ParallaxBackground()
    screen = pygame.display.get_surface()
    bg.use_crossing()
    bg.draw_back(screen, (200, 400), camera_x=float(TRAIL_ORIGIN_X))
    bg.draw_front(screen, (200, 400))
    bg.draw_back(screen, (200, 400), camera_x=float(FOREST_WORLD_WIDTH - SCREEN_WIDTH))
    bg.draw_front(screen, (200, 400))
    bg.use_boss_arena()
    assert bg.is_boss_arena()
    bg.draw_back(screen, (200, 400), camera_x=0)

"""Base da pirâmide: física pura, sem loop de jogo."""

from __future__ import annotations

import pygame

from src.config import GRAVITY, GROUND_Y, JUMP_VELOCITY, PLAYER_RUN_SPEED, PLAYER_WALK_SPEED, SCREEN_HEIGHT, SCREEN_WIDTH
from src.config import TRAIL_GAP_1_WIDTH, TRAIL_GAP_2_WIDTH, TRAIL_PLATFORMS, TRAIL_WORLD_WIDTH
from src.entities import apply_gravity_and_platforms, platform_rects, set_physics_world


def _body(x: int = 200, bottom: int = GROUND_Y) -> pygame.Rect:
    rect = pygame.Rect(0, 0, 60, 120)
    rect.midbottom = (x, bottom)
    return rect


def test_plataformas_cobrem_a_largura_da_tela():
    plats = platform_rects()
    assert len(plats) == 1
    assert plats[0].left == 0
    assert plats[0].width == SCREEN_WIDTH
    assert plats[0].top == GROUND_Y


def test_gravidade_aumenta_velocidade_de_queda():
    rect, vel_y, grounded = apply_gravity_and_platforms(_body(bottom=200), 0.0, False)
    assert vel_y == GRAVITY
    assert rect.bottom >= 200
    assert grounded is False


def test_queda_pousa_na_laje_e_zera_vel_y():
    rect = _body(bottom=GROUND_Y - 4)
    vel_y = 8.0
    grounded = False
    for _ in range(12):
        rect, vel_y, grounded = apply_gravity_and_platforms(rect, vel_y, grounded)
    assert grounded is True
    assert vel_y == 0
    assert rect.bottom == GROUND_Y + 1


def test_pulo_sai_do_chao_e_depois_aterissa():
    rect = _body()
    vel_y = JUMP_VELOCITY
    grounded = False
    airborne = False
    for _ in range(80):
        rect, vel_y, grounded = apply_gravity_and_platforms(rect, vel_y, grounded)
        if not grounded:
            airborne = True
        elif airborne:
            break
    assert airborne is True
    assert grounded is True
    assert rect.bottom == GROUND_Y + 1


def test_corpo_nao_sai_pelas_laterais_da_tela():
    rect = _body(x=-40)
    rect, _, _ = apply_gravity_and_platforms(rect, 0.0, True)
    assert rect.left >= 0

    rect = _body(x=SCREEN_WIDTH + 80)
    rect, _, _ = apply_gravity_and_platforms(rect, 0.0, True)
    assert rect.right <= SCREEN_WIDTH


def test_corpo_nao_cai_abaixo_do_chao_mesmo_com_vel_alta():
    rect = _body(bottom=GROUND_Y - 2)
    rect, vel_y, grounded = apply_gravity_and_platforms(rect, 80.0, False)
    assert grounded is True
    assert vel_y == 0
    assert rect.bottom <= GROUND_Y + 1
    assert rect.bottom < SCREEN_HEIGHT


def test_fendas_exigem_salto_e_cabem_na_corrida():
    """A 1ª fenda da pintura cabe no pulo a pé (~156 px); a 2ª pede corrida (~273 px)."""
    walk_range = int(PLAYER_WALK_SPEED) * 39
    run_range = int(PLAYER_RUN_SPEED) * 39
    assert walk_range == 156
    assert run_range == 273
    assert TRAIL_GAP_1_WIDTH > 80
    assert TRAIL_GAP_1_WIDTH < walk_range
    assert walk_range - TRAIL_GAP_1_WIDTH >= 8
    assert TRAIL_GAP_2_WIDTH > walk_range
    assert TRAIL_GAP_2_WIDTH < run_range - 40


def _lip_rect(plat: pygame.Rect, ground_y: int) -> pygame.Rect:
    """Pés encostados na borda da grama, como quem vai pular a fenda."""
    rect = pygame.Rect(0, 0, 92, 168)
    rect.x = plat.right - 2 - 80
    rect.bottom = ground_y
    return rect


def test_pulo_a_pe_cruza_a_primeira_fenda():
    from src.config import PLATFORMS, TRAIL_GROUND_Y

    set_physics_world(TRAIL_PLATFORMS, TRAIL_WORLD_WIDTH, allow_pits=True)
    try:
        plats = [pygame.Rect(*box) for box in TRAIL_PLATFORMS]
        rect = _lip_rect(plats[0], TRAIL_GROUND_Y)
        vel_y = JUMP_VELOCITY
        grounded = False
        landed = False
        for _ in range(55):
            rect.x += 4
            rect, vel_y, grounded = apply_gravity_and_platforms(rect, vel_y, grounded)
            if grounded and rect.centerx > plats[0].right:
                landed = True
                break
        assert landed
    finally:
        set_physics_world(PLATFORMS, SCREEN_WIDTH, allow_pits=False)


def test_pulo_correndo_cruza_as_duas_fendas():
    from src.config import PLATFORMS, TRAIL_GROUND_Y

    set_physics_world(TRAIL_PLATFORMS, TRAIL_WORLD_WIDTH, allow_pits=True)
    try:
        plats = [pygame.Rect(*box) for box in TRAIL_PLATFORMS]
        for prev, nxt in zip(plats, plats[1:]):
            rect = _lip_rect(prev, TRAIL_GROUND_Y)
            vel_y = JUMP_VELOCITY
            grounded = False
            landed = False
            for _ in range(55):
                rect.x += 7
                rect, vel_y, grounded = apply_gravity_and_platforms(rect, vel_y, grounded)
                if grounded and rect.centerx > prev.right:
                    landed = True
                    break
            assert landed, f"falhou {prev.right} → {nxt.left}"
    finally:
        set_physics_world(PLATFORMS, SCREEN_WIDTH, allow_pits=False)


def test_clareira_continua_o_chao_da_arena():
    """Arena e fendas compartilham a mesma linha de grama, sem degrau na costura."""
    from src.config import FOREST_CROSSING_PLATFORMS, FOREST_WORLD_WIDTH, PLATFORMS, TRAIL_ORIGIN_X

    assert all(box[1] == GROUND_Y for box in FOREST_CROSSING_PLATFORMS)
    arena = FOREST_CROSSING_PLATFORMS[0]
    assert arena[0] + arena[2] == TRAIL_ORIGIN_X

    set_physics_world(FOREST_CROSSING_PLATFORMS, FOREST_WORLD_WIDTH, allow_pits=True)
    try:
        rect = pygame.Rect(0, 0, 92, 168)
        rect.midbottom = (TRAIL_ORIGIN_X, GROUND_Y)
        _, _, grounded = apply_gravity_and_platforms(rect, 0.0, True)
        assert grounded is True
    finally:
        set_physics_world(PLATFORMS, SCREEN_WIDTH, allow_pits=False)


def test_fenda_pintada_nao_tem_chao():
    from src.config import PLATFORMS, TRAIL_GROUND_Y, TRAIL_A_X, TRAIL_PLATFORM_A_WIDTH, TRAIL_GAP_1_WIDTH

    set_physics_world(TRAIL_PLATFORMS, TRAIL_WORLD_WIDTH, allow_pits=True)
    try:
        gap_x = TRAIL_A_X + TRAIL_PLATFORM_A_WIDTH + TRAIL_GAP_1_WIDTH // 2
        rect = pygame.Rect(0, 0, 92, 168)
        rect.midbottom = (gap_x, TRAIL_GROUND_Y)
        _, _, grounded = apply_gravity_and_platforms(rect, 0.0, True)
        assert grounded is False
    finally:
        set_physics_world(PLATFORMS, SCREEN_WIDTH, allow_pits=False)

"""Base da pirâmide: física pura, sem loop de jogo."""

from __future__ import annotations

import pygame

from src.config import GRAVITY, GROUND_Y, JUMP_VELOCITY, SCREEN_HEIGHT, SCREEN_WIDTH
from src.entities import apply_gravity_and_platforms, platform_rects


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

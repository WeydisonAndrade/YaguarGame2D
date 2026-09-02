"""Flecha-corda só nas poças: o galho vira pêndulo, o resto do arco não muda."""
from __future__ import annotations

import pygame

from src.config import (
    CONTINUE_DRAW_X,
    GROUND_Y,
    MAPINGUARI_GATE_X,
    ROPE_BRANCH_H,
    ROPE_BRANCH_W,
    ROPE_BRANCH_X,
    ROPE_BRANCH_Y,
)
from src.entities import Arrow, YaguarPlayer
from src import rope_swing
from tests.conftest import FakeKeys


def test_flecha_so_leva_corda_neste_trecho():
    arena = YaguarPlayer(200, GROUND_Y)
    assert rope_swing.in_zone(arena) is False
    sand = YaguarPlayer(CONTINUE_DRAW_X + 40, GROUND_Y)
    assert rope_swing.in_zone(sand) is True


def test_galho_fica_sobre_as_pocas():
    box = rope_swing.branch_rect()
    assert box.top == ROPE_BRANCH_Y
    assert box.width == ROPE_BRANCH_W
    assert box.height == ROPE_BRANCH_H
    assert box.left == ROPE_BRANCH_X
    assert box.bottom < GROUND_Y
    assert box.right > CONTINUE_DRAW_X + 500


def test_cravar_no_galho_comeca_o_balanco():
    player = YaguarPlayer(CONTINUE_DRAW_X + 80, GROUND_Y)
    player.facing = 1
    arrow = Arrow(ROPE_BRANCH_X + 80, ROPE_BRANCH_Y + 40, 0.0, 400.0, 12)
    arrow.roped = True
    rope_swing.attach(player, arrow)
    assert player.swinging is True
    assert player.on_ground is False
    assert player.rope_len > 40
    start_x = player.rect.centerx
    keys = FakeKeys()
    for _ in range(45):
        rope_swing.step(player, keys, 1.0 / 60.0)
        if not player.swinging:
            break
    assert player.swinging is True
    assert player.rect.centerx != start_x
    assert player.rect.bottom < GROUND_Y


def test_soltar_a_corda_devolve_o_momentum():
    player = YaguarPlayer(CONTINUE_DRAW_X + 80, GROUND_Y)
    arrow = Arrow(ROPE_BRANCH_X + 120, ROPE_BRANCH_Y + 30, 0.0, 400.0, 12)
    arrow.roped = True
    rope_swing.attach(player, arrow)
    player.rope_omega = 0.08
    rope_swing.release(player)
    assert player.swinging is False
    assert abs(player.air_vx) > 0 or player.vel_y != 0


def test_flecha_no_galho_marca_a_ancora():
    arrow = Arrow(ROPE_BRANCH_X + 40, ROPE_BRANCH_Y + 20, 0.2, 1200.0, 12)
    arrow.roped = True
    arrow.prev_x = arrow.fx - 30
    arrow.prev_y = arrow.fy + 10
    assert rope_swing.arrow_hits_branch(arrow) is True
    miss = Arrow(200, 200, 0.0, 800.0, 12)
    miss.roped = True
    miss.prev_x, miss.prev_y = 180.0, 200.0
    assert rope_swing.arrow_hits_branch(miss) is False


def test_flecha_crava_no_ponto_exato_da_arvore():
    """A ponta fica no impacto, no ângulo do voo — não no centro do retângulo."""
    import math

    # Vem da esquerda e entra no tronco da segunda árvore.
    surface_x = float(CONTINUE_DRAW_X + 800)
    surface_y = 280.0
    arrow = Arrow(surface_x + 10, surface_y, 0.0, 1400.0, 12)
    arrow.roped = True
    arrow.prev_x = surface_x - 40
    arrow.prev_y = surface_y
    hit = rope_swing.tree_hit_point(arrow)
    assert hit is not None
    assert abs(hit[0] - surface_x) <= 2
    assert abs(hit[1] - surface_y) <= 2
    ux, uy = 1.0, 0.0
    rope_swing.embed_arrow(arrow, hit[0], hit[1])
    assert arrow.stuck is True
    assert arrow.anchor_hit is True
    nose = rope_swing._arrow_tip_offset(arrow._base)
    tip_x = arrow.fx + ux * nose
    tip_y = arrow.fy + uy * nose
    assert abs(tip_x - (hit[0] + rope_swing.ROPE_EMBED)) <= 2
    assert abs(tip_y - hit[1]) <= 2
    assert abs(arrow._flight_ux - ux) < 1e-6
    ang = -math.degrees(math.atan2(arrow._flight_uy, arrow._flight_ux))
    arrow._orient()
    expected = pygame.transform.rotate(arrow._base, ang)
    assert arrow.image.get_size() == expected.get_size()


def test_primeira_arvore_nao_crava_a_flecha():
    """A árvore antes das poças não é alvo; só a da direita."""
    x0 = CONTINUE_DRAW_X + 80
    arrow = Arrow(x0 + 20, 180.0, 0.0, 1200.0, 12)
    arrow.roped = True
    arrow.prev_x = x0 - 30
    arrow.prev_y = 180.0
    assert rope_swing.tree_hit_point(arrow) is None


def test_arbustos_nao_cravam_a_flecha():
    """Musgo pendurado e folhagem ao lado do tronco não são madeira."""
    under = Arrow(CONTINUE_DRAW_X + 530, 210.0, 0.0, 1200.0, 12)
    under.roped = True
    under.prev_x = CONTINUE_DRAW_X + 500
    under.prev_y = 210.0
    assert rope_swing.tree_hit_point(under) is None
    beside = Arrow(CONTINUE_DRAW_X + 730, 280.0, 0.0, 1200.0, 12)
    beside.roped = True
    beside.prev_x = CONTINUE_DRAW_X + 700
    beside.prev_y = 280.0
    assert rope_swing.tree_hit_point(beside) is None


def test_balanco_nao_e_engolido_pela_areia():
    from src import quicksand

    player = YaguarPlayer(CONTINUE_DRAW_X + 80, GROUND_Y)
    arrow = Arrow(ROPE_BRANCH_X + 80, ROPE_BRANCH_Y + 40, 0.0, 400.0, 12)
    rope_swing.attach(player, arrow)
    player.rect.centerx = CONTINUE_DRAW_X + 400
    quicksand.after_physics(player, 1.0 / 60.0)
    assert player.swinging is True
    assert player.sand_sink == 0
    assert quicksand.swallowed(player) is False


def test_portao_fica_a_direita_do_galho():
    assert MAPINGUARI_GATE_X > ROPE_BRANCH_X


def test_balanco_para_a_direita_cruza_a_primeira_poca():
    from src.config import CONTINUE_SAND_POOLS

    player = YaguarPlayer(CONTINUE_DRAW_X + 40, GROUND_Y)
    arrow = Arrow(ROPE_BRANCH_X + ROPE_BRANCH_W - 40, ROPE_BRANCH_Y + 36, 0.0, 400.0, 12)
    rope_swing.attach(player, arrow)
    keys = FakeKeys(pygame.K_d)
    xs = [player.rect.centerx]
    for _ in range(180):
        rope_swing.step(player, keys, 1.0 / 60.0)
        xs.append(player.rect.centerx)
    first_pool_end = CONTINUE_SAND_POOLS[0][0] + CONTINUE_SAND_POOLS[0][1]
    assert max(xs) > first_pool_end


def test_disparo_neste_trecho_amarra_a_corda(monkeypatch):
    from src.config import BOW_NOCK, FOREST_CROSSING_PLATFORMS, FOREST_WORLD_WIDTH, KEY_ATTACK, KEY_BOW_AIM
    from src.entities import set_physics_world

    set_physics_world(FOREST_CROSSING_PLATFORMS, FOREST_WORLD_WIDTH, allow_pits=True)

    def _aim(player, wx, wy):
        monkeypatch.setattr(
            pygame.mouse, "get_pos", lambda: (int(wx - player.camera_x), int(wy))
        )

    sand = YaguarPlayer(CONTINUE_DRAW_X + 40, GROUND_Y)
    _aim(sand, ROPE_BRANCH_X + 80, ROPE_BRANCH_Y + 40)
    for _ in range(int(BOW_NOCK / (1 / 60)) + 4):
        sand.update(FakeKeys(KEY_BOW_AIM), (False, False, False), 1 / 60)
    sand.update(FakeKeys(KEY_BOW_AIM, KEY_ATTACK), (True, False, False), 1 / 60)
    sand.update(FakeKeys(KEY_BOW_AIM), (False, False, False), 1 / 60)
    arrow = sand.pop_arrow()
    assert arrow is not None
    assert arrow.roped is True

    arena = YaguarPlayer(200, GROUND_Y)
    _aim(arena, 800, arena.hurtbox.centery)
    for _ in range(int(BOW_NOCK / (1 / 60)) + 4):
        arena.update(FakeKeys(KEY_BOW_AIM), (False, False, False), 1 / 60)
    arena.update(FakeKeys(KEY_BOW_AIM, KEY_ATTACK), (True, False, False), 1 / 60)
    arena.update(FakeKeys(KEY_BOW_AIM), (False, False, False), 1 / 60)
    other = arena.pop_arrow()
    assert other is not None
    assert other.roped is False

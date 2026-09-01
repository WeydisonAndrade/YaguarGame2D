"""Arco e flecha: mira, carga, física em dt, colisão swept e um hit."""

from __future__ import annotations

import math

import pygame

from src.config import (
    BOW_DAMAGE_MAX,
    BOW_DAMAGE_MIN,
    BOW_GRAVITY,
    BOW_MAX_CHARGE,
    BOW_MAX_SPEED,
    BOW_MIN_SPEED,
    BOW_NOCK,
    BOW_WEAK_MULT,
    GROUND_Y,
    KEY_ATTACK,
    KEY_BOW_AIM,
    PLAYER_WALK_SPEED,
)
from src.entities import Arrow, SpectralJaguar, YaguarPlayer, set_physics_world
from tests.conftest import FakeKeys


def _aim(player: YaguarPlayer, world_x: float, world_y: float, monkeypatch) -> None:
    monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (int(world_x - player.camera_x), int(world_y)))


def _hold_bow(player: YaguarPlayer, monkeypatch, wx: float, wy: float, fire: bool = False, dt: float = 1 / 60):
    _aim(player, wx, wy, monkeypatch)
    keys = FakeKeys(KEY_BOW_AIM, KEY_ATTACK) if fire else FakeKeys(KEY_BOW_AIM)
    mouse = (fire, False, False)
    player.update(keys, mouse, dt)


def _nock_until_aim(player: YaguarPlayer, monkeypatch, wx: float, wy: float, dt: float = 1 / 60) -> None:
    """Avança a animação da aljava até a mira pronta."""
    steps = int(BOW_NOCK / dt) + 3
    for _ in range(steps):
        _hold_bow(player, monkeypatch, wx, wy, dt=dt)
        if player.bow_state == "aim":
            return
    raise AssertionError(f"nock não chegou na mira: {player.bow_state}")


def test_sacar_arco_tira_a_flecha_da_aljava(monkeypatch):
    player = YaguarPlayer(200, GROUND_Y)
    _hold_bow(player, monkeypatch, 800, player.hurtbox.centery)
    assert player.bow_state == "nock"
    assert player._pose_name == "bow_quiver"
    for _ in range(int((BOW_NOCK * 0.55) / (1 / 60)) + 1):
        _hold_bow(player, monkeypatch, 800, player.hurtbox.centery)
    assert player.bow_state == "nock"
    assert player._pose_name == "bow_nock"
    _nock_until_aim(player, monkeypatch, 800, player.hurtbox.centery)
    assert player.bow_state == "aim"
    assert player._pose_name == "bow_nock"
    assert player.facing == 1
    keys = FakeKeys(KEY_BOW_AIM, pygame.K_a)
    _aim(player, 800, player.hurtbox.centery, monkeypatch)
    player.update(keys, (False, False, False), 1 / 60)
    assert player.facing == -1


def test_nao_dispara_enquanto_saca_da_aljava(monkeypatch):
    player = YaguarPlayer(200, GROUND_Y)
    _hold_bow(player, monkeypatch, 800, player.hurtbox.centery)
    _hold_bow(player, monkeypatch, 800, player.hurtbox.centery, fire=True)
    _hold_bow(player, monkeypatch, 800, player.hurtbox.centery, fire=False)
    assert player.pop_arrow() is None
    assert player.bow_state == "nock"


def test_puxar_a_corda_usa_a_pose_de_tiro(monkeypatch):
    player = YaguarPlayer(200, GROUND_Y)
    _nock_until_aim(player, monkeypatch, 800, player.hurtbox.centery)
    _hold_bow(player, monkeypatch, 800, player.hurtbox.centery, fire=True)
    assert player.bow_state == "draw"
    assert player._pose_name == "bow"


def test_sacar_arco_entra_em_mira_e_vira_para_o_alvo(monkeypatch):
    player = YaguarPlayer(200, GROUND_Y)
    _nock_until_aim(player, monkeypatch, 800, player.hurtbox.centery)
    assert player.bow_state == "aim"
    assert player.facing == 1
    keys = FakeKeys(KEY_BOW_AIM, pygame.K_a)
    _aim(player, 800, player.hurtbox.centery, monkeypatch)
    player.update(keys, (False, False, False), 1 / 60)
    assert player.facing == -1


def test_mira_nao_vira_pelo_mouse(monkeypatch):
    """O cursor à direita não desvira quem já olha para a esquerda."""
    player = YaguarPlayer(400, GROUND_Y)
    player.facing = -1
    _nock_until_aim(player, monkeypatch, 900, player.hurtbox.centery)
    assert player.facing == -1
    assert abs(player.aim_angle - math.pi) < 0.05


def test_disparo_para_a_esquerda(monkeypatch):
    player = YaguarPlayer(400, GROUND_Y)
    player.facing = -1
    _nock_until_aim(player, monkeypatch, 900, player.hurtbox.centery)
    _hold_bow(player, monkeypatch, 900, player.hurtbox.centery, fire=True)
    _hold_bow(player, monkeypatch, 900, player.hurtbox.centery, fire=False)
    arrow = player.pop_arrow()
    assert arrow is not None
    assert arrow.vx < 0
    assert arrow.fx < player.rect.centerx

    player = YaguarPlayer(200, GROUND_Y)
    _nock_until_aim(player, monkeypatch, 400, 80)
    assert player.bow_state == "aim"
    assert player.facing == 1
    assert abs(player.aim_angle) < 0.01
    assert player._pose_name == "bow_nock"


def test_movimento_reduz_durante_a_mira(monkeypatch):
    player = YaguarPlayer(200, GROUND_Y)
    _nock_until_aim(player, monkeypatch, 800, player.hurtbox.centery)
    x0 = player.rect.midbottom[0]
    keys = FakeKeys(KEY_BOW_AIM, pygame.K_d)
    _aim(player, 800, player.hurtbox.centery, monkeypatch)
    player.update(keys, (False, False, False), 1 / 60)
    walked = player.rect.midbottom[0] - x0
    assert 0 < walked < int(PLAYER_WALK_SPEED)


def test_soltar_q_cancela_a_mira(monkeypatch):
    player = YaguarPlayer(200, GROUND_Y)
    _nock_until_aim(player, monkeypatch, 800, player.hurtbox.centery)
    assert player.bow_state == "aim"
    player.update(FakeKeys(), (False, False, False), 1 / 60)
    assert player.bow_state is None


def test_tiro_rapido_e_carregado(monkeypatch):
    player = YaguarPlayer(200, GROUND_Y)
    _nock_until_aim(player, monkeypatch, 800, player.hurtbox.centery)
    _hold_bow(player, monkeypatch, 800, player.hurtbox.centery, fire=True, dt=1 / 60)
    _hold_bow(player, monkeypatch, 800, player.hurtbox.centery, fire=False, dt=1 / 60)
    tap = player.pop_arrow()
    assert tap is not None
    assert tap.damage == BOW_DAMAGE_MIN
    assert math.isclose(math.hypot(tap.vx, tap.vy), BOW_MIN_SPEED, rel_tol=0.08)
    assert player.bow_state == "shoot"

    charged = YaguarPlayer(200, GROUND_Y)
    _nock_until_aim(charged, monkeypatch, 800, charged.hurtbox.centery)
    steps = int(BOW_MAX_CHARGE / (1 / 60)) + 2
    for _ in range(steps):
        _hold_bow(charged, monkeypatch, 800, charged.hurtbox.centery, fire=True, dt=1 / 60)
    assert charged.bow_charge == 1.0
    _hold_bow(charged, monkeypatch, 800, charged.hurtbox.centery, fire=False, dt=1 / 60)
    full = charged.pop_arrow()
    assert full is not None
    assert full.damage == BOW_DAMAGE_MAX
    assert math.isclose(math.hypot(full.vx, full.vy), BOW_MAX_SPEED, rel_tol=0.08)


def test_um_input_nao_spawna_duas_flechas(monkeypatch):
    player = YaguarPlayer(200, GROUND_Y)
    _nock_until_aim(player, monkeypatch, 800, player.hurtbox.centery)
    _hold_bow(player, monkeypatch, 800, player.hurtbox.centery, fire=True)
    _hold_bow(player, monkeypatch, 800, player.hurtbox.centery, fire=False)
    first = player.pop_arrow()
    assert first is not None
    _hold_bow(player, monkeypatch, 800, player.hurtbox.centery, fire=False)
    assert player.pop_arrow() is None


def test_lanca_continua_funcionando_sem_q():
    player = YaguarPlayer(200, GROUND_Y)
    player.queue_attack(heavy=False)
    player.update(FakeKeys(), (False, False, False), 1 / 60)
    assert player.attacking is True
    assert player.bow_state is None


def test_dano_cancela_o_arco(monkeypatch):
    player = YaguarPlayer(200, GROUND_Y)
    _nock_until_aim(player, monkeypatch, 800, player.hurtbox.centery)
    player.take_damage(10, source_x=400)
    assert player.bow_state is None


def test_flecha_nasce_na_ponta_da_pose_de_tiro(monkeypatch):
    player = YaguarPlayer(200, GROUND_Y)
    _nock_until_aim(player, monkeypatch, 800, player.hurtbox.centery)
    _hold_bow(player, monkeypatch, 800, player.hurtbox.centery, fire=True)
    ax, ay = player.bow_anchor()
    sx, sy = player.arrow_spawn()
    assert player._pose_name == "bow"
    assert ax > player.rect.centerx + 40
    assert ay < player.rect.centery
    assert (sx, sy) == (ax, ay)


def test_apos_o_tiro_volta_a_sacar_da_aljava(monkeypatch):
    from src.config import BOW_RECOVER

    player = YaguarPlayer(200, GROUND_Y)
    _nock_until_aim(player, monkeypatch, 800, player.hurtbox.centery)
    _hold_bow(player, monkeypatch, 800, player.hurtbox.centery, fire=True)
    _hold_bow(player, monkeypatch, 800, player.hurtbox.centery, fire=False)
    assert player.pop_arrow() is not None
    steps = int(BOW_RECOVER / (1 / 60)) + 3
    for _ in range(steps):
        _hold_bow(player, monkeypatch, 800, player.hurtbox.centery)
    assert player.bow_state == "nock"
    assert player._pose_name == "bow_quiver"


def test_fisica_independe_do_fps():
    a60 = Arrow(100, 200, 0.0, 400, 10)
    a30 = Arrow(100, 200, 0.0, 400, 10)
    for _ in range(60):
        a60.update(1 / 60)
    for _ in range(30):
        a30.update(1 / 30)
    assert abs(a60.fx - a30.fx) < 6
    assert abs(a60.fy - a30.fy) < 2
    assert abs(a60.fy - 200) < 1


def test_disparo_e_linear_e_usa_a_flecha_isolada():
    assert BOW_GRAVITY == 0.0
    arrow = Arrow(100, 200, 0.0, 1080, 12)
    arrow.update(1 / 60)
    assert arrow.fy == 200
    assert arrow.fx > 100
    assert 5 <= arrow.image.get_height() <= 10
    assert 40 <= arrow.image.get_width() <= 100


def test_rotacao_acompanha_a_velocidade():
    arrow = Arrow(0, 0, 0.0, 400, 10)
    arrow.vx, arrow.vy = 0.0, 200.0
    arrow._orient()
    assert abs(arrow.image.get_rect().width - arrow.image.get_rect().height) >= 0
    ang = math.degrees(math.atan2(arrow.vy, arrow.vx))
    assert abs(ang - 90) < 1


def test_swept_nao_atravessa_inimigo():
    jaguar = SpectralJaguar(400, GROUND_Y)
    arrow = Arrow(120, jaguar.hurtbox.centery, 0.0, 9000, 12)
    group = pygame.sprite.Group(arrow)
    hit = False
    for _ in range(8):
        arrow.update(1 / 30)
        got, _weak = arrow.try_hit_enemy(jaguar)
        if got:
            hit = True
            assert arrow.resolve_hit(False) == 12
            assert arrow.resolve_hit(False) == 0
            break
    group.update(1 / 30)
    assert hit is True


def test_flecha_crava_no_chao():
    from src.config import PLATFORMS, SCREEN_WIDTH

    set_physics_world(PLATFORMS, SCREEN_WIDTH, allow_pits=False)
    arrow = Arrow(200, GROUND_Y - 40, math.pi / 2, 80, 10)
    stuck = False
    for _ in range(90):
        arrow.update(1 / 60)
        if arrow.stuck:
            stuck = True
            break
    assert stuck is True


def test_ponto_fraco_multiplica_dano():
    jaguar = SpectralJaguar(400, GROUND_Y)
    weak = jaguar.weak_hurtbox
    assert weak is not None
    arrow = Arrow(weak.centerx - 4, weak.centery, 0.0, 10, 10)
    arrow.prev_x, arrow.prev_y = weak.centerx - 20, weak.centery
    arrow.fx, arrow.fy = weak.centerx + 4, weak.centery
    hit, is_weak = arrow.try_hit_enemy(jaguar)
    assert hit is True
    assert is_weak is True
    assert arrow.resolve_hit(True) == int(round(10 * BOW_WEAK_MULT))


def test_municao_limitada_pode_ser_ligada_depois(monkeypatch):
    player = YaguarPlayer(200, GROUND_Y)
    player.arrow_ammo = 0
    _nock_until_aim(player, monkeypatch, 800, player.hurtbox.centery)
    _hold_bow(player, monkeypatch, 800, player.hurtbox.centery, fire=True)
    _hold_bow(player, monkeypatch, 800, player.hurtbox.centery, fire=False)
    assert player.pop_arrow() is None
    assert player.arrow_ammo == 0


def test_poses_em_pe_mantem_o_tamanho_do_corpo():
    from PIL import Image

    from src.player_anim import _silhouette_body_height, load_player_frames

    frames = load_player_frames()
    idle = frames["idle"]
    idle_img = Image.frombytes("RGBA", idle.get_size(), pygame.image.tobytes(idle, "RGBA"))
    ref = _silhouette_body_height(idle_img)
    for name in ("run1", "run2", "attack", "defend", "bow", "bow_quiver", "bow_nock"):
        if name not in frames:
            continue
        surf = frames[name]
        img = Image.frombytes("RGBA", surf.get_size(), pygame.image.tobytes(surf, "RGBA"))
        body = _silhouette_body_height(img)
        assert abs(body - ref) <= 10, f"{name} body={body} idle={ref}"

"""Base da pirâmide: regras de combate do jogador, hitbox e projétil."""

from __future__ import annotations

import math

import pygame
import pytest

from src.config import (
    BLOCK_DAMAGE_FACTOR,
    GROUND_Y,
    ONCA_RUN_SPEED,
    ONCA_WALK_SPEED,
    PLAYER_ATTACK_FRAMES,
    PLAYER_INVULN_FRAMES,
    PLAYER_WALK_SPEED,
)
from src.entities import AttackHitbox, HerbItem, TreeTrunk, YaguarPlayer, SpectralJaguar
from tests.conftest import FakeKeys


def test_dano_cheio_aplica_i_frames_e_nao_vai_abaixo_de_zero():
    player = YaguarPlayer(150, GROUND_Y)
    dealt = player.take_damage(40, source_x=400)
    assert dealt == 40
    assert player.health == 60
    assert player.invuln == PLAYER_INVULN_FRAMES

    ignored = player.take_damage(40, source_x=400)
    assert ignored == 0
    assert player.health == 60

    player.invuln = 0
    player.take_damage(999, source_x=400)
    assert player.health == 0


def test_bloqueio_reduz_dano_e_ganha_recuperacao_curta():
    player = YaguarPlayer(150, GROUND_Y)
    player.blocking = True
    dealt = player.take_damage(10, source_x=400)
    assert dealt == pytest.approx(10 * BLOCK_DAMAGE_FACTOR)
    assert player.health == pytest.approx(100 - 10 * BLOCK_DAMAGE_FACTOR)
    assert player.invuln > 0
    assert player.invuln < PLAYER_INVULN_FRAMES


def test_ataque_leve_cria_hitbox_na_janela_ativa():
    player = YaguarPlayer(200, GROUND_Y)
    player.queue_attack(heavy=False)
    idle = FakeKeys()
    spawned = None
    for _ in range(PLAYER_ATTACK_FRAMES + 2):
        player.update(idle, (False, False, False))
        spawned = player.pop_strike() or spawned
    assert spawned is not None
    assert spawned.damage == 18
    assert spawned.rect.width > 0


def test_ataque_pesado_sem_garra_e_ignorado():
    player = YaguarPlayer(200, GROUND_Y)
    assert player.has_garra_espiritual is False
    player.queue_attack(heavy=True)
    assert player.queued_attack is None
    player.update(FakeKeys(), (False, False, False))
    assert player.attacking is False


def test_ataque_pesado_com_garra_tem_alcance_e_dano_maiores():
    player = YaguarPlayer(200, GROUND_Y)
    player.has_garra_espiritual = True
    player.queue_attack(heavy=True)
    spawned = None
    for _ in range(PLAYER_ATTACK_FRAMES + 2):
        player.update(FakeKeys(), (False, False, False))
        spawned = player.pop_strike() or spawned
    assert spawned is not None
    assert spawned.damage == 34
    assert spawned.rect.width == 86


def test_cooldown_impede_novo_golpe_imediatamente():
    player = YaguarPlayer(200, GROUND_Y)
    player.queue_attack(heavy=False)
    player.update(FakeKeys(), (False, False, False))
    assert player.attacking is True
    player.queue_attack(heavy=False)
    assert player.queued_attack is None


def test_rugido_a_cada_dez_golpes_de_lanca():
    player = YaguarPlayer(200, GROUND_Y)
    for _ in range(9):
        player._begin_attack(heavy=False)
        assert player.spear_magic == 0
    player._begin_attack(heavy=False)
    assert player.spear_attacks == 10
    assert player.spear_magic == 56


def test_andar_para_direita_avanca_e_vira_o_facing():
    player = YaguarPlayer(200, GROUND_Y)
    x0 = player.rect.midbottom[0]
    player.update(FakeKeys(pygame.K_d), (False, False, False))
    # O rect.x muda com a largura do frame; a âncora dos pés é o que anda.
    assert player.rect.midbottom[0] > x0
    assert player.facing == 1
    assert player.rect.midbottom[0] - x0 == int(PLAYER_WALK_SPEED)


def test_hitbox_some_depois_da_vida_util():
    group = pygame.sprite.Group()
    hb = AttackHitbox(10, 10, 20, 20, 18)
    group.add(hb)
    for _ in range(8):
        group.update()
    assert len(group) == 0


def test_tronco_voa_na_direcao_do_alvo_e_some_fora_da_tela():
    trunk = TreeTrunk(100, 200, (300, 200))
    assert trunk.vx > 0
    assert abs(trunk.vy) < 0.01
    assert math.isclose(math.hypot(trunk.vx, trunk.vy), 10.5, rel_tol=1e-6)

    group = pygame.sprite.Group(TreeTrunk(80, 200, (-400, 200)))
    for _ in range(80):
        group.update()
        if len(group) == 0:
            break
    assert len(group) == 0


def test_erva_nasce_com_os_pes_no_chao():
    herb = HerbItem(220, GROUND_Y)
    assert herb.rect.bottom == GROUND_Y


def _mean_opaque_rgb(surf: pygame.Surface) -> tuple[float, float, float]:
    buf = pygame.image.tostring(surf, "RGBA")
    rs = gs = bs = n = 0
    for i in range(0, len(buf), 4):
        if buf[i + 3] > 80:
            rs += buf[i]
            gs += buf[i + 1]
            bs += buf[i + 2]
            n += 1
    return rs / n, gs / n, bs / n


def test_primeira_onca_e_pintada_e_mais_lenta():
    pintada = SpectralJaguar(800, GROUND_Y, kind="normal")
    espectral = SpectralJaguar(800, GROUND_Y, kind="espectral")

    assert pintada.kind == "normal"
    assert pintada.walk_speed < ONCA_WALK_SPEED
    assert pintada.walk_speed < espectral.walk_speed
    assert pintada.run_speed < ONCA_RUN_SPEED
    assert pintada.run_speed < espectral.run_speed
    assert pintada.recover_cooldown > espectral.recover_cooldown
    assert pintada.strike_frames > espectral.strike_frames
    assert pintada.attack_range < espectral.attack_range

    gold = _mean_opaque_rgb(pintada.frames["idle"])
    lava = _mean_opaque_rgb(espectral.frames["idle"])
    assert gold[0] > 110
    assert gold[1] > 70
    assert gold[1] > gold[2]
    assert gold[1] > lava[1]


def test_segunda_onca_e_pantera_negra():
    pantera = SpectralJaguar(800, GROUND_Y, kind="pantera")
    pintada = SpectralJaguar(800, GROUND_Y, kind="normal")
    espectral = SpectralJaguar(800, GROUND_Y, kind="espectral")

    assert pantera.kind == "pantera"
    black = _mean_opaque_rgb(pantera.frames["idle"])
    gold = _mean_opaque_rgb(pintada.frames["idle"])
    lava = _mean_opaque_rgb(espectral.frames["idle"])
    lum_black = sum(black) / 3
    lum_gold = sum(gold) / 3
    assert lum_black < lum_gold
    assert lum_black < 55
    assert black[0] < lava[0]
    assert black[0] < 55

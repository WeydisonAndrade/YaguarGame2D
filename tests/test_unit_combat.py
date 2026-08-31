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


def test_tres_oncas_usam_o_aspecto_espectral():
    pintada = SpectralJaguar(800, GROUND_Y, kind="normal")
    pantera = SpectralJaguar(800, GROUND_Y, kind="pantera")
    espectral = SpectralJaguar(800, GROUND_Y, kind="espectral")

    for cat in (pintada, pantera, espectral):
        assert cat.walk_speed == ONCA_WALK_SPEED
        assert cat.run_speed == ONCA_RUN_SPEED
        assert cat.run_distance == espectral.run_distance
        assert cat.attack_range == espectral.attack_range
        assert cat.recover_cooldown == espectral.recover_cooldown
        assert cat.strike_frames == espectral.strike_frames
        assert cat.bite_lunge == espectral.bite_lunge
        assert cat.charge_lunge == espectral.charge_lunge
        assert cat.anim_run == espectral.anim_run
        assert cat.anim_walk == espectral.anim_walk
        assert set(cat.frames) == set(espectral.frames)

    for pose in ("idle", "claw", "bite", "run1", "run2"):
        ref = pygame.image.tostring(espectral.frames[pose], "RGBA")
        assert pygame.image.tostring(pintada.frames[pose], "RGBA") == ref
        assert pygame.image.tostring(pantera.frames[pose], "RGBA") == ref

    player = (200, GROUND_Y - 55)
    for _ in range(40):
        pintada.update(player)
        pantera.update(player)
        espectral.update(player)
    assert pintada.rect.centerx == pantera.rect.centerx == espectral.rect.centerx
    assert pintada.running is pantera.running is espectral.running is True
    assert pintada.action == pantera.action == espectral.action

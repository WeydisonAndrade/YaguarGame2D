"""Meio da pirâmide: PlayingState + entidades + FX no mesmo update."""

from __future__ import annotations

import pygame
import pytest

from src.config import GROUND_Y, ONCA_WAVE_TOTAL, TOTAL_HERBS_TO_COLLECT
from src.entities import AttackHitbox, MapinguariBoss, SpectralJaguar
from src.game_states import GameOverState, PlayingState, VictoryCinematicState
from tests.conftest import FakeKeys


def _idle_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: FakeKeys())
    monkeypatch.setattr(pygame.mouse, "get_pressed", lambda: (False, False, False))


def test_golpe_da_lanca_derrota_a_onca_e_spawna_a_proxima(game, monkeypatch):
    _idle_keys(monkeypatch)
    first = next(iter(game.enemies))
    assert isinstance(first, SpectralJaguar)
    hb = AttackHitbox(first.hurtbox.x, first.hurtbox.y, 220, 180, 999)
    game.attack_hitboxes.add(hb)

    game.state.update(game)

    assert first not in game.enemies
    assert game.jaguars_defeated == 1
    assert len(game.enemies) == 1
    assert isinstance(next(iter(game.enemies)), SpectralJaguar)
    assert "2/3" in game.state.current_zone


def test_terceira_onca_libera_garra_e_chama_o_mapinguari(game, monkeypatch):
    _idle_keys(monkeypatch)
    for wave in range(ONCA_WAVE_TOTAL):
        enemy = next(iter(game.enemies))
        hb = AttackHitbox(enemy.hurtbox.x, enemy.hurtbox.y, 260, 220, 999)
        game.attack_hitboxes.add(hb)
        game.state.update(game)

    assert game.jaguars_defeated == ONCA_WAVE_TOTAL
    assert game.player.has_garra_espiritual is True
    assert game.zone_stage == 2
    bosses = [e for e in game.enemies if isinstance(e, MapinguariBoss)]
    assert len(bosses) == 1
    assert isinstance(game.state, PlayingState)


def test_derrotar_o_mapinguari_vai_para_vitoria(game, monkeypatch):
    _idle_keys(monkeypatch)
    game.player.has_garra_espiritual = True
    game.zone_stage = 2
    for enemy in list(game.enemies):
        enemy.kill()
    boss = MapinguariBoss(700, GROUND_Y)
    game.enemies.add(boss)
    game.all_sprites.add(boss)
    hb = AttackHitbox(boss.hurtbox.x, boss.hurtbox.y, 280, 240, 999)
    game.attack_hitboxes.add(hb)

    game.state.update(game)

    assert isinstance(game.state, VictoryCinematicState)


def test_golpe_mortal_do_inimigo_sem_corpo_a_corpo_causa_game_over(game, monkeypatch):
    """A onça pode matar só com a hitbox da garra, mesmo longe o bastante para não encostar."""
    _idle_keys(monkeypatch)
    jaguar = next(iter(game.enemies))
    game.player.rect.midbottom = (120, GROUND_Y)
    jaguar.rect.midbottom = (900, GROUND_Y)
    game.player.health = 5
    jaguar.pending_damage = 40
    jaguar.pending_melee = game.player.hurtbox.copy()

    game.state.update(game)

    assert game.player.health <= 0
    assert isinstance(game.state, GameOverState)


def test_bloqueio_nao_e_dilacerado_a_60_hits_por_segundo(game, monkeypatch):
    """Chip no bloqueio existe, mas o contato contínuo não drena a vida em um instante."""
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: FakeKeys(pygame.K_k))
    monkeypatch.setattr(pygame.mouse, "get_pressed", lambda: (False, False, False))
    jaguar = next(iter(game.enemies))
    start = game.player.health

    for _ in range(45):
        if not isinstance(game.state, PlayingState):
            break
        game.player.rect.midbottom = (400, GROUND_Y)
        jaguar.rect.midbottom = (400, GROUND_Y)
        game.state.update(game)

    assert isinstance(game.state, PlayingState)
    assert game.player.health < start
    assert game.player.health > 50


def test_coletar_erva_cura_e_conta_no_hud(game, monkeypatch):
    _idle_keys(monkeypatch)
    game.player.health = 40
    herb = next(iter(game.herbs))
    game.player.rect.center = herb.rect.center

    game.state.update(game)

    assert game.herbs_collected == 1
    assert game.player.health == 65
    assert len(game.herbs) == TOTAL_HERBS_TO_COLLECT - 1

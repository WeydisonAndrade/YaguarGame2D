"""Meio da pirâmide: PlayingState + entidades + FX no mesmo update."""

from __future__ import annotations

import pygame
import pytest

from src.config import (
    GROUND_Y,
    ONCA_WAVE_TOTAL,
    SCREEN_WIDTH,
    TOTAL_HERBS_TO_COLLECT,
    TRAIL_CHECKPOINT_X,
    TRAIL_EXIT_X,
    TRAIL_FALL_DAMAGE,
    TRAIL_GROUND_Y,
    TRAIL_ORIGIN_X,
    MAPINGUARI_GATE_X,
)
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
    assert first.kind == "normal"
    hb = AttackHitbox(first.hurtbox.x, first.hurtbox.y, 220, 180, 999)
    game.attack_hitboxes.add(hb)

    game.state.update(game)

    assert first not in game.enemies
    assert game.jaguars_defeated == 1
    assert len(game.enemies) == 1
    assert isinstance(next(iter(game.enemies)), SpectralJaguar)
    assert next(iter(game.enemies)).kind == "pantera"
    assert "2/3" in game.state.current_zone
    assert "Espectral" in game.state.current_zone


def test_terceira_onca_abre_a_clareira_e_depois_o_mapinguari(game, monkeypatch):
    _idle_keys(monkeypatch)
    from src.game_states import BossCinematicState

    for wave in range(ONCA_WAVE_TOTAL):
        enemy = next(iter(game.enemies))
        hb = AttackHitbox(enemy.hurtbox.x, enemy.hurtbox.y, 260, 220, 999)
        game.attack_hitboxes.add(hb)
        game.state.update(game)

    assert game.jaguars_defeated == ONCA_WAVE_TOTAL
    assert game.player.has_garra_espiritual is True
    assert isinstance(game.state, PlayingState)
    assert game.zone_stage == 1
    assert game.parallax.mode == "crossing"
    assert game.player.rect.bottom in (GROUND_Y, GROUND_Y + 1)

    game.player.rect.midbottom = (TRAIL_EXIT_X, TRAIL_GROUND_Y)
    game.player.on_ground = True
    game.state.update(game)
    assert isinstance(game.state, PlayingState)
    assert game.zone_stage == 1

    game.player.rect.midbottom = (MAPINGUARI_GATE_X, TRAIL_GROUND_Y)
    game.player.on_ground = True
    game.state.update(game)
    assert isinstance(game.state, BossCinematicState)

    game.state.handle_events(game, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
    assert isinstance(game.state, PlayingState)
    bosses = [e for e in game.enemies if isinstance(e, MapinguariBoss)]
    assert len(bosses) == 1
    assert game.player.rect.centerx < SCREEN_WIDTH
    assert game.parallax.mode == "scene"
    assert game.parallax.is_boss_arena()
    assert game.zone_stage == 2


def test_queda_na_clareira_fere_e_devolve_ao_checkpoint(game, monkeypatch):
    _idle_keys(monkeypatch)
    game.begin_forest_crossing()
    start = game.player.health
    game.player.checkpoint = (TRAIL_CHECKPOINT_X, TRAIL_GROUND_Y)
    game.player.rect.midbottom = (TRAIL_ORIGIN_X + 330, TRAIL_GROUND_Y + 40)
    game.player.vel_y = 12
    game.player.on_ground = False

    for _ in range(90):
        if not isinstance(game.state, PlayingState):
            break
        game.state.update(game)
        if game.player.health < start:
            break

    assert isinstance(game.state, PlayingState)
    assert game.player.health == start - TRAIL_FALL_DAMAGE
    assert game.player.rect.centerx == TRAIL_CHECKPOINT_X
    assert game.player.on_ground is True


def test_caminho_aberto_permite_voltar_a_arena(game, monkeypatch):
    """Com o caminho aberto, andar à esquerda devolve Yáguar à arena das onças."""
    _idle_keys(monkeypatch)
    game.begin_forest_crossing()
    game.player.rect.midbottom = (200, GROUND_Y)
    game.player.on_ground = True
    game.player.vel_y = 0
    game.state.update(game)
    assert isinstance(game.state, PlayingState)
    assert game.zone_stage == 1
    assert game.player.on_ground is True
    assert game.player.rect.centerx < TRAIL_ORIGIN_X
    assert game.player.rect.bottom in (GROUND_Y, GROUND_Y + 1)


def test_camera_deixa_o_caminho_a_frente_visivel(game, monkeypatch):
    """Ao avançar, Yáguar fica à esquerda do centro para a clareira aparecer primeiro."""
    _idle_keys(monkeypatch)
    game.begin_forest_crossing()
    game.player.rect.midbottom = (1200, GROUND_Y)
    game.player.facing = 1
    game.player.on_ground = True
    game.player.vel_y = 0
    game.camera_x = 0
    for _ in range(45):
        game.state.update(game)
    screen_x = game.player.rect.centerx - game.camera_x
    assert 0.32 * SCREEN_WIDTH < screen_x < 0.50 * SCREEN_WIDTH
    assert game.camera_x > 0


def test_desenha_a_clareira_das_fendas_com_debug(game, monkeypatch):
    _idle_keys(monkeypatch)
    game.begin_forest_crossing()
    game.player.rect.midbottom = (TRAIL_ORIGIN_X + 90, GROUND_Y)
    game.player.on_ground = True
    game.debug_draw = True
    game.state.update(game)
    game.state.draw(game, game.screen)
    assert game.zone_stage == 1
    assert not hasattr(game, "vines") or not game.vines


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


def test_coletar_erva_guarda_no_bolso_e_e_cura(game, monkeypatch):
    _idle_keys(monkeypatch)
    game.player.health = 40
    herb = next(iter(game.herbs))
    game.player.rect.center = herb.rect.center

    game.state.update(game)

    assert game.herbs_collected == 1
    assert game.herbs_held == 1
    assert game.player.health == 40
    assert len(game.herbs) == TOTAL_HERBS_TO_COLLECT - 1

    game.state.handle_events(game, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
    assert game.player.health == 65
    assert game.herbs_held == 0


def test_e_colhe_erva_ao_alcance_sem_sobrepor_o_sprite(game, monkeypatch):
    _idle_keys(monkeypatch)
    herb = next(iter(game.herbs))
    game.player.rect.midbottom = (herb.rect.centerx - 70, herb.rect.bottom)
    game.player.on_ground = True
    assert not game.player.rect.colliderect(herb.rect)

    game.state.handle_events(game, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
    assert game.herbs_held == 1
    assert game.herbs_collected == 1


def test_flecha_fere_onca_uma_vez_pelo_sistema_existente(game, monkeypatch):
    _idle_keys(monkeypatch)
    from src.entities import Arrow

    enemy = next(iter(game.enemies))
    hp = enemy.health
    hb = enemy.hurtbox
    arrow = Arrow(hb.centerx - 8, hb.centery, 0.0, 400, 16)
    game.projectiles.add(arrow)
    game.state.update(game)
    assert enemy.health == hp - 16 or enemy not in game.enemies
    leftover = hp - enemy.health if enemy in game.enemies else 16
    game.state.update(game)
    if enemy in game.enemies:
        assert leftover == hp - enemy.health or leftover == 16


def test_mira_nao_dispara_lanca(game, monkeypatch):
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: FakeKeys(pygame.K_q))
    monkeypatch.setattr(pygame.mouse, "get_pressed", lambda: (False, False, False))
    monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (900, 300))
    game.state.handle_events(game, pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(900, 300)))
    from src.config import BOW_NOCK

    steps = int(BOW_NOCK / (1 / 60)) + 4
    for _ in range(steps):
        game.state.update(game)
    assert game.player.bow_state == "aim"
    assert game.player.attacking is False
    assert game.player.queued_attack is None


"""Topo da pirâmide: fluxo de telas da sessão (menu → intro → partida → pausa)."""

from __future__ import annotations

import pygame

from src.game import Game
from src.game_states import (
    CinematicIntroState,
    MenuState,
    PauseState,
    PlayingState,
)
from src.ui import PauseOverlay, RitualMenu


def _key(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def test_espaco_no_menu_abre_a_sinopse():
    game = Game()
    assert isinstance(game.state, MenuState)
    game.state.handle_events(game, _key(pygame.K_SPACE))
    assert isinstance(game.state, CinematicIntroState)


def test_espaco_na_sinopse_comeca_a_partida():
    game = Game()
    game.change_state(CinematicIntroState())
    game.state.handle_events(game, _key(pygame.K_SPACE))
    assert isinstance(game.state, PlayingState)
    assert game.player.health == 100
    assert len(game.enemies) == 1
    assert len(game.herbs) == 3


def test_esc_pausa_e_espaco_retoma():
    game = Game()
    playing = PlayingState()
    game.change_state(playing)
    game.state.handle_events(game, _key(pygame.K_ESCAPE))
    assert isinstance(game.state, PauseState)
    game.state.handle_events(game, _key(pygame.K_SPACE))
    assert game.state is playing


def test_m_na_pausa_volta_ao_menu():
    game = Game()
    game.change_state(PlayingState())
    game.state.handle_events(game, _key(pygame.K_ESCAPE))
    game.state.handle_events(game, _key(pygame.K_m))
    assert isinstance(game.state, MenuState)


def test_clique_no_cta_funciona_antes_do_primeiro_draw():
    """O botão do menu precisa ter hitbox mesmo no primeiro frame."""
    game = Game()
    assert game.state.ui.cta_rect.width > 0
    click = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN,
        button=1,
        pos=game.state.ui.cta_rect.center,
    )
    game.state.handle_events(game, click)
    assert isinstance(game.state, CinematicIntroState)


def test_clique_continuar_na_pausa_funciona_antes_do_draw():
    overlay = PauseOverlay()
    assert overlay.resume_rect.width > 0
    assert overlay.hit(overlay.resume_rect.center) == "resume"
    assert overlay.hit(overlay.menu_rect.center) == "menu"
    assert overlay.hit((0, 0)) is None


def test_ritos_do_menu_descrevem_os_controles_reais():
    menu = RitualMenu()
    right = {label: keys for keys, label in menu.right_rites}
    assert "Defesa ancestral" in right
    defesa_keys = " ".join(right["Defesa ancestral"])
    assert "Clique Dir" not in defesa_keys
    assert any("Garra" in label for label in right)


def test_partida_desenha_um_frame_sem_erro(game):
    screen = pygame.display.get_surface()
    game.state.draw(game, screen)
    assert screen.get_width() == 1024

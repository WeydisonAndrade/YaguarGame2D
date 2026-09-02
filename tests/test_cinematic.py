"""Cinemática da introdução: carregamento, avanço e término."""

from __future__ import annotations

import pygame

from src.cinematic import CinematicSequence
from src.config import CINEMATIC_FADE_FRAMES, CINEMATIC_HOLD_FRAMES, GROUND_Y
from src.game import Game
from src.game_states import CinematicIntroState, PlayingState, SandCinematicState, BossCinematicState


def _click(pos=(512, 300)) -> pygame.event.Event:
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)


def test_cinematica_carrega_os_seis_quadros():
    seq = CinematicSequence()
    assert seq.shot_count == 6
    assert seq.done is False
    assert seq.index == 0


def test_cinematica_skip_encerra_na_hora():
    seq = CinematicSequence()
    seq.skip()
    assert seq.done is True


def test_cinematica_avanca_e_termina_no_ultimo_quadro():
    seq = CinematicSequence()
    for _ in range(5):
        seq.advance()
        assert seq.done is False
    seq.advance()
    assert seq.done is True


def test_ultimo_quadro_termina_depois_do_fade():
    seq = CinematicSequence()
    seq.index = seq.shot_count - 1
    seq.timer = CINEMATIC_HOLD_FRAMES + CINEMATIC_FADE_FRAMES
    seq.update()
    assert seq.done is True


def test_clique_avanca_um_quadro_sem_comecar_a_partida():
    game = Game()
    game.change_state(CinematicIntroState())
    game.state.handle_events(game, _click())
    assert isinstance(game.state, CinematicIntroState)
    assert game.state.cine.index == 1


def test_cinematica_concluida_abre_a_partida():
    game = Game()
    game.change_state(CinematicIntroState())
    game.state.cine.skip()
    game.state.update(game)
    assert isinstance(game.state, PlayingState)


def test_partida_encerra_a_trilha_epica_da_cinematica():
    from src import audio

    assert audio.CINEMATIC_TRACK.is_file()
    game = Game()
    game.change_state(CinematicIntroState())
    if audio._current == "cinematic":
        game.state.handle_events(
            game, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
        )
        assert audio._current == "fight"
        assert isinstance(game.state, PlayingState)


def test_cinematica_desenha_um_frame_sem_erro():
    game = Game()
    game.change_state(CinematicIntroState())
    screen = pygame.display.get_surface()
    game.state.draw(game, screen)
    assert screen.get_width() == 1024


def test_cinematica_do_mapinguari_carrega_sete_quadros():
    seq = CinematicSequence.mapinguari()
    assert seq.shot_count == 7
    assert seq.done is False
    assert "MAPINGUARI" in seq.kicker


def test_cinematica_da_areia_carrega_seis_quadros():
    seq = CinematicSequence.sand()
    assert seq.shot_count == 6
    assert seq.done is False
    assert "AREIA" in seq.kicker


def test_cinematica_da_areia_dispara_antes_das_pocas():
    from src.config import SAND_CINEMATIC_GATE_X

    game = Game()
    game.change_state(PlayingState())
    game.begin_forest_crossing()
    game.player.rect.midbottom = (SAND_CINEMATIC_GATE_X, GROUND_Y)
    game.player.on_ground = True
    game.state.update(game)
    assert isinstance(game.state, SandCinematicState)


def test_cinematica_da_areia_nao_repete():
    from src.config import SAND_CINEMATIC_GATE_X

    game = Game()
    game.change_state(PlayingState())
    game.begin_forest_crossing()
    game.sand_cinematic_done = True
    game.player.rect.midbottom = (SAND_CINEMATIC_GATE_X, GROUND_Y)
    game.player.on_ground = True
    game.state.update(game)
    assert isinstance(game.state, PlayingState)

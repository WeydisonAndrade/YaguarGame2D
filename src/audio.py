"""Música de fundo e efeitos sonoros (rugidos).

A trilha usa pygame.mixer.music (um canal só, em loop).
Os rugidos usam pygame.mixer.Sound para tocar por cima da música.
"""
from __future__ import annotations

from pathlib import Path

import pygame

# Caminhos relativos à pasta yaguar_game/, independentes do cwd.
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
MENU_TRACK = ASSETS_DIR / "music" / "musicStartAndMenu.mp3"
FIGHT_TRACK = ASSETS_DIR / "music" / "musicGamefight01.mp3"
MAPINGUARI_TRACK = ASSETS_DIR / "music" / "musicMapinguari.mp3"
CINEMATIC_TRACK = ASSETS_DIR / "cinematic_animation" / "epic_music01.mp3"
MAPINGUARI_ROAR = ASSETS_DIR / "sfx" / "MapinguariRugido01.mp3"
YAGUAR_ROAR = ASSETS_DIR / "sfx" / "roarYaguar01.mp3"
ONCA_ROAR = ASSETS_DIR / "sfx" / "roarOnca.mp3"

_current: str | None = None
_sounds: dict[str, pygame.mixer.Sound] = {}


def init() -> None:
    """Ajusta o mixer antes de pygame.init() para melhor suporte a MP3."""
    pygame.mixer.pre_init(44100, -16, 2, 1024)


def _play(track_id: str, path: Path, volume: float = 0.55, loops: int = -1) -> None:
    """Carrega a faixa; loops=-1 entra em ciclo, 0 toca uma vez."""
    global _current
    if _current == track_id and pygame.mixer.get_init() and pygame.mixer.music.get_busy():
        return
    if not path.is_file() or not pygame.mixer.get_init():
        return
    try:
        pygame.mixer.music.load(str(path))
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play(loops)
        _current = track_id
    except pygame.error:
        _current = None


def play_menu() -> None:
    """Tema do menu, da vitória e da derrota."""
    _play("menu", MENU_TRACK, 0.55)


def play_cinematic() -> None:
    """Tema épico da introdução; a partida encerra esta faixa."""
    _play("cinematic", CINEMATIC_TRACK, 0.62, loops=0)


def play_fight() -> None:
    """Tema das onças espectrais; substitui a trilha da cinemática."""
    _play("fight", FIGHT_TRACK, 0.5)


def play_mapinguari() -> None:
    """Tema da luta contra o Mapinguari."""
    _play("mapinguari", MAPINGUARI_TRACK, 0.52)


def _sfx(name: str, path: Path, volume: float) -> pygame.mixer.Sound | None:
    """Carrega o clipe uma vez e devolve a instância em cache."""
    cached = _sounds.get(name)
    if cached is not None:
        return cached
    if not path.is_file() or not pygame.mixer.get_init():
        return None
    try:
        snd = pygame.mixer.Sound(str(path))
        snd.set_volume(volume)
        _sounds[name] = snd
        return snd
    except pygame.error:
        return None


def play_mapinguari_roar() -> None:
    """Rugido do Mapinguari; não sobrepõe se o clipe ainda estiver tocando."""
    _play_sfx_once("mapinguari_roar", MAPINGUARI_ROAR, 0.88)


def play_yaguar_roar() -> None:
    """Rugido do Yáguar; não sobrepõe se o clipe ainda estiver tocando."""
    _play_sfx_once("yaguar_roar", YAGUAR_ROAR, 0.9)


def play_onca_roar() -> None:
    """Rugido da onça espectral ao surgir; não sobrepõe se o clipe ainda estiver tocando."""
    _play_sfx_once("onca_roar", ONCA_ROAR, 0.86)


def _play_sfx_once(name: str, path: Path, volume: float) -> None:
    """Toca o SFX só se nenhum canal já estiver reproduzindo o mesmo som."""
    snd = _sfx(name, path, volume)
    if snd is None:
        return
    for ch in range(pygame.mixer.get_num_channels()):
        channel = pygame.mixer.Channel(ch)
        if channel.get_busy() and channel.get_sound() is snd:
            return
    snd.play()


def stop(fade_ms: int = 700) -> None:
    """Encerra a trilha com fade; usado se a partida precisa silenciar o fundo."""
    global _current
    if _current is None or not pygame.mixer.get_init():
        return
    try:
        pygame.mixer.music.fadeout(fade_ms)
    except pygame.error:
        pygame.mixer.music.stop()
    _current = None

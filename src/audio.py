"""Música de fundo do jogo."""
from __future__ import annotations

from pathlib import Path

import pygame

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
MENU_TRACK = ASSETS_DIR / "music" / "musicStartAndMenu.mp3"
FIGHT_TRACK = ASSETS_DIR / "music" / "musicGamefight01.mp3"
MAPINGUARI_TRACK = ASSETS_DIR / "music" / "musicMapinguari.mp3"
MAPINGUARI_ROAR = ASSETS_DIR / "sfx" / "MapinguariRugido01.mp3"
YAGUAR_ROAR = ASSETS_DIR / "sfx" / "roarYaguar01.mp3"

_current: str | None = None
_sounds: dict[str, pygame.mixer.Sound] = {}


def init() -> None:
    pygame.mixer.pre_init(44100, -16, 2, 1024)


def _play(track_id: str, path: Path, volume: float = 0.55) -> None:
    global _current
    if _current == track_id and pygame.mixer.get_init() and pygame.mixer.music.get_busy():
        return
    if not path.is_file() or not pygame.mixer.get_init():
        return
    try:
        pygame.mixer.music.load(str(path))
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play(-1)
        _current = track_id
    except pygame.error:
        _current = None


def play_menu() -> None:
    """Tema do menu e da abertura. Não reinicia se já estiver tocando."""
    _play("menu", MENU_TRACK, 0.55)


def play_fight() -> None:
    """Tema da partida. Não reinicia se já estiver tocando."""
    _play("fight", FIGHT_TRACK, 0.5)


def play_mapinguari() -> None:
    """Tema da batalha contra o Mapinguari. Não reinicia se já estiver tocando."""
    _play("mapinguari", MAPINGUARI_TRACK, 0.52)


def _sfx(name: str, path: Path, volume: float) -> pygame.mixer.Sound | None:
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


def _play_sfx_once(name: str, path: Path, volume: float) -> None:
    snd = _sfx(name, path, volume)
    if snd is None:
        return
    for ch in range(pygame.mixer.get_num_channels()):
        channel = pygame.mixer.Channel(ch)
        if channel.get_busy() and channel.get_sound() is snd:
            return
    snd.play()


def stop(fade_ms: int = 700) -> None:
    global _current
    if _current is None or not pygame.mixer.get_init():
        return
    try:
        pygame.mixer.music.fadeout(fade_ms)
    except pygame.error:
        pygame.mixer.music.stop()
    _current = None

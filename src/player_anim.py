"""Recorta o fundo branco e carrega as poses do Yáguar."""

from __future__ import annotations

from collections import deque
from pathlib import Path

import pygame
from PIL import Image

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
PLAYER_DIR = ASSETS_DIR / "player"

SOURCE_DIR = Path(r"C:\Users\weydi\.cursor\projects\c-Users-weydi-Desktop-Nova-pasta\assets")
IDLE_SOURCE = SOURCE_DIR / "c__Users_weydi_AppData_Roaming_Cursor_User_workspaceStorage_1bd7cbd3559718fc58a727b7ea3b1a25_images_Protagonista-8067cf50-ebea-4906-aa1f-cc9fd7ea829b.jpg"

POSE_SOURCES = {
    "idle": IDLE_SOURCE,
    "run1": SOURCE_DIR / "yaguar_run1.png",
    "run2": SOURCE_DIR / "yaguar_run2.png",
    "crouch": SOURCE_DIR / "yaguar_crouch.png",
    "jump": SOURCE_DIR / "yaguar_jump.png",
    "attack": SOURCE_DIR / "yaguar_attack.png",
    "defend": SOURCE_DIR / "yaguar_defend.png",
}

TARGET_H = 168
WHITE = (255, 255, 255)
TOL = 34
SOFT = 20


def _dist(c0: tuple[int, int, int], c1: tuple[int, int, int]) -> float:
    return ((c0[0] - c1[0]) ** 2 + (c0[1] - c1[1]) ** 2 + (c0[2] - c1[2]) ** 2) ** 0.5


def _flood_knockout(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()
    seen = bytearray(w * h)
    q = deque([(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)])
    for x in range(0, w, max(1, w // 12)):
        q.append((x, 0))
        q.append((x, h - 1))
    for y in range(0, h, max(1, h // 12)):
        q.append((0, y))
        q.append((w - 1, y))

    while q:
        x, y = q.popleft()
        if x < 0 or y < 0 or x >= w or y >= h:
            continue
        i = y * w + x
        if seen[i]:
            continue
        seen[i] = 1
        r, g, b, a = px[x, y]
        d = _dist((r, g, b), WHITE)
        if d <= TOL:
            px[x, y] = (r, g, b, 0)
            q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
        elif d <= TOL + SOFT:
            px[x, y] = (r, g, b, int(a * ((d - TOL) / SOFT)))

    return img


def _autocrop(img: Image.Image, alpha_min: int = 20) -> Image.Image:
    bbox = img.getbbox()
    if not bbox:
        return img
    return img.crop(bbox)


def _fit_feet(img: Image.Image, height: int = TARGET_H) -> Image.Image:
    img = _autocrop(img)
    w, h = img.size
    if h == 0:
        return img
    scale = height / h
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    return img.resize((nw, nh), Image.Resampling.LANCZOS)


def prepare_player_sprites(force: bool = False) -> dict[str, Path]:
    PLAYER_DIR.mkdir(parents=True, exist_ok=True)
    out: dict[str, Path] = {}
    for name, source in POSE_SOURCES.items():
        dest = PLAYER_DIR / f"{name}.png"
        out[name] = dest
        if dest.exists() and not force:
            continue
        if not source.exists():
            continue
        cut = _flood_knockout(Image.open(source))
        cut = _fit_feet(cut, 140 if name == "crouch" else TARGET_H)
        cut.save(dest, "PNG")
    return out


def load_player_frames() -> dict[str, pygame.Surface]:
    prepare_player_sprites()
    frames: dict[str, pygame.Surface] = {}
    for name in POSE_SOURCES:
        path = PLAYER_DIR / f"{name}.png"
        if path.exists():
            frames[name] = pygame.image.load(str(path)).convert_alpha()
    if "idle" not in frames:
        raise FileNotFoundError("Sprite idle do Yáguar não encontrado.")
    return frames

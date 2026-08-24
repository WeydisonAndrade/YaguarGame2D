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
HOLE_MIN_AREA = 4
NEIGHBORS4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
NEIGHBORS8 = NEIGHBORS4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))


def _dist(c0: tuple[int, int, int], c1: tuple[int, int, int]) -> float:
    """Distância euclidiana no espaço RGB."""
    return ((c0[0] - c1[0]) ** 2 + (c0[1] - c1[1]) ** 2 + (c0[2] - c1[2]) ** 2) ** 0.5


def _is_background(r: int, g: int, b: int, a: int, tol: int) -> bool:
    """True se o pixel for transparente ou branco o bastante para ser fundo."""
    if a < 12:
        return True
    return _dist((r, g, b), WHITE) <= tol


def _apply_fade(px, x: int, y: int, r: int, g: int, b: int, a: int) -> None:
    d = _dist((r, g, b), WHITE)
    if d <= TOL or a < 12:
        px[x, y] = (r, g, b, 0)
    elif d <= TOL + SOFT:
        px[x, y] = (r, g, b, int(a * ((d - TOL) / SOFT)))


def _flood_knockout(img: Image.Image) -> Image.Image:
    """Remove o fundo branco a partir das bordas (flood fill) e depois as ilhas internas."""
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
        if not _is_background(r, g, b, a, TOL + SOFT):
            continue
        _apply_fade(px, x, y, r, g, b, a)
        for dx, dy in NEIGHBORS4:
            q.append((x + dx, y + dy))

    _punch_interior_white(px, w, h)
    return img


def _punch_interior_white(px, w: int, h: int) -> None:
    """Remove ilhas brancas presas entre arco, lança e corpo."""
    seen = bytearray(w * h)
    for y in range(h):
        for x in range(w):
            i = y * w + x
            if seen[i]:
                continue
            r, g, b, a = px[x, y]
            if a < 12 or _dist((r, g, b), WHITE) > TOL + SOFT:
                continue
            blob: list[tuple[int, int, int, int, int, int]] = []
            q = deque([(x, y)])
            seen[i] = 1
            while q:
                cx, cy = q.popleft()
                cr, cg, cb, ca = px[cx, cy]
                blob.append((cx, cy, cr, cg, cb, ca))
                for dx, dy in NEIGHBORS8:
                    nx, ny = cx + dx, cy + dy
                    if nx < 0 or ny < 0 or nx >= w or ny >= h:
                        continue
                    ni = ny * w + nx
                    if seen[ni]:
                        continue
                    nr, ng, nb, na = px[nx, ny]
                    if na < 12 or _dist((nr, ng, nb), WHITE) > TOL + SOFT:
                        continue
                    seen[ni] = 1
                    q.append((nx, ny))
            if len(blob) < HOLE_MIN_AREA:
                continue
            for bx, by, br, bg, bb, ba in blob:
                _apply_fade(px, bx, by, br, bg, bb, ba)


def _autocrop(img: Image.Image, alpha_min: int = 20) -> Image.Image:
    """Corta a folga transparente em volta do personagem."""
    bbox = img.getbbox()
    if not bbox:
        return img
    return img.crop(bbox)


def _fit_feet(img: Image.Image, height: int = TARGET_H) -> Image.Image:
    """Redimensiona pela altura para os pés alinharem no GROUND_Y."""
    img = _autocrop(img)
    w, h = img.size
    if h == 0:
        return img
    scale = height / h
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    return img.resize((nw, nh), Image.Resampling.LANCZOS)


def _clean_existing_sprite(path: Path) -> None:
    img = Image.open(path).convert("RGBA")
    w, h = img.size
    before = img.tobytes()
    px = img.load()
    _punch_interior_white(px, w, h)
    if img.tobytes() != before:
        img.save(path, "PNG")


def prepare_player_sprites(force: bool = False) -> dict[str, Path]:
    """Gera PNGs em assets/player/ a partir das fontes, sem sobrescrever se já existirem."""
    PLAYER_DIR.mkdir(parents=True, exist_ok=True)
    out: dict[str, Path] = {}
    for name, source in POSE_SOURCES.items():
        dest = PLAYER_DIR / f"{name}.png"
        out[name] = dest
        if dest.exists() and not force:
            _clean_existing_sprite(dest)
            continue
        if not source.exists():
            if dest.exists():
                _clean_existing_sprite(dest)
            continue
        cut = _flood_knockout(Image.open(source))
        cut = _fit_feet(cut, 140 if name == "crouch" else TARGET_H)
        cut.save(dest, "PNG")
    return out


def load_player_frames() -> dict[str, pygame.Surface]:
    """Garante os PNGs e devolve as Surfaces prontas para o YaguarPlayer."""
    prepare_player_sprites()
    frames: dict[str, pygame.Surface] = {}
    for name in POSE_SOURCES:
        path = PLAYER_DIR / f"{name}.png"
        if path.exists():
            frames[name] = pygame.image.load(str(path)).convert_alpha()
    if "idle" not in frames:
        raise FileNotFoundError("Sprite idle do Yáguar não encontrado.")
    return frames

"""Recorta o fundo branco e carrega as poses do Yáguar."""

from __future__ import annotations

from collections import deque
from pathlib import Path

import pygame
import numpy as np
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

# Pose de tiro: imagem enviada (fundo preto). Cópia local em assets/player_src/.
BOW_SRC_DIR = ASSETS_DIR / "player_src"
BOW_DRAW_DEST = PLAYER_DIR / "bow.png"
ARROW_DEST = PLAYER_DIR / "arrow.png"
# Altura da haste na pose de tiro (~3–7 px no sprite de 168). A de voo casa com essa.
ARROW_TARGET_H = 6
ARROW_SOURCE_CANDIDATES = (
    BOW_SRC_DIR / "arrow_src.png",
    Path(r"C:\Users\weydi\.cursor\projects\c-Users-weydi-Desktop-Yaguar-O-Guardiao-da-Floresta\assets\yaguar_arrow_src.png"),
)
BOW_SOURCE_CANDIDATES = (
    PLAYER_DIR / "trigger01.png",
    BOW_SRC_DIR / "bow_draw.png",
    BOW_SRC_DIR / "bow_draw.jpg",
    Path(r"C:\Users\weydi\.cursor\projects\c-Users-weydi-Desktop-Yaguar-O-Guardiao-da-Floresta\assets\c__Users_weydi_AppData_Roaming_Cursor_User_workspaceStorage_5f880407ed4f95d861c48a2c1df55467_images_trigger01-6c3d992d-7efc-4bce-89a9-cebbbaf94309.jpg"),
)
BOW_PREP_POSES = ("bow_quiver", "bow_nock")
BOW_PREP_CANDIDATES = {
    "bow_quiver": (
        BOW_SRC_DIR / "bow_quiver_src.png",
        Path(r"C:\Users\weydi\.cursor\projects\c-Users-weydi-Desktop-Yaguar-O-Guardiao-da-Floresta\assets\bow_quiver_src.png"),
    ),
    "bow_nock": (
        BOW_SRC_DIR / "bow_nock_src.png",
        Path(r"C:\Users\weydi\.cursor\projects\c-Users-weydi-Desktop-Yaguar-O-Guardiao-da-Floresta\assets\bow_nock_src.png"),
    ),
}

TARGET_H = 168
BOW_BODY_H = 168
BODY_ROW_MIN = 18  # ignora ponta de lanca/arco ao medir o corpo
POSE_ANCHORS: dict[str, tuple[float, float]] = {}
SCALED_ARROW: pygame.Surface | None = None
RAW_BOW_SURFACES: dict[str, pygame.Surface] = {}
BLACK = (0, 0, 0)
BLACK_TOL = 6
BLACK_SOFT = 0
BLACK_INTERIOR = 5
VINE_POSES = ("grab", "swing_left", "swing_center", "swing_right", "release")
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


def _is_warm_pixel(r: int, g: int, b: int) -> bool:
    """Pele, madeira, tatuagem, penas — qualquer tom do corpo, inclusive sombra."""
    return r >= 12 and r + g >= 18 and (r >= b or r >= 20)


def _is_black_bg(r: int, g: int, b: int, a: int, tol: int) -> bool:
    """Só o preto do estúdio. Sombras do corpo não entram."""
    if a < 12:
        return True
    if _is_warm_pixel(r, g, b):
        return False
    luma = 0.3 * r + 0.59 * g + 0.11 * b
    chroma = max(r, g, b) - min(r, g, b)
    return luma <= tol and chroma <= 5


def _luma(r: int, g: int, b: int) -> float:
    return 0.3 * r + 0.59 * g + 0.11 * b


def _sat(r: int, g: int, b: int) -> int:
    return max(r, g, b) - min(r, g, b)


def _unblend_from_white(r: int, g: int, b: int, a: int) -> tuple[int, int, int, int]:
    """Tira a mistura do fundo branco. Papel de estúdio vira transparente."""
    if a <= 10:
        return (r, g, b, 0)
    fa = a / 255.0
    inv = 1.0 - fa
    nr = (r - inv * 255.0) / fa
    ng = (g - inv * 255.0) / fa
    nb = (b - inv * 255.0) / fa
    if nr < 4 and ng < 4 and nb < 4 and _luma(r, g, b) > 90:
        return (r, g, b, 0)
    if nr < -4 or ng < -4 or nb < -4:
        return (r, g, b, 0)
    return (
        int(max(0, min(255, round(nr)))),
        int(max(0, min(255, round(ng)))),
        int(max(0, min(255, round(nb)))),
        a,
    )


def _is_paper_fringe(r: int, g: int, b: int, a: int) -> bool:
    """Halo/pontos do matte branco — não a pena creme nem o brilho da lança."""
    if a < 12:
        return True
    luma = _luma(r, g, b)
    sat = _sat(r, g, b)
    if _is_warm_pixel(r, g, b) and sat >= 28 and luma < 235:
        return False
    if luma >= 200 and sat <= 42:
        return True
    if luma >= 175 and sat <= 22:
        return True
    if a < 110 and luma >= 140 and sat <= 48:
        return True
    return False


def _touches_transparent(px, x: int, y: int, w: int, h: int, alpha_min: int = 18) -> bool:
    for dx, dy in NEIGHBORS8:
        nx, ny = x + dx, y + dy
        if nx < 0 or ny < 0 or nx >= w or ny >= h:
            return True
        if px[nx, ny][3] < alpha_min:
            return True
    return False


def _apply_fade(px, x: int, y: int, r: int, g: int, b: int, a: int) -> None:
    d = _dist((r, g, b), WHITE)
    if d <= TOL or a < 12:
        px[x, y] = (r, g, b, 0)
    elif d <= TOL + SOFT:
        if _is_warm_pixel(r, g, b):
            px[x, y] = _unblend_from_white(r, g, b, a)
        else:
            px[x, y] = (r, g, b, 0)


def _defringe_white(img: Image.Image) -> Image.Image:
    """Remove o anel de pixels brancos no contorno e devolve a cor do corpo."""
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a <= 0:
                continue
            if a < 252:
                r, g, b, a = _unblend_from_white(r, g, b, a)
                px[x, y] = (r, g, b, a)
            if a > 0 and _is_paper_fringe(r, g, b, a) and (a < 160 or _touches_transparent(px, x, y, w, h)):
                px[x, y] = (0, 0, 0, 0)

    src = img.copy()
    sp = src.load()
    px = img.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = sp[x, y]
            if a <= 0 or not _touches_transparent(sp, x, y, w, h):
                continue
            neigh: list[tuple[int, int, int]] = []
            for dx, dy in NEIGHBORS8:
                nx, ny = x + dx, y + dy
                if nx < 0 or ny < 0 or nx >= w or ny >= h:
                    continue
                rr, gg, bb, aa = sp[nx, ny]
                if aa >= 200 and not _is_paper_fringe(rr, gg, bb, aa):
                    neigh.append((rr, gg, bb))
            if not neigh:
                if _is_paper_fringe(r, g, b, a) or a < 90 or _luma(r, g, b) > 160:
                    px[x, y] = (0, 0, 0, 0)
                continue
            n_luma = sum(_luma(*n) for n in neigh) / len(neigh)
            if _luma(r, g, b) > n_luma + 14 and _sat(r, g, b) < 55:
                px[x, y] = (0, 0, 0, 0)
            elif _luma(r, g, b) > n_luma + 6:
                ar = int(sum(n[0] for n in neigh) / len(neigh))
                ag = int(sum(n[1] for n in neigh) / len(neigh))
                ab = int(sum(n[2] for n in neigh) / len(neigh))
                px[x, y] = (ar, ag, ab, 255 if _is_warm_pixel(ar, ag, ab) else a)

    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if 0 < a < 250 and _is_warm_pixel(r, g, b):
                px[x, y] = (r, g, b, 255)
    return img


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
    return _defringe_white(img)


def _warm_neighbor_count(px, x: int, y: int, w: int, h: int) -> int:
    n = 0
    for dx, dy in NEIGHBORS8:
        nx, ny = x + dx, y + dy
        if nx < 0 or ny < 0 or nx >= w or ny >= h:
            continue
        r, g, b, a = px[nx, ny]
        if a >= 80 and _is_warm_pixel(r, g, b):
            n += 1
    return n


def _apply_black_fade(px, x: int, y: int, r: int, g: int, b: int, a: int, w: int, h: int) -> None:
    """Apaga só o fundo. Nunca reduz o alfa de um pixel do corpo."""
    if _is_warm_pixel(r, g, b):
        return
    if _warm_neighbor_count(px, x, y, w, h) >= 3:
        return
    luma = 0.3 * r + 0.59 * g + 0.11 * b
    chroma = max(r, g, b) - min(r, g, b)
    if luma <= BLACK_TOL and chroma <= 5:
        px[x, y] = (r, g, b, 0)


def _restore_body_opacity(img: Image.Image) -> Image.Image:
    """Garante que sombras e tatuagens fiquem opacas após o knockout."""
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a <= 0 or a >= 250:
                continue
            if _is_paper_fringe(r, g, b, a):
                continue
            if _is_warm_pixel(r, g, b) or (_luma(r, g, b) > BLACK_TOL + 2 and _sat(r, g, b) >= 8):
                px[x, y] = (r, g, b, 255)
    return img


def _flood_knockout_black(img: Image.Image) -> Image.Image:
    """Remove o fundo preto a partir das bordas e os ocos internos (corda do arco)."""
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
        if not _is_black_bg(r, g, b, a, BLACK_TOL):
            continue
        _apply_black_fade(px, x, y, r, g, b, a, w, h)
        for dx, dy in NEIGHBORS4:
            q.append((x + dx, y + dy))

    _punch_interior_black(px, w, h)
    return _restore_body_opacity(img)


def _punch_interior_black(px, w: int, h: int) -> None:
    """Remove ilhas pretas presas entre a corda, o arco e o corpo."""
    seen = bytearray(w * h)
    for y in range(h):
        for x in range(w):
            i = y * w + x
            if seen[i]:
                continue
            r, g, b, a = px[x, y]
            if a < 12 or not _is_black_bg(r, g, b, a, BLACK_INTERIOR):
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
                    if na < 12 or not _is_black_bg(nr, ng, nb, na, BLACK_INTERIOR + 4):
                        continue
                    seen[ni] = 1
                    q.append((nx, ny))
            if len(blob) < HOLE_MIN_AREA:
                continue
            for bx, by, br, bg, bb, ba in blob:
                _apply_black_fade(px, bx, by, br, bg, bb, ba, w, h)


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


def _silhouette_body_height(img: Image.Image) -> int:
    """Altura do corpo (cocar → pés), ignorando pontas finas de arma."""
    w, h = img.size
    px = img.load()
    top = None
    bot = 0
    for y in range(h):
        n = 0
        for x in range(w):
            if px[x, y][3] > 80:
                n += 1
        if n >= BODY_ROW_MIN and top is None:
            top = y
        if n >= 3:
            bot = y
    if top is None:
        return max(8, h)
    return max(8, bot - top + 1)


def _resize_keep_color(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Reduz RGBA sem misturar o preto transparente na pele (premultiply)."""
    if img.size == size:
        return img
    tw, th = size
    w, h = img.size
    while w > tw * 2 and h > th * 2:
        w, h = max(tw, (w + 1) // 2), max(th, (h + 1) // 2)
        img = _resize_keep_color_once(img, (w, h))
    return _resize_keep_color_once(img, size)


def _resize_keep_color_once(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    arr = np.asarray(img.convert("RGBA"))
    rgb = arr[..., :3].astype(np.float32)
    alpha = arr[..., 3].astype(np.float32)
    a = np.clip(alpha / 255.0, 0.0, 1.0)
    premul = np.clip(rgb * a[..., None], 0.0, 255.0).astype(np.uint8)
    rgb_img = Image.fromarray(premul, "RGB").resize(size, Image.Resampling.LANCZOS)
    a_img = Image.fromarray(arr[..., 3], "L").resize(size, Image.Resampling.LANCZOS)
    p = np.asarray(rgb_img).astype(np.float32)
    aa = np.asarray(a_img).astype(np.float32)
    a01 = np.maximum(aa / 255.0, 1e-6)
    out_rgb = np.clip(np.divide(p, a01[..., None]), 0.0, 255.0)
    out_rgb = np.where(aa[..., None] >= 10.0, out_rgb, p)
    out = np.empty((size[1], size[0], 4), dtype=np.uint8)
    out[..., :3] = np.round(out_rgb).astype(np.uint8)
    out[..., 3] = np.asarray(a_img)
    return Image.fromarray(out, "RGBA")


def _crisp_resize(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Reduz a arte de trigger01 sem sujar a cor com o fundo preto."""
    return _resize_keep_color(img, size)


def _scale_body_to(img: Image.Image, target_body: int, crisp: bool = False) -> Image.Image:
    """Redimensiona para o corpo ter a mesma altura da pose idle."""
    body = _silhouette_body_height(img)
    scale = target_body / body
    if abs(scale - 1.0) < 0.02:
        return img
    w, h = img.size
    nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    if crisp:
        return _resize_keep_color(img, (nw, nh))
    return img.resize((nw, nh), Image.Resampling.LANCZOS)


def _pil_to_surface(img: Image.Image) -> pygame.Surface:
    img = img.convert("RGBA")
    surf = pygame.image.frombytes(img.tobytes(), img.size, "RGBA")
    if pygame.display.get_init():
        return surf.convert_alpha()
    return surf


def _rightmost_midbottom_offset(img: Image.Image) -> tuple[float, float]:
    """Offset da ponta da flecha (pixel opaco mais à direita) relativo aos pés."""
    w, h = img.size
    px = img.load()
    rx, ry = 0, 0
    for y in range(h):
        for x in range(w):
            if px[x, y][3] > 90 and x >= rx:
                rx, ry = x, y
    return rx - w / 2.0, ry - float(h)


def _fit_feet(img: Image.Image, height: int = TARGET_H) -> Image.Image:
    """Redimensiona pela altura para os pés alinharem no GROUND_Y."""
    img = _autocrop(img)
    w, h = img.size
    if h == 0:
        return img
    scale = height / h
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    return img.resize((nw, nh), Image.Resampling.LANCZOS)


def _kill_paper_specks(img: Image.Image) -> Image.Image:
    """Apaga só pontinhos de papel no contorno. Não descontamina (fundo era preto)."""
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 12:
                continue
            if _is_paper_fringe(r, g, b, a) and _touches_transparent(px, x, y, w, h):
                px[x, y] = (0, 0, 0, 0)
    return img


def _kill_unsharp_edge_flash(img: Image.Image) -> Image.Image:
    """Apaga flash cinza-claro que o unsharp pode criar no contorno."""
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 40:
                continue
            if not _touches_transparent(px, x, y, w, h):
                continue
            luma = 0.3 * r + 0.59 * g + 0.11 * b
            sat = max(r, g, b) - min(r, g, b)
            if luma >= 200 and sat <= 22:
                px[x, y] = (0, 0, 0, 0)
    return img


_DEFRINGE_POSES = ("attack.png",)


def _clean_existing_sprite(path: Path) -> None:
    img = Image.open(path).convert("RGBA")
    before = img.tobytes()
    if path.name in _DEFRINGE_POSES:
        img = _defringe_white(img)
    else:
        w, h = img.size
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
    prepare_bow_sprites(force=force)
    return out


def _resolve_bow_source() -> Path | None:
    """Prefere trigger01.png (nítido) ao JPEG comprimido."""
    BOW_SRC_DIR.mkdir(parents=True, exist_ok=True)
    trigger = PLAYER_DIR / "trigger01.png"
    local_png = BOW_SRC_DIR / "bow_draw.png"
    if trigger.is_file():
        if not local_png.is_file() or local_png.stat().st_size != trigger.stat().st_size:
            local_png.write_bytes(trigger.read_bytes())
        return local_png
    if local_png.is_file():
        return local_png
    local_jpg = BOW_SRC_DIR / "bow_draw.jpg"
    if local_jpg.is_file():
        return local_jpg
    for cand in BOW_SOURCE_CANDIDATES:
        if cand.is_file():
            dest = local_png if cand.suffix.lower() == ".png" else local_jpg
            dest.write_bytes(cand.read_bytes())
            return dest
    return None


def _extract_arrow(sprite: Image.Image) -> Image.Image | None:
    """Recorta a flecha horizontal da pose de tiro (a mesma que ele segura)."""
    w, h = sprite.size
    px = sprite.load()
    rx, ry, best = 0, 0, -1
    for y in range(h):
        for x in range(w):
            if px[x, y][3] > 90 and x >= best:
                best = x
                rx, ry = x, y
    if best < 20:
        return None
    top, bot = max(0, ry - 7), min(h, ry + 8)
    left = rx
    for x in range(rx, int(w * 0.20), -1):
        filled = sum(1 for y in range(top, bot) if px[x, y][3] > 60)
        if filled > 11 and x < int(w * 0.55):
            break
        if filled > 0:
            left = x
    if rx - left < 28:
        return None
    return sprite.crop((left, top, min(w, rx + 2), bot))


def _fit_black_character(source: Path) -> Image.Image | None:
    """Recorta o fundo preto e reduz sem sujar a cor do corpo."""
    cut = _flood_knockout_black(Image.open(source))
    cut = _autocrop(cut)
    cw, ch = cut.size
    if ch < 8:
        return None
    scale = BOW_BODY_H / ch
    fitted = _crisp_resize(cut, (max(1, int(cw * scale)), max(1, int(ch * scale))))
    fitted = _restore_body_opacity(fitted)
    fitted = _kill_paper_specks(fitted)
    return _kill_unsharp_edge_flash(fitted)


def _resolve_arrow_source() -> Path | None:
    BOW_SRC_DIR.mkdir(parents=True, exist_ok=True)
    local = BOW_SRC_DIR / "arrow_src.png"
    if local.is_file():
        return local
    for cand in ARROW_SOURCE_CANDIDATES:
        if cand.is_file():
            local.write_bytes(cand.read_bytes())
            return local
    return None


def _fit_arrow(source: Path) -> Image.Image | None:
    """Recorta o fundo preto da flecha isolada e reduz para o tamanho de voo."""
    cut = _flood_knockout_black(Image.open(source))
    cut = _autocrop(cut)
    w, h = cut.size
    if w < 16 or h < 4:
        return None
    nh = ARROW_TARGET_H
    nw = max(40, int(round(w * nh / h)))
    fitted = _resize_keep_color(cut, (nw, nh))
    fitted = _kill_paper_specks(fitted)
    return _kill_unsharp_edge_flash(fitted)


def prepare_arrow_sprite(force: bool = False) -> None:
    """Gera arrow.png a partir da flecha isolada (não do recorte da pose)."""
    source = _resolve_arrow_source()
    if source is None:
        return
    if ARROW_DEST.exists() and not force:
        return
    fitted = _fit_arrow(source)
    if fitted is not None:
        fitted.save(ARROW_DEST, "PNG")
        from src.color_profile import apply_yaguar_grade

        apply_yaguar_grade(fitted).save(PLAYER_DIR / "arrow_color_corrected.png", "PNG")


def prepare_bow_sprites(force: bool = False) -> None:
    """Gera bow.png (personagem sem fundo) e a flecha de projétil."""
    PLAYER_DIR.mkdir(parents=True, exist_ok=True)
    if not BOW_DRAW_DEST.exists() or force:
        source = _resolve_bow_source()
        if source is not None:
            fitted = _fit_black_character(source)
            if fitted is not None:
                fitted.save(BOW_DRAW_DEST, "PNG")
                if not ARROW_DEST.exists() and _resolve_arrow_source() is None:
                    arrow = _extract_arrow(fitted)
                    if arrow is not None:
                        arrow.save(ARROW_DEST, "PNG")
    prepare_arrow_sprite(force=force)
    prepare_bow_prep_sprites(force=force)
    from src.color_profile import prepare_bow_color_grades

    prepare_bow_color_grades(force=force)


def _resolve_prep_source(name: str) -> Path | None:
    BOW_SRC_DIR.mkdir(parents=True, exist_ok=True)
    local = BOW_SRC_DIR / f"{name}_src.png"
    if local.is_file():
        return local
    for cand in BOW_PREP_CANDIDATES.get(name, ()):
        if cand.is_file():
            local.write_bytes(cand.read_bytes())
            return local
    return None


def prepare_bow_prep_sprites(force: bool = False) -> None:
    """Gera as poses de sacar da aljava e encaixar a flecha."""
    PLAYER_DIR.mkdir(parents=True, exist_ok=True)
    for name in BOW_PREP_POSES:
        dest = PLAYER_DIR / f"{name}.png"
        if dest.exists() and not force:
            continue
        source = _resolve_prep_source(name)
        if source is None:
            continue
        fitted = _fit_black_character(source)
        if fitted is not None:
            fitted.save(dest, "PNG")


def load_player_frames() -> dict[str, pygame.Surface]:
    """Garante os PNGs, iguala a escala do corpo à do idle e devolve as Surfaces."""
    global SCALED_ARROW
    prepare_player_sprites()
    idle_path = PLAYER_DIR / "idle.png"
    if not idle_path.is_file():
        raise FileNotFoundError("Sprite idle do Yáguar não encontrado.")
    idle_img = Image.open(idle_path).convert("RGBA")
    ref_body = _silhouette_body_height(idle_img)

    frames: dict[str, pygame.Surface] = {}
    names = list(POSE_SOURCES) + list(VINE_POSES) + ["bow", "bow_quiver", "bow_nock"]
    bow_scale = 1.0
    RAW_BOW_SURFACES.clear()
    from src.color_profile import corrected_path
    from src.config import BOW_GRADE_POSES

    for name in names:
        raw_path = PLAYER_DIR / f"{name}.png"
        path = raw_path
        if name in BOW_GRADE_POSES:
            alt = corrected_path(name)
            if alt.is_file():
                path = alt
        if not path.is_file() and not raw_path.is_file():
            continue
        if not path.is_file():
            path = raw_path
        img = Image.open(path).convert("RGBA")
        if name != "crouch":
            before = _silhouette_body_height(img)
            img = _scale_body_to(img, ref_body, crisp=name in BOW_GRADE_POSES)
            if name == "bow" and before:
                bow_scale = ref_body / before
        if name in ("bow", "bow_quiver", "bow_nock"):
            POSE_ANCHORS[name] = _rightmost_midbottom_offset(img)
        frames[name] = _pil_to_surface(img)
        if name in BOW_GRADE_POSES and raw_path.is_file() and path != raw_path:
            raw_img = Image.open(raw_path).convert("RGBA")
            if name != "crouch":
                raw_img = _scale_body_to(raw_img, ref_body, crisp=True)
            RAW_BOW_SURFACES[name] = _pil_to_surface(raw_img)

    arrow_path = ARROW_DEST
    graded_arrow = PLAYER_DIR / "arrow_color_corrected.png"
    if graded_arrow.is_file():
        arrow_path = graded_arrow
    if arrow_path.is_file():
        arrow = Image.open(arrow_path).convert("RGBA")
        if abs(bow_scale - 1.0) > 0.02:
            aw, ah = arrow.size
            arrow = _crisp_resize(
                arrow,
                (max(1, int(round(aw * bow_scale))), max(1, int(round(ah * bow_scale)))),
            )
        SCALED_ARROW = _pil_to_surface(arrow)
    if "idle" not in frames:
        raise FileNotFoundError("Sprite idle do Yáguar não encontrado.")
    return frames

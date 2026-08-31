"""Cipós balançáveis: pêndulo, zona de agarrar e lianas da caverna.

A física não muda. O desenho usa tiles de musgo da pintura; se faltarem,
cai num fita orgânica — nunca nas linhas verdes do debug.
"""
from __future__ import annotations

import math
from pathlib import Path

import pygame

from src.config import GRAVITY, SCREEN_WIDTH

VINE_DAMPING = 0.993
VINE_DEFS: tuple = ()
VINE_GRAB_RADIUS = 54
VINE_MAX_ANGLE = 1.12
VINE_QUICKSAND: tuple = ()
VINE_SPIKES: tuple = ()
VINE_STALACTITES: tuple = ()

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
VINE_ART_DIR = ASSETS_DIR / "gameplay" / "vines"

VINE_OMEGA_MAX = 0.095
VINE_ROPE_GRAB_FRAC = 0.58
VINE_BARK = (62, 78, 40)
VINE_BARK_DARK = (36, 48, 28)
VINE_BARK_LIT = (92, 108, 52)
VINE_MOSS = (74, 92, 44)
VINE_LEAF = (88, 110, 48)
VINE_HIGHLIGHT = (168, 214, 92)

_STAMPS: dict[str, pygame.Surface] | None = None
_VINE_ART: dict[str, pygame.Surface] | None = None
_ROT_CACHE: dict[tuple[int, int], pygame.Surface] = {}


def _safe_load(path: Path) -> pygame.Surface | None:
    if not path.is_file() or not pygame.get_init():
        return None
    try:
        return pygame.image.load(str(path)).convert_alpha()
    except pygame.error:
        return None


def _stamps() -> dict[str, pygame.Surface]:
    global _STAMPS
    if _STAMPS is not None:
        return _STAMPS
    leaf = pygame.Surface((11, 7), pygame.SRCALPHA)
    pygame.draw.ellipse(leaf, (*VINE_LEAF, 230), (0, 1, 10, 5))
    pygame.draw.ellipse(leaf, (48, 78, 32, 200), (1, 2, 7, 3))
    _STAMPS = {"leaf": leaf}
    return _STAMPS


def _vine_art() -> dict[str, pygame.Surface]:
    global _VINE_ART
    if _VINE_ART is not None:
        return _VINE_ART
    art: dict[str, pygame.Surface] = {}
    mapping = {
        "seg1": VINE_ART_DIR / "segments" / "vine_segment_01.png",
        "seg2": VINE_ART_DIR / "segments" / "vine_segment_02.png",
        "leaf": VINE_ART_DIR / "segments" / "vine_moss_tuft_01.png",
        "leaf_alt": VINE_ART_DIR / "segments" / "vine_segment_leaf.png",
        "anchor_ceiling": VINE_ART_DIR / "anchors" / "vine_anchor_ceiling_01.png",
        "anchor_branch": VINE_ART_DIR / "anchors" / "vine_anchor_branch_01.png",
        "anchor_root": VINE_ART_DIR / "anchors" / "vine_anchor_root_01.png",
        "anchor_rock": VINE_ART_DIR / "anchors" / "vine_anchor_rock_01.png",
    }
    for key, path in mapping.items():
        surf = _safe_load(path)
        if surf is not None:
            art[key] = surf
    if "leaf" not in art and "leaf_alt" in art:
        art["leaf"] = art["leaf_alt"]
    _VINE_ART = art
    return _VINE_ART


def _rotated(surf: pygame.Surface, angle_deg: float) -> pygame.Surface:
    key = (id(surf), int(round(angle_deg / 5.0) * 5))
    cached = _ROT_CACHE.get(key)
    if cached is not None:
        return cached
    rotated = pygame.transform.rotate(surf, -key[1])
    if len(_ROT_CACHE) > 256:
        _ROT_CACHE.clear()
    _ROT_CACHE[key] = rotated
    return rotated


def _ribbon_polygon(pts: list[tuple[int, int]], width_start: float, width_end: float) -> list[tuple[int, int]]:
    if len(pts) < 2:
        return []
    left: list[tuple[int, int]] = []
    right: list[tuple[int, int]] = []
    last = len(pts) - 1
    for i, (x, y) in enumerate(pts):
        t = i / last
        width = width_start * (1.0 - t) + width_end * t
        if i == 0:
            dx, dy = pts[1][0] - x, pts[1][1] - y
        elif i == last:
            dx, dy = x - pts[i - 1][0], y - pts[i - 1][1]
        else:
            dx, dy = pts[i + 1][0] - pts[i - 1][0], pts[i + 1][1] - pts[i - 1][1]
        dist = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / dist, dx / dist
        hw = width * 0.5
        left.append((int(x + nx * hw), int(y + ny * hw)))
        right.append((int(x - nx * hw), int(y - ny * hw)))
    return left + list(reversed(right))


def _hash01(*values: float) -> float:
    n = 0.0
    for v in values:
        n = math.fmod(n * 37.17 + v * 0.013, 1.0)
    return abs(n)


class Vine:
    """Corda de comprimento fixo com âncora no teto da caverna."""

    def __init__(self, ax: float, ay: float, length: float, grab_radius: int = VINE_GRAB_RADIUS):
        self.ax = float(ax)
        self.ay = float(ay)
        self.length = float(length)
        self.grab_radius = int(grab_radius)
        self.highlight = False
        self._seed = _hash01(ax, ay, length)

    @property
    def rest(self) -> tuple[float, float]:
        return (self.ax, self.ay + self.length)

    def hang_point(self, angle: float) -> tuple[float, float]:
        """Ponto do peito no pêndulo. y cresce para baixo (Pygame)."""
        return (
            self.ax + self.length * math.sin(angle),
            self.ay + self.length * math.cos(angle),
        )

    def angle_from_point(self, x: float, y: float) -> float:
        return math.atan2(x - self.ax, y - self.ay)

    def closest_on_rope(self, x: float, y: float) -> tuple[float, float, float]:
        """Ponto mais próximo no segmento âncora→repouso. Devolve (px, py, t)."""
        dx = 0.0
        dy = self.length
        span = dx * dx + dy * dy or 1.0
        t = max(0.0, min(1.0, ((x - self.ax) * dx + (y - self.ay) * dy) / span))
        return (self.ax + dx * t, self.ay + dy * t, t)

    def in_reach(self, x: float, y: float) -> bool:
        """Zona de agarrar: círculo no repouso + cápsula na metade inferior."""
        rx, ry = self.rest
        if math.hypot(x - rx, y - ry) <= self.grab_radius:
            return True
        px, py, t = self.closest_on_rope(x, y)
        if t < VINE_ROPE_GRAB_FRAC:
            return False
        return math.hypot(x - px, y - py) <= self.grab_radius

    def _polyline(self, hang: tuple[float, float], taut: bool) -> list[tuple[float, float]]:
        hx, hy = hang
        dx, dy = hx - self.ax, hy - self.ay
        dist = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / dist, dx / dist
        n = max(8, min(14, int(self.length / 22)))
        amp = 2.4 if taut else 5.5
        pts = []
        for i in range(n + 1):
            t = i / n
            wobble = math.sin(t * 6.2 + self._seed * 12.0) * amp * (1.0 - t * 0.35)
            wobble += math.sin(t * 13.0 + self._seed * 7.0) * amp * 0.28
            pts.append((self.ax + dx * t + nx * wobble, self.ay + dy * t + ny * wobble))
        return pts

    def _draw_anchor(self, screen: pygame.Surface, ax: int, ay: int) -> None:
        art = _vine_art()
        stamp = art.get("anchor_ceiling") or art.get("anchor_root") or art.get("anchor_branch")
        if stamp is not None:
            rect = stamp.get_rect(midbottom=(ax, ay + 10))
            screen.blit(stamp, rect)
            return
        pygame.draw.ellipse(screen, VINE_BARK_DARK, (ax - 28, ay - 18, 56, 28))
        pygame.draw.ellipse(screen, VINE_MOSS, (ax - 16, ay - 14, 32, 18))

    def _draw_tiled_rope(self, screen: pygame.Surface, pts: list[tuple[int, int]], taut: bool) -> bool:
        art = _vine_art()
        seg = art.get("seg2" if self._seed >= 0.5 else "seg1") or art.get("seg1") or art.get("seg2")
        if seg is None or len(pts) < 2:
            return False
        leaf = art.get("leaf")
        step = max(14, int(seg.get_height() * (0.52 if taut else 0.58)))
        dist_acc = 0.0
        next_stamp = 0.0
        i_leaf = 0
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            dx, dy = x1 - x0, y1 - y0
            span = math.hypot(dx, dy) or 1.0
            angle = math.degrees(math.atan2(dx, dy))
            rotated = _rotated(seg, angle)
            start = dist_acc
            end = dist_acc + span
            while next_stamp <= end:
                t = (next_stamp - start) / span
                px = int(x0 + dx * t)
                py = int(y0 + dy * t)
                screen.blit(rotated, rotated.get_rect(center=(px, py)))
                if leaf is not None and i_leaf % 2 == 0:
                    lf = pygame.transform.rotate(leaf, (self._seed * 80 + i_leaf * 25) % 360)
                    screen.blit(lf, lf.get_rect(center=(px + 5, py)))
                i_leaf += 1
                next_stamp += step
            dist_acc = end
        return True

    def draw_visual(
        self,
        screen: pygame.Surface,
        cam_x: float,
        ox: int = 0,
        oy: int = 0,
        hang=None,
        taut: bool = False,
    ) -> None:
        if hang is None:
            hang = self.rest
        ax = int(self.ax - cam_x + ox)
        ay = int(self.ay + oy)
        hx = int(hang[0] - cam_x + ox)
        hy = int(hang[1] + oy)
        if max(ax, hx) < -90 or min(ax, hx) > SCREEN_WIDTH + 90:
            return
        pts = [(int(x - cam_x + ox), int(y + oy)) for x, y in self._polyline(hang, taut)]
        tiled = self._draw_tiled_rope(screen, pts, taut)
        if not tiled and len(pts) >= 2:
            body = _ribbon_polygon(pts, 13 if taut else 12, 7)
            edge = _ribbon_polygon(pts, 16 if taut else 15, 9)
            if len(edge) >= 3:
                pygame.draw.polygon(screen, VINE_BARK_DARK, edge)
            if len(body) >= 3:
                pygame.draw.polygon(screen, VINE_BARK_LIT if self.highlight else VINE_BARK, body)
            stamps = _stamps()
            for i, (px, py) in enumerate(pts[1:-1]):
                if i % 3:
                    continue
                leaf = pygame.transform.rotate(stamps["leaf"], (self._seed * 80 + i * 25) % 360)
                screen.blit(leaf, leaf.get_rect(center=(px + 3, py)))
        self._draw_anchor(screen, ax, ay)

    def draw(self, screen: pygame.Surface, cam_x: float, ox: int = 0, oy: int = 0, hang=None) -> None:
        """Compatível com o loop antigo: desenho orgânico, sem linha de debug."""
        taut = hang is not None
        self.draw_visual(screen, cam_x, ox, oy, hang=hang, taut=taut)

    def draw_debug(
        self,
        screen: pygame.Surface,
        cam_x: float,
        ox: int = 0,
        oy: int = 0,
        hang=None,
    ) -> None:
        ax = int(self.ax - cam_x + ox)
        ay = int(self.ay + oy)
        if hang is None:
            hx, hy = self.rest
        else:
            hx, hy = hang
        hx = int(hx - cam_x + ox)
        hy = int(hy + oy)
        pygame.draw.line(screen, VINE_HIGHLIGHT, (ax, ay), (hx, hy), 1)
        pygame.draw.circle(screen, VINE_HIGHLIGHT, (ax, ay), 4, 1)
        pygame.draw.circle(screen, VINE_HIGHLIGHT, (ax, ay), self.grab_radius, 1)
        rx, ry = self.rest
        pygame.draw.circle(screen, VINE_HIGHLIGHT, (int(rx - cam_x + ox), int(ry + oy)), self.grab_radius, 1)


def make_vines() -> list[Vine]:
    return [Vine(ax, ay, length) for ax, ay, length in VINE_DEFS]


def step_pendulum(angle: float, omega: float, length: float, pump: float = 0.0, dt: float = 1.0) -> tuple[float, float]:
    """Integra α = -(g/L) sin(θ) + pump. dt=1 corresponde a um frame a 60 FPS."""
    length = max(8.0, float(length))
    alpha = -(GRAVITY / length) * math.sin(angle) + pump
    omega = (omega + alpha * dt) * VINE_DAMPING
    omega = max(-VINE_OMEGA_MAX, min(VINE_OMEGA_MAX, omega))
    angle = angle + omega * dt
    if angle > VINE_MAX_ANGLE:
        angle = VINE_MAX_ANGLE
        omega *= -0.28
    elif angle < -VINE_MAX_ANGLE:
        angle = -VINE_MAX_ANGLE
        omega *= -0.28
    return angle, omega


def release_velocity(angle: float, omega: float, length: float) -> tuple[float, float]:
    """Velocidade tangencial → (vx, vy) em px/frame, sem zerar o momentum."""
    vx = omega * length * math.cos(angle)
    vy = -omega * length * math.sin(angle)
    return vx, vy


def grab_omega(angle: float, vx: float, vy: float, length: float) -> float:
    """Projeta a velocidade aérea na tangente do pêndulo."""
    length = max(8.0, float(length))
    omega = (vx * math.cos(angle) - vy * math.sin(angle)) / length
    return max(-VINE_OMEGA_MAX, min(VINE_OMEGA_MAX, omega))


def nearest_grabbable(vines: list[Vine], x: float, y: float) -> Vine | None:
    best = None
    best_d = 1e9
    for vine in vines:
        if not vine.in_reach(x, y):
            continue
        rx, ry = vine.rest
        dist = math.hypot(x - rx, y - ry)
        if dist < best_d:
            best = vine
            best_d = dist
    return best


def spike_rects() -> list[pygame.Rect]:
    return [pygame.Rect(*box) for box in VINE_SPIKES]


def stalactite_rects() -> list[pygame.Rect]:
    return [pygame.Rect(*box) for box in VINE_STALACTITES]


def quicksand_rects() -> list[pygame.Rect]:
    return [pygame.Rect(*box) for box in VINE_QUICKSAND]


def hand_anchor_from_player(player) -> tuple[float, float]:
    """Ponto visual das mãos. Não altera hurtbox nem o pêndulo."""
    if hasattr(player, "hand_anchor"):
        return player.hand_anchor()
    body = player.hurtbox
    facing = getattr(player, "facing", 1)
    return (float(body.centerx + facing * 16), float(body.centery - 26))


def draw_vines(
    screen: pygame.Surface,
    vines: list[Vine],
    cam_x: float,
    ox: int = 0,
    oy: int = 0,
    held: Vine | None = None,
    hang=None,
    debug: bool = False,
) -> None:
    for vine in vines:
        taut = vine is held
        end = hang if taut else None
        vine.draw_visual(screen, cam_x, ox, oy, hang=end, taut=taut)
        if debug:
            vine.draw_debug(screen, cam_x, ox, oy, hang=end)

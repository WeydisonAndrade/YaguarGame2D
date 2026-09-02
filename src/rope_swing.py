"""Flecha com corda só na floresta das poças: o galho vira pêndulo.

Fora deste trecho o arco não muda. Aqui a flecha sai com a corda no talão;
se cravar no galho, Yáguar se balança para cruzar a areia.
"""
from __future__ import annotations

import math

import pygame

from src.config import (
    CONTINUE_DRAW_X,
    GRAVITY,
    GROUND_Y,
    ROPE_BRANCH_H,
    ROPE_BRANCH_W,
    ROPE_BRANCH_X,
    ROPE_BRANCH_Y,
    ROPE_DAMPING,
    ROPE_HANG_CLEARANCE,
    ROPE_MAX_ANGLE,
    ROPE_OMEGA_MAX,
    ROPE_PUMP,
    ROPE_REEL_TIME,
)

ROPE_DARK = (72, 48, 24)
ROPE_MID = (118, 82, 38)
ROPE_LIT = (168, 124, 62)
ROPE_EMBED = 54.0
_TIP_CACHE: dict[int, float] = {}


def in_zone(player) -> bool:
    """True à direita da primeira árvore deste trecho — onde estão as poças."""
    return int(player.rect.centerx) >= CONTINUE_DRAW_X


def branch_rect() -> pygame.Rect:
    return pygame.Rect(ROPE_BRANCH_X, ROPE_BRANCH_Y, ROPE_BRANCH_W, ROPE_BRANCH_H)


def tree_rects() -> tuple[pygame.Rect, ...]:
    """Só a madeira da segunda árvore: galho e tronco, sem musgo nem arbustos."""
    x0 = CONTINUE_DRAW_X
    return (
        pygame.Rect(x0 + 300, 146, 110, 24),
        pygame.Rect(x0 + 400, 134, 130, 36),
        pygame.Rect(x0 + 520, 108, 155, 46),
        pygame.Rect(x0 + 660, 92, 155, 68),
        pygame.Rect(x0 + 768, 40, 250, 88),
        pygame.Rect(x0 + 800, 80, 220, 340),
    )


def tree_hit_point(arrow) -> tuple[float, float] | None:
    """Primeiro ponto em que o voo entra na árvore; None se não acertou madeira."""
    p0, p1 = arrow.flight_segment()
    best: tuple[float, float] | None = None
    best_d = 1e9
    for box in tree_rects():
        if box.collidepoint(p0):
            d = 0.0
            pt = (float(p0[0]), float(p0[1]))
        else:
            clipped = box.clipline(p0, p1)
            if not clipped:
                tip = arrow.tip_rect()
                if not box.colliderect(tip):
                    continue
                pt = (float(tip.centerx), float(tip.centery))
                d = math.hypot(pt[0] - p0[0], pt[1] - p0[1])
            else:
                (x, y), _end = clipped
                pt = (float(x), float(y))
                d = math.hypot(pt[0] - p0[0], pt[1] - p0[1])
        if d < best_d:
            best_d = d
            best = pt
    return best


def arrow_hits_branch(arrow) -> bool:
    return tree_hit_point(arrow) is not None


def _arrow_tip_offset(surf: pygame.Surface) -> float:
    """Distância do centro até a ponta opaca — ignora padding transparente."""
    key = id(surf)
    cached = _TIP_CACHE.get(key)
    if cached is not None:
        return cached
    w, h = surf.get_width(), surf.get_height()
    cx = (w - 1) * 0.5
    nose = max(8.0, w * 0.48)
    for x in range(w - 1, -1, -1):
        for y in range(h):
            if surf.get_at((x, y))[3] > 20:
                nose = max(6.0, float(x) - cx)
                _TIP_CACHE[key] = nose
                return nose
    _TIP_CACHE[key] = nose
    return nose


def embed_arrow(arrow, x: float, y: float) -> None:
    """Crava a ponta opaca no impacto, no ângulo do voo."""
    speed = math.hypot(arrow.vx, arrow.vy) or 1.0
    ux, uy = arrow.vx / speed, arrow.vy / speed
    arrow._flight_ux = ux
    arrow._flight_uy = uy
    nose = _arrow_tip_offset(arrow._base)
    tip_x = x + ux * ROPE_EMBED
    tip_y = y + uy * ROPE_EMBED
    arrow.fx = tip_x - ux * nose
    arrow.fy = tip_y - uy * nose
    arrow._orient()
    img = arrow.image
    w, h = img.get_width(), img.get_height()
    cx, cy = w * 0.5, h * 0.5
    best = -1.0e9
    ox = oy = 0.0
    for py in range(h):
        for px in range(w):
            if img.get_at((px, py))[3] <= 20:
                continue
            proj = (px - cx) * ux + (py - cy) * uy
            if proj > best:
                best = proj
                ox, oy = px - cx, py - cy
    arrow.fx = tip_x - ox + ux
    arrow.fy = tip_y - oy + uy
    arrow.rect = img.get_rect(center=(round(arrow.fx), round(arrow.fy)))
    arrow._stick(30.0)
    arrow.anchor_hit = True


def active(player) -> bool:
    return bool(getattr(player, "swinging", False))


def reset(player) -> None:
    """Solta a corda no respawn ou ao sair do pêndulo."""
    player.swinging = False
    player.on_vine = False
    player.rope_ax = 0.0
    player.rope_ay = 0.0
    player.rope_len = 0.0
    player.rope_len_from = 0.0
    player.rope_reel = 0.0
    player.rope_angle = 0.0
    player.rope_omega = 0.0
    arrow = getattr(player, "rope_arrow", None)
    player.rope_arrow = None
    if arrow is not None:
        arrow.kill()


def _hands(player) -> tuple[float, float]:
    if hasattr(player, "hand_anchor"):
        return player.hand_anchor()
    body = player.hurtbox
    facing = getattr(player, "facing", 1)
    return (float(body.centerx + facing * 10), float(body.top + 18))


def _hang(ax: float, ay: float, length: float, angle: float) -> tuple[float, float]:
    return (ax + length * math.sin(angle), ay + length * math.cos(angle))


def _place_player(player, hx: float, hy: float) -> None:
    """Coloca o peito no pêndulo, pés livres no ar."""
    body = player.hurtbox
    dx = hx - body.centerx
    dy = hy - body.centery
    player.rect.x = int(round(player.rect.x + dx))
    player.rect.y = int(round(player.rect.y + dy))
    player.vel_y = 0
    player.on_ground = False
    player.air_state = "jumping"


def _nock(arrow) -> tuple[float, float]:
    speed = math.hypot(arrow.vx, arrow.vy)
    if speed < 1e-3:
        width = max(8.0, arrow.image.get_width() * 0.42)
        return (arrow.fx - width, arrow.fy)
    tail = max(8.0, getattr(arrow, "_base", arrow.image).get_width() * 0.46)
    return (arrow.fx - arrow.vx / speed * tail, arrow.fy - arrow.vy / speed * tail)


def attach(player, arrow) -> None:
    """Crava a flecha no galho e puxa Yáguar para o pêndulo."""
    from src import quicksand

    ax = float(arrow.fx)
    ay = float(arrow.fy)
    hx, hy = _hands(player)
    dist = max(48.0, math.hypot(hx - ax, hy - ay))
    target = max(96.0, min(dist, GROUND_Y - ROPE_HANG_CLEARANCE - ay))
    player.swinging = True
    player.on_vine = True
    player.rope_ax = ax
    player.rope_ay = ay
    player.rope_len = target
    player.rope_len_from = dist
    player.rope_reel = ROPE_REEL_TIME if dist > target + 8 else 0.0
    player.rope_angle = math.atan2(hx - ax, hy - ay)
    player.rope_angle = max(-ROPE_MAX_ANGLE, min(ROPE_MAX_ANGLE, player.rope_angle))
    toward = 1.0 if hx <= ax else -1.0
    player.rope_omega = 0.055 * toward
    player.rope_arrow = arrow
    player.air_vx = 0.0
    player._cancel_bow()
    quicksand.reset(player)
    arrow.stuck_life = 60.0
    length = dist if player.rope_reel > 0 else target
    _place_player(player, *_hang(ax, ay, length, player.rope_angle))


def release(player) -> None:
    """Solta a corda e devolve o momentum tangencial."""
    if not player.swinging:
        return
    angle = float(player.rope_angle)
    omega = float(player.rope_omega)
    length = max(8.0, float(player.rope_len))
    player.air_vx = omega * length * math.cos(angle)
    player.vel_y = -omega * length * math.sin(angle)
    player.on_ground = False
    player.air_state = "jumping" if player.vel_y < 0 else "falling"
    reset(player)


def step(player, keys, dt: float) -> None:
    """Integra o pêndulo; W/espaço solta no pico do balanço."""
    dt = max(1e-4, float(dt))
    if keys[pygame.K_w] or keys[pygame.K_UP] or keys[pygame.K_SPACE]:
        if not getattr(player, "_jump_held", False):
            release(player)
            player._jump_held = True
            return
    player._jump_held = bool(keys[pygame.K_w] or keys[pygame.K_UP] or keys[pygame.K_SPACE])

    ax, ay = float(player.rope_ax), float(player.rope_ay)
    target = float(player.rope_len)
    if player.rope_reel > 0:
        player.rope_reel = max(0.0, player.rope_reel - dt)
        t = 1.0 - (player.rope_reel / ROPE_REEL_TIME)
        t = t * t * (3.0 - 2.0 * t)
        length = player.rope_len_from + (target - player.rope_len_from) * t
    else:
        length = target
    length = max(48.0, length)

    pump = 0.0
    left = bool(keys[pygame.K_a] or keys[pygame.K_LEFT])
    right = bool(keys[pygame.K_d] or keys[pygame.K_RIGHT])
    if right and player.rope_omega >= 0:
        pump = ROPE_PUMP
    elif left and player.rope_omega <= 0:
        pump = -ROPE_PUMP

    frames = dt * 60.0
    alpha = -(GRAVITY / length) * math.sin(player.rope_angle) + pump
    omega = (player.rope_omega + alpha * frames) * ROPE_DAMPING
    omega = max(-ROPE_OMEGA_MAX, min(ROPE_OMEGA_MAX, omega))
    angle = player.rope_angle + omega * frames
    if angle > ROPE_MAX_ANGLE:
        angle = ROPE_MAX_ANGLE
        omega *= -0.28
    elif angle < -ROPE_MAX_ANGLE:
        angle = -ROPE_MAX_ANGLE
        omega *= -0.28
    player.rope_angle = angle
    player.rope_omega = omega
    player.facing = 1 if omega >= 0 else -1
    _place_player(player, *_hang(ax, ay, length, angle))


def apply_pose(player) -> None:
    angle = float(getattr(player, "rope_angle", 0.0))
    if angle < -0.28:
        name = "swing_left"
    elif angle > 0.28:
        name = "swing_right"
    else:
        name = "swing_center"
    frames = getattr(player, "frames", {})
    if name not in frames:
        name = "jump" if "jump" in frames else "idle"
    player._set_pose(name)


def _draw_rope(screen: pygame.Surface, x0: float, y0: float, x1: float, y1: float, sag: float) -> None:
    dx, dy = x1 - x0, y1 - y0
    dist = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / dist, dx / dist
    mx = (x0 + x1) * 0.5 + nx * sag
    my = (y0 + y1) * 0.5 + ny * sag
    pts = [(int(x0), int(y0)), (int(mx), int(my)), (int(x1), int(y1))]
    pygame.draw.lines(screen, ROPE_DARK, False, pts, 5)
    pygame.draw.lines(screen, ROPE_MID, False, pts, 3)
    pygame.draw.lines(screen, ROPE_LIT, False, pts, 1)


def draw(screen: pygame.Surface, player, projectiles, cam: int, offset: tuple[float, float]) -> None:
    """Corda no talão da flecha em voo, ou tensa até as mãos no balanço."""
    ox, oy = offset
    if active(player):
        hx, hy = _hands(player)
        _draw_rope(
            screen,
            player.rope_ax + ox,
            player.rope_ay + oy,
            hx + ox,
            hy + oy,
            sag=2.0,
        )
        return
    for proj in projectiles:
        if not getattr(proj, "roped", False) or getattr(proj, "spent", False):
            continue
        if not proj.alive():
            continue
        nx, ny = _nock(proj)
        hx, hy = _hands(player)
        dist = math.hypot(hx - nx, hy - ny)
        sag = min(28.0, dist * 0.07)
        _draw_rope(screen, hx + ox, hy + oy, nx + ox, ny + oy, sag)


def draw_debug(screen: pygame.Surface, cam: int, oy: int = 0) -> None:
    for box in tree_rects():
        pygame.draw.rect(screen, (210, 170, 70), box.move(-cam, oy), 1)

"""Areia movediça só na floresta depois da última clareira.

A laje continua sólida (não é fenda). Quem pisa na poça afunda devagar até
o mesmo respawn da queda. O visual é só o corpo sumindo no chão pintado.
"""
from __future__ import annotations

import pygame

from src.config import (
    CONTINUE_SAND_POOLS,
    GROUND_Y,
    QUICKSAND_RECESS,
    QUICKSAND_RISE_SPEED,
    QUICKSAND_SINK_SPEED,
    QUICKSAND_SLOW,
    QUICKSAND_SWALLOW_DEPTH,
)


def pool_containing(x: float) -> tuple[int, int] | None:
    """Poça cuja faixa X contém o ponto; None se está no chão firme."""
    px = int(x)
    for left, width in CONTINUE_SAND_POOLS:
        if left <= px < left + width:
            return (left, width)
    return None


def feet_in_quicksand(rect: pygame.Rect) -> tuple[int, int] | None:
    """Poça sob os pés (faixa da hitbox, não só o centro)."""
    left = rect.x + 12
    right = rect.x + max(12, rect.width - 12)
    for pool_x, width in CONTINUE_SAND_POOLS:
        if right > pool_x and left < pool_x + width:
            return (pool_x, width)
    return None


def slow_factor(player) -> float:
    """Andar na poça é pesado; fora dela a velocidade não muda."""
    if getattr(player, "sand_sink", 0) > 0 or feet_in_quicksand(player.rect):
        return QUICKSAND_SLOW
    return 1.0


def can_jump(player) -> bool:
    """Na areia não dá para pular para fora; o pulo aéreo anterior segue valendo."""
    if getattr(player, "sand_sink", 0) > 0:
        return False
    if player.on_ground and feet_in_quicksand(player.rect):
        return False
    return True


def reset(player) -> None:
    """Zera o afundamento — respawn ou ao sair da poça."""
    player.sand_rise = 0.0
    player.sand_sink = 0.0


def swallowed(player) -> bool:
    """True quando a areia já cobriu o bastante para o respawn."""
    return getattr(player, "sand_sink", 0.0) >= QUICKSAND_SWALLOW_DEPTH


def after_physics(player, dt: float) -> None:
    """Sobe o piso até os pés e, em seguida, puxa o corpo para baixo."""
    if getattr(player, "swinging", False):
        return
    pool = feet_in_quicksand(player.rect)
    sinking = getattr(player, "sand_sink", 0.0) > 0
    if pool is None:
        reset(player)
        return
    if not player.on_ground and not sinking:
        return

    dt = max(1e-4, float(dt))
    rise = float(getattr(player, "sand_rise", 0.0))
    sink = float(getattr(player, "sand_sink", 0.0))
    player.vel_y = 0
    player.on_ground = True
    player.air_state = "grounded"
    if rise < QUICKSAND_RECESS:
        rise = min(float(QUICKSAND_RECESS), rise + QUICKSAND_RISE_SPEED * dt)
        player.rect.bottom = GROUND_Y + 1
    else:
        sink = min(float(QUICKSAND_SWALLOW_DEPTH), sink + QUICKSAND_SINK_SPEED * dt)
        player.rect.bottom = int(GROUND_Y + 1 + sink)
    player.sand_rise = rise
    player.sand_sink = sink


def draw(screen: pygame.Surface, player, offset: tuple[float, float]) -> None:
    """Desenha o Yáguar só acima do piso pintado — o corpo some no chão."""
    image = getattr(player, "image", None)
    if image is None:
        return
    dest = player.rect.move(int(offset[0]), int(offset[1]))
    visible = int(GROUND_Y - dest.top)
    if visible <= 0:
        return
    visible = min(visible, image.get_height())
    area = pygame.Rect(0, 0, image.get_width(), visible)
    screen.blit(image, dest, area)
    flash = getattr(player, "flash_timer", 0)
    if flash <= 0:
        return
    color = getattr(player, "flash_color", (255, 255, 255))
    overlay = image.copy()
    strength = min(180, flash * 22)
    overlay.fill((color[0], color[1], color[2], 0), special_flags=pygame.BLEND_RGBA_ADD)
    overlay.set_alpha(strength)
    screen.blit(overlay, dest, area)

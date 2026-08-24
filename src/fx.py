"""Efeitos visuais de combate — cortes, impactos, flash e números de dano."""

from __future__ import annotations

import math
import random

import pygame

from src.config import COLOR_GOLD_BRIGHT, COLOR_GOLD_LEAF, COLOR_SCARLET, SCREEN_HEIGHT, SCREEN_WIDTH

SPIRIT = (255, 228, 150)
SPIRIT_DEEP = (212, 160, 48)
CORRUPT = (220, 36, 42)
CORRUPT_GLOW = (255, 110, 70)
BLOCK = (240, 220, 150)


class CombatFX:
    """Partículas, cortes, números de dano, shake de câmera e véus de hit."""

    def __init__(self) -> None:
        self.particles: list[dict] = []
        self.slashes: list[dict] = []
        self.popups: list[dict] = []
        self.shake = 0
        self.hitstop = 0      # Frames em que o loop não atualiza a lógica
        self.hurt_veil = 0    # Véu vermelho quando o jogador leva dano
        self.hit_veil = 0     # Clarão breve no acerto
        self.ox = 0           # Offset de câmera do shake
        self.oy = 0
        self._font = None
        self.rings: list[dict] = []
        self.motes: list[dict] = []

    def _popup_font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.SysFont("georgia", 22, bold=True)
        return self._font

    def clear(self) -> None:
        """Limpa todos os efeitos ao reiniciar a fase."""
        self.particles.clear()
        self.slashes.clear()
        self.popups.clear()
        self.shake = 0
        self.hitstop = 0
        self.hurt_veil = 0
        self.hit_veil = 0
        self.ox = 0
        self.oy = 0
        self.rings.clear()
        self.motes.clear()

    def slash_attack(self, rect: pygame.Rect, facing: int, heavy: bool = False, enchanted: bool = False) -> None:
        """Arco de corte na direção do golpe da lança (ou da Garra)."""
        x = rect.centerx + facing * 8
        y = rect.centery
        self.slashes.append(
            {
                "x": x,
                "y": y,
                "facing": facing,
                "life": 18 if enchanted else (14 if heavy else 10),
                "max": 18 if enchanted else (14 if heavy else 10),
                "heavy": heavy or enchanted,
                "enchanted": enchanted,
                "angle": (-38 if facing > 0 else 38) + random.uniform(-8, 8),
            }
        )
        self._burst(x, y, facing, SPIRIT, SPIRIT_DEEP, 10 if heavy else 7, speed=3.8)
        if enchanted:
            self._burst(x, y, facing, COLOR_GOLD_BRIGHT, (160, 255, 210), 14, speed=5.2)
            self.slashes.append(
                {
                    "x": x + facing * 16,
                    "y": y - 10,
                    "facing": facing,
                    "life": 12,
                    "max": 12,
                    "heavy": True,
                    "enchanted": True,
                    "angle": (-18 if facing > 0 else 18) + random.uniform(-6, 6),
                }
            )
        self.hit_veil = max(self.hit_veil, 8 if enchanted else (5 if heavy else 3))
        self.shake = max(self.shake, 6 if enchanted else (4 if heavy else 2))

    def hit_enemy(self, x: float, y: float, facing: int, damage: int, heavy: bool = False) -> None:
        """Impacto no inimigo: faíscas, número de dano, shake e hitstop."""
        self._burst(x, y, facing, SPIRIT, (255, 255, 255), 16 if heavy else 12, speed=5.4)
        self._burst(x, y, facing, SPIRIT_DEEP, COLOR_GOLD_LEAF, 8, speed=2.6)
        self.slashes.append(
            {
                "x": x,
                "y": y,
                "facing": facing,
                "life": 8,
                "max": 8,
                "heavy": heavy,
                "enchanted": False,
                "angle": (22 if facing > 0 else -22) + random.uniform(-12, 12),
            }
        )
        self._popup(x, y - 28, f"-{int(damage)}", COLOR_GOLD_BRIGHT)
        self.shake = max(self.shake, 7 if heavy else 5)
        self.hitstop = max(self.hitstop, 3 if heavy else 2)
        self.hit_veil = max(self.hit_veil, 6)

    def player_hurt(self, x: float, y: float, damage: float, blocked: bool = False) -> None:
        """Feedback visual de dano no Yáguar; bloqueio gera faíscas douradas."""
        if blocked:
            self._burst(x, y, 0, BLOCK, COLOR_GOLD_LEAF, 10, speed=3.2)
            self.shake = max(self.shake, 3)
            self.hit_veil = max(self.hit_veil, 4)
            return
        self._burst(x, y, 0, CORRUPT, CORRUPT_GLOW, 18, speed=5.0)
        self._burst(x, y, 0, (80, 10, 16), CORRUPT, 8, speed=2.2)
        self._popup(x, y - 30, f"-{int(damage)}", CORRUPT_GLOW)
        self.shake = max(self.shake, 10)
        self.hitstop = max(self.hitstop, 4)
        self.hurt_veil = max(self.hurt_veil, 14)

    def yaguar_roar(self, player) -> None:
        """Explosão espiritual na lança no instante do rugido."""
        _hand, tip = player.spear_axis()
        tx, ty = tip
        self._burst(tx, ty, player.facing, SPIRIT, COLOR_GOLD_BRIGHT, 22, speed=6.2)
        self._burst(tx, ty, player.facing, (140, 255, 210), SPIRIT_DEEP, 12, speed=3.4)
        self.rings.append({"x": tx, "y": ty, "life": 22, "max": 22, "scale": 1.0})
        self.rings.append({"x": tx, "y": ty, "life": 16, "max": 16, "scale": 0.55})
        self.hit_veil = max(self.hit_veil, 10)
        self.shake = max(self.shake, 5)
        for _ in range(10):
            self._spawn_mote(tx, ty, player.facing)

    def tick_spear_magic(self, player) -> None:
        """Enquanto a lança está encantada, solta fagulhas ao longo do cabo."""
        if getattr(player, "spear_magic", 0) <= 0:
            return
        player.spear_magic -= 1
        hand, tip = player.spear_axis()
        t = random.random()
        x = hand[0] + (tip[0] - hand[0]) * t
        y = hand[1] + (tip[1] - hand[1]) * t
        if random.random() < 0.65:
            self._spawn_mote(x, y, player.facing, drift=True)

    def _spawn_mote(self, x: float, y: float, facing: int, drift: bool = False) -> None:
        ang = random.uniform(-0.8, 0.8)
        spd = random.uniform(0.4, 1.6) if drift else random.uniform(1.2, 3.2)
        self.motes.append(
            {
                "x": x + random.uniform(-4, 4),
                "y": y + random.uniform(-6, 6),
                "vx": facing * spd * 0.35 + math.cos(ang) * 0.4,
                "vy": -spd * 0.7 + math.sin(ang) * 0.3,
                "life": random.randint(14, 28),
                "max": 28,
                "size": random.choice((2, 3, 3, 4)),
                "color": random.choice((SPIRIT, COLOR_GOLD_BRIGHT, (170, 255, 214), SPIRIT_DEEP)),
            }
        )

    def _burst(
        self,
        x: float,
        y: float,
        facing: int,
        c0: tuple[int, int, int],
        c1: tuple[int, int, int],
        count: int,
        speed: float,
    ) -> None:
        """Emite um leque de partículas a partir de (x, y)."""
        for _ in range(count):
            ang = random.uniform(-math.pi, math.pi)
            if facing != 0:
                ang = math.pi / 2 + facing * random.uniform(0.4, 2.4)
            spd = random.uniform(speed * 0.45, speed)
            self.particles.append(
                {
                    "x": x + random.uniform(-8, 8),
                    "y": y + random.uniform(-12, 12),
                    "vx": math.cos(ang) * spd,
                    "vy": math.sin(ang) * spd - random.uniform(0.4, 1.8),
                    "life": random.randint(10, 20),
                    "max": 20,
                    "color": c0 if random.random() < 0.55 else c1,
                    "size": random.choice((2, 2, 3, 4)),
                    "g": 0.18,
                }
            )

    def _popup(self, x: float, y: float, text: str, color: tuple[int, int, int]) -> None:
        self.popups.append({"x": x, "y": y, "text": text, "color": color, "life": 36, "max": 36})

    def tick_flashes(self, sprites) -> None:
        """Decrementa o flash_timer de cada sprite atingido."""
        for spr in sprites:
            t = getattr(spr, "flash_timer", 0)
            if t:
                spr.flash_timer = t - 1

    def update(self) -> None:
        """Avança shake, véus, partículas, cortes e números flutuantes."""
        # O offset ox/oy é somado no blit dos sprites na PlayingState.
        if self.shake > 0:
            mag = min(11, int(self.shake))
            self.ox = random.randint(-mag, mag)
            self.oy = random.randint(-mag, mag)
            self.shake -= 1
        else:
            self.ox = 0
            self.oy = 0

        if self.hurt_veil > 0:
            self.hurt_veil -= 1
        if self.hit_veil > 0:
            self.hit_veil -= 1

        alive_p = []
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += p["g"]
            p["vx"] *= 0.94
            p["life"] -= 1
            if p["life"] > 0:
                alive_p.append(p)
        self.particles = alive_p

        alive_s = []
        for s in self.slashes:
            s["life"] -= 1
            if s["life"] > 0:
                alive_s.append(s)
        self.slashes = alive_s

        alive_n = []
        for n in self.popups:
            n["y"] -= 0.85
            n["life"] -= 1
            if n["life"] > 0:
                alive_n.append(n)
        self.popups = alive_n

        alive_r = []
        for ring in self.rings:
            ring["life"] -= 1
            if ring["life"] > 0:
                alive_r.append(ring)
        self.rings = alive_r

        alive_m = []
        for mote in self.motes:
            mote["x"] += mote["vx"]
            mote["y"] += mote["vy"]
            mote["vy"] -= 0.04
            mote["life"] -= 1
            if mote["life"] > 0:
                alive_m.append(mote)
        self.motes = alive_m

    def draw_world(self, screen: pygame.Surface) -> None:
        """Desenha cortes, faíscas e popups no espaço do mundo (com shake)."""
        for s in self.slashes:
            t = s["life"] / s["max"]
            w = int(28 + 70 * (1 - t * 0.35))
            h = int(10 + 16 * t)
            surf = pygame.Surface((w, h * 2 + 8), pygame.SRCALPHA)
            if s.get("enchanted"):
                col = (255, 232, 140, int(240 * t))
                core = (210, 255, 230, int(220 * t))
            elif s["heavy"]:
                col = (186, 92, 255, int(230 * t))
                core = (255, 230, 255, int(200 * t))
            else:
                col = (*SPIRIT, int(230 * t))
                core = (255, 255, 230, int(200 * t))
            pygame.draw.ellipse(surf, col, (0, 4, w, h + 4))
            pygame.draw.ellipse(surf, core, (int(w * 0.18), 6, int(w * 0.55), max(3, h - 2)))
            rot = pygame.transform.rotate(surf, s["angle"])
            screen.blit(rot, rot.get_rect(center=(int(s["x"] + self.ox), int(s["y"] + self.oy))))

        for p in self.particles:
            t = p["life"] / p["max"]
            alpha = int(255 * t)
            r = max(1, int(p["size"] * (0.45 + t)))
            blob = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(blob, (*p["color"], alpha), (r, r), r)
            screen.blit(blob, (int(p["x"] + self.ox - r), int(p["y"] + self.oy - r)))

        for ring in self.rings:
            t = ring["life"] / ring["max"]
            radius = int((1.0 - t) * 52 * ring["scale"] + 10)
            alpha = int(200 * t)
            surf = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
            cx = radius + 4
            pygame.draw.circle(surf, (255, 230, 140, alpha), (cx, cx), radius, 2)
            pygame.draw.circle(surf, (170, 255, 210, int(alpha * 0.6)), (cx, cx), max(2, radius - 5), 1)
            screen.blit(surf, (int(ring["x"] + self.ox - cx), int(ring["y"] + self.oy - cx)))

        for mote in self.motes:
            t = mote["life"] / mote["max"]
            r = max(1, int(mote["size"] * (0.4 + t)))
            blob = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(blob, (*mote["color"], int(255 * t)), (r, r), r)
            screen.blit(blob, (int(mote["x"] + self.ox - r), int(mote["y"] + self.oy - r)))

        font = self._popup_font()
        for n in self.popups:
            t = n["life"] / n["max"]
            label = font.render(n["text"], True, n["color"])
            label.set_alpha(int(255 * min(1.0, t * 1.4)))
            rect = label.get_rect(center=(int(n["x"] + self.ox), int(n["y"] + self.oy)))
            screen.blit(label, rect)

    def draw_spear_magic(self, screen: pygame.Surface, player) -> None:
        """Brilho no cabo e na ponta da lança enquanto o encantamento estiver ativo."""
        if getattr(player, "spear_magic", 0) <= 0:
            return
        t = min(1.0, player.spear_magic / 56)
        pulse = 0.65 + 0.35 * math.sin(pygame.time.get_ticks() / 90.0)
        hand, tip = player.spear_axis()
        hx, hy = hand[0] + self.ox, hand[1] + self.oy
        tx, ty = tip[0] + self.ox, tip[1] + self.oy
        dx, dy = tx - hx, ty - hy
        length = max(8, int(math.hypot(dx, dy)))
        angle = -math.degrees(math.atan2(dy, dx))
        shaft = pygame.Surface((length + 24, 22), pygame.SRCALPHA)
        alpha = int(90 + 140 * t * pulse)
        pygame.draw.ellipse(shaft, (255, 228, 140, alpha), (0, 4, length + 20, 14))
        pygame.draw.ellipse(shaft, (180, 255, 220, int(alpha * 0.7)), (8, 7, int(length * 0.7), 8))
        rot = pygame.transform.rotate(shaft, angle)
        screen.blit(rot, rot.get_rect(center=(int((hx + tx) / 2), int((hy + ty) / 2))))

        flare = pygame.Surface((64, 64), pygame.SRCALPHA)
        for radius, col, a in (
            (26, (255, 236, 150), int(50 * t * pulse)),
            (16, (170, 255, 210), int(80 * t * pulse)),
            (8, (255, 255, 230), int(160 * t * pulse)),
        ):
            pygame.draw.circle(flare, (*col, a), (32, 32), radius)
        screen.blit(flare, flare.get_rect(center=(int(tx), int(ty))))

    def draw_veils(self, screen: pygame.Surface) -> None:
        """Camadas de tela cheia: vermelho no dano, ouro claro no acerto."""
        if self.hurt_veil > 0:
            veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            veil.fill((COLOR_SCARLET[0], 8, 10, int(90 * (self.hurt_veil / 14))))
            screen.blit(veil, (0, 0))
        if self.hit_veil > 0:
            veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            veil.fill((255, 240, 200, int(28 * (self.hit_veil / 6))))
            screen.blit(veil, (0, 0))


def blit_flashed(screen: pygame.Surface, sprite: pygame.sprite.Sprite, offset: tuple[int, int]) -> None:
    """Blita o sprite e, se houver flash_timer, sobrepõe um tint de impacto."""
    dest = sprite.rect.move(*offset)
    screen.blit(sprite.image, dest)
    flash = getattr(sprite, "flash_timer", 0)
    if flash <= 0:
        return
    color = getattr(sprite, "flash_color", (255, 255, 255))
    overlay = sprite.image.copy()
    strength = min(180, flash * 22)
    overlay.fill((color[0], color[1], color[2], 0), special_flags=pygame.BLEND_RGBA_ADD)
    overlay.set_alpha(strength)
    screen.blit(overlay, dest)

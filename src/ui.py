"""Interface ritual do menu — floresta, ouro velho e geometria ancestral."""

from __future__ import annotations

import math
import random

import pygame

from src.config import (
    COLOR_BARK,
    COLOR_GOLD_BRIGHT,
    COLOR_GOLD_LEAF,
    COLOR_GOLD_SHADOW,
    COLOR_INK,
    COLOR_MOSS,
    COLOR_PARCHMENT,
    COLOR_SCARLET,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TOTAL_HERBS_TO_COLLECT,
)

_TITLE_FONTS = (
    "palatinolinotype",
    "palatino",
    "georgia",
    "garamond",
    "constantia",
    "cambria",
    "timesnewroman",
    "serif",
)
_BODY_FONTS = (
    "georgia",
    "garamond",
    "constantia",
    "cambria",
    "palatinolinotype",
    "timesnewroman",
    "serif",
)


def load_font(families: tuple[str, ...], size: int, bold: bool = False) -> pygame.font.Font:
    for name in families:
        path = pygame.font.match_font(name, bold=bold)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.SysFont(families[0], size, bold=bold)


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _mix(c0: tuple[int, int, int], c1: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return (
        int(_lerp(c0[0], c1[0], t)),
        int(_lerp(c0[1], c1[1], t)),
        int(_lerp(c0[2], c1[2], t)),
    )


def blit_centered(screen: pygame.Surface, surf: pygame.Surface, center: tuple[int, int]) -> pygame.Rect:
    rect = surf.get_rect(center=center)
    screen.blit(surf, rect)
    return rect


def blit_spaced(
    screen: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    color: tuple[int, int, int],
    center: tuple[int, int],
    tracking: int = 14,
) -> pygame.Rect:
    glyphs = [font.render(ch, True, color) for ch in text]
    width = sum(g.get_width() for g in glyphs) + tracking * max(0, len(glyphs) - 1)
    height = max((g.get_height() for g in glyphs), default=0)
    x = center[0] - width // 2
    y = center[1] - height // 2
    for glyph in glyphs:
        screen.blit(glyph, (x, y + (height - glyph.get_height()) // 2))
        x += glyph.get_width() + tracking
    return pygame.Rect(center[0] - width // 2, y, width, height)


def _make_vignette() -> pygame.Surface:
    surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    cx, cy = SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.42
    max_r = math.hypot(SCREEN_WIDTH, SCREEN_HEIGHT) * 0.62
    for i in range(90, 0, -1):
        t = i / 90
        radius = int(max_r * t)
        alpha = int(210 * (t ** 2.4))
        pygame.draw.circle(surf, (4, 8, 6, alpha), (int(cx), int(cy)), radius, 6)
    top = pygame.Surface((SCREEN_WIDTH, 110), pygame.SRCALPHA)
    for y in range(110):
        a = int(150 * (1 - y / 110))
        pygame.draw.line(top, (6, 8, 6, a), (0, y), (SCREEN_WIDTH, y))
    surf.blit(top, (0, 0))
    bottom = pygame.Surface((SCREEN_WIDTH, 220), pygame.SRCALPHA)
    for y in range(220):
        a = int(200 * (y / 220) ** 1.35)
        pygame.draw.line(bottom, (6, 8, 6, a), (0, y), (SCREEN_WIDTH, y))
    surf.blit(bottom, (0, SCREEN_HEIGHT - 220))
    return surf


def _make_wash() -> pygame.Surface:
    surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    surf.fill((8, 14, 10, 118))
    return surf


class RitualMenu:
    def __init__(self) -> None:
        self.font_kicker = load_font(_BODY_FONTS, 15, bold=True)
        self.font_title = load_font(_TITLE_FONTS, 62, bold=True)
        self.font_subtitle = load_font(_TITLE_FONTS, 24)
        self.font_panel = load_font(_BODY_FONTS, 16, bold=True)
        self.font_key = load_font(_BODY_FONTS, 13, bold=True)
        self.font_body = load_font(_BODY_FONTS, 16)
        self.font_cta = load_font(_TITLE_FONTS, 20, bold=True)
        self.font_hint = load_font(_BODY_FONTS, 14)

        self.vignette = _make_vignette()
        self.wash = _make_wash()
        self.cta_rect = pygame.Rect(0, 0, 0, 0)
        self.time = 0.0
        self.embers = [
            {
                "x": random.uniform(40, SCREEN_WIDTH - 40),
                "y": random.uniform(40, SCREEN_HEIGHT - 80),
                "phase": random.uniform(0, math.tau),
                "speed": random.uniform(0.35, 0.85),
                "size": random.choice((1, 1, 2)),
            }
            for _ in range(22)
        ]

        self.left_rites = (
            (("A / D", "Setas"), "Andar"),
            (("SHIFT",), "Correr"),
            (("W / ↑", "ESPAÇO"), "Pular"),
            (("S / ↓",), "Agachar"),
        )
        self.right_rites = (
            (("J", "Clique Esq."), "Ataque com lança"),
            (("K", "Clique Dir."), "Defesa ancestral"),
            (("E",), "Ervas sagradas"),
            (("ESC", "P"), "Pausar"),
        )

    def update(self, dt: float = 1 / 60) -> None:
        self.time += dt
        for ember in self.embers:
            ember["phase"] += dt * ember["speed"]
            ember["y"] -= dt * 8 * ember["speed"]
            ember["x"] += math.sin(ember["phase"] * 1.4) * 0.35
            if ember["y"] < 20:
                ember["y"] = SCREEN_HEIGHT - 30
                ember["x"] = random.uniform(40, SCREEN_WIDTH - 40)

    def draw_backdrop(self, screen: pygame.Surface, game, focus: tuple[float, float]) -> None:
        game.parallax.draw_back(screen, focus)
        screen.blit(self.wash, (0, 0))
        self._draw_scarlet_moon(screen)
        self._draw_embers(screen)
        screen.blit(self.vignette, (0, 0))

    def draw(self, screen: pygame.Surface) -> None:
        pulse = 0.5 + 0.5 * math.sin(self.time * 2.2)
        self._draw_header(screen, pulse)
        self._draw_rites_panel(screen)
        self._draw_cta(screen, pulse)

    def _draw_scarlet_moon(self, screen: pygame.Surface) -> None:
        glow = pygame.Surface((220, 220), pygame.SRCALPHA)
        cx, cy = 110, 110
        for radius, alpha in ((96, 18), (72, 28), (48, 46), (28, 70)):
            pygame.draw.circle(glow, (*COLOR_SCARLET, alpha), (cx, cy), radius)
        pygame.draw.circle(glow, (196, 86, 64, 90), (cx, cy), 18)
        screen.blit(glow, (SCREEN_WIDTH - 250, 8))

    def _draw_embers(self, screen: pygame.Surface) -> None:
        layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for ember in self.embers:
            flicker = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(ember["phase"] * 3))
            alpha = int(90 + 130 * flicker)
            color = (*_mix(COLOR_GOLD_LEAF, COLOR_GOLD_BRIGHT, flicker), alpha)
            pygame.draw.circle(layer, color, (int(ember["x"]), int(ember["y"])), ember["size"])
        screen.blit(layer, (0, 0))

    def _draw_header(self, screen: pygame.Surface, pulse: float) -> None:
        kicker = self.font_kicker.render("FASE I  ·  O CORAÇÃO DA FLORESTA", True, COLOR_GOLD_LEAF)
        blit_centered(screen, kicker, (SCREEN_WIDTH // 2, 46))

        title_color = _mix(COLOR_GOLD_LEAF, COLOR_GOLD_BRIGHT, 0.35 + 0.45 * pulse)
        for ox, oy in ((2, 3), (0, 2), (-1, 1)):
            blit_spaced(
                screen,
                self.font_title,
                "YÁGUAR",
                COLOR_GOLD_SHADOW,
                (SCREEN_WIDTH // 2 + ox, 104 + oy),
                tracking=16,
            )
        blit_spaced(screen, self.font_title, "YÁGUAR", title_color, (SCREEN_WIDTH // 2, 104), tracking=16)

        subtitle = self.font_subtitle.render("O Guardião da Floresta", True, COLOR_PARCHMENT)
        blit_centered(screen, subtitle, (SCREEN_WIDTH // 2, 156))
        self._draw_spirit_divider(screen, SCREEN_WIDTH // 2, 182, 210)

    def _draw_spirit_divider(self, screen: pygame.Surface, cx: int, cy: int, half: int) -> None:
        left, right = cx - half, cx + half
        pygame.draw.line(screen, COLOR_GOLD_SHADOW, (left, cy), (cx - 22, cy), 2)
        pygame.draw.line(screen, COLOR_GOLD_LEAF, (cx + 22, cy), (right, cy), 2)
        pygame.draw.line(screen, COLOR_GOLD_SHADOW, (cx + 22, cy), (right, cy), 1)
        diamond = ((cx, cy - 8), (cx + 9, cy), (cx, cy + 8), (cx - 9, cy))
        pygame.draw.polygon(screen, COLOR_GOLD_LEAF, diamond)
        pygame.draw.polygon(screen, COLOR_GOLD_SHADOW, diamond, 1)
        pygame.draw.circle(screen, COLOR_SCARLET, (cx, cy), 3)

    def _draw_rites_panel(self, screen: pygame.Surface) -> None:
        panel = pygame.Rect(118, 204, SCREEN_WIDTH - 236, 248)
        pygame.draw.rect(screen, COLOR_INK, panel.move(0, 6), border_radius=10)

        body = pygame.Surface(panel.size, pygame.SRCALPHA)
        pygame.draw.rect(body, (*COLOR_BARK, 220), body.get_rect(), border_radius=10)
        pygame.draw.rect(body, (*COLOR_MOSS, 40), body.get_rect(), border_radius=10)
        screen.blit(body, panel.topleft)

        pygame.draw.rect(screen, COLOR_GOLD_SHADOW, panel, 3, border_radius=10)
        inner = panel.inflate(-10, -10)
        pygame.draw.rect(screen, COLOR_GOLD_LEAF, inner, 1, border_radius=8)
        self._draw_corner_marks(screen, panel)
        self._draw_zigzag(screen, panel.x + 28, panel.y + 38, panel.w - 56)

        header = self.font_panel.render("RITOS DO GUERREIRO", True, COLOR_GOLD_BRIGHT)
        blit_centered(screen, header, (panel.centerx, panel.y + 24))

        mid_x = panel.centerx
        pygame.draw.line(screen, COLOR_GOLD_SHADOW, (mid_x, panel.y + 54), (mid_x, panel.bottom - 22), 1)

        left_title = self.font_kicker.render("MOVIMENTO", True, COLOR_GOLD_LEAF)
        right_title = self.font_kicker.render("COMBATE", True, COLOR_GOLD_LEAF)
        screen.blit(left_title, (panel.x + 36, panel.y + 50))
        screen.blit(right_title, (mid_x + 28, panel.y + 50))

        self._draw_rite_column(screen, self.left_rites, panel.x + 36, panel.y + 78)
        self._draw_rite_column(screen, self.right_rites, mid_x + 28, panel.y + 78)

    def _draw_rite_column(
        self,
        screen: pygame.Surface,
        rows: tuple[tuple[tuple[str, ...], str], ...],
        x: int,
        y: int,
    ) -> None:
        for keys, label in rows:
            self._draw_key_row(screen, keys, label, x, y)
            y += 38

    def _draw_key_row(
        self,
        screen: pygame.Surface,
        keys: tuple[str, ...],
        label: str,
        x: int,
        y: int,
    ) -> None:
        cursor = x
        for key in keys:
            glyph = self.font_key.render(key, True, COLOR_PARCHMENT)
            pad_x, pad_y = 8, 4
            box = pygame.Rect(cursor, y, glyph.get_width() + pad_x * 2, glyph.get_height() + pad_y * 2)
            pygame.draw.rect(screen, COLOR_INK, box, border_radius=4)
            pygame.draw.rect(screen, COLOR_GOLD_LEAF, box, 1, border_radius=4)
            screen.blit(glyph, (box.x + pad_x, box.y + pad_y))
            cursor = box.right + 6
        text = self.font_body.render(label, True, COLOR_PARCHMENT)
        screen.blit(text, (max(cursor + 10, x + 188), y + 3))

    def _draw_corner_marks(self, screen: pygame.Surface, panel: pygame.Rect) -> None:
        size = 12
        inset = 8
        corners = (
            (panel.left + inset, panel.top + inset, 1, 1),
            (panel.right - inset, panel.top + inset, -1, 1),
            (panel.left + inset, panel.bottom - inset, 1, -1),
            (panel.right - inset, panel.bottom - inset, -1, -1),
        )
        for x, y, sx, sy in corners:
            pygame.draw.line(screen, COLOR_GOLD_LEAF, (x, y), (x + size * sx, y), 2)
            pygame.draw.line(screen, COLOR_GOLD_LEAF, (x, y), (x, y + size * sy), 2)

    def _draw_zigzag(self, screen: pygame.Surface, x: int, y: int, width: int) -> None:
        step = 10
        points = []
        toggle = 0
        px = x
        while px <= x + width:
            points.append((px, y + (0 if toggle == 0 else 5)))
            px += step
            toggle = 1 - toggle
        if len(points) >= 2:
            pygame.draw.lines(screen, COLOR_GOLD_SHADOW, False, points, 1)

    def _draw_cta(self, screen: pygame.Surface, pulse: float) -> None:
        color = _mix(COLOR_GOLD_LEAF, COLOR_GOLD_BRIGHT, pulse)
        label = self.font_cta.render("Pressione  ESPAÇO  para responder ao chamado", True, color)
        hint = self.font_hint.render("A floresta aguarda o seu protetor.", True, COLOR_PARCHMENT)
        text_rect = label.get_rect(center=(SCREEN_WIDTH // 2, 500))
        self.cta_rect = text_rect.inflate(36, 18)

        fill = pygame.Surface(self.cta_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            fill,
            (*COLOR_BARK, 130 + int(40 * pulse)),
            fill.get_rect(),
            border_radius=6,
        )
        pygame.draw.rect(fill, (*color, 160), fill.get_rect(), 1, border_radius=6)
        screen.blit(fill, self.cta_rect.topleft)
        screen.blit(label, text_rect)
        blit_centered(screen, hint, (SCREEN_WIDTH // 2, 542))


class PauseOverlay:
    def __init__(self) -> None:
        self.font_title = load_font(_TITLE_FONTS, 42, bold=True)
        self.font_sub = load_font(_TITLE_FONTS, 18)
        self.font_btn = load_font(_BODY_FONTS, 18, bold=True)
        self.font_hint = load_font(_BODY_FONTS, 14)
        self.resume_rect = pygame.Rect(0, 0, 0, 0)
        self.menu_rect = pygame.Rect(0, 0, 0, 0)
        self.time = 0.0

    def update(self, dt: float = 1 / 60) -> None:
        self.time += dt

    def hit(self, pos: tuple[int, int]) -> str | None:
        if self.resume_rect.collidepoint(pos):
            return "resume"
        if self.menu_rect.collidepoint(pos):
            return "menu"
        return None

    def draw(self, screen: pygame.Surface) -> None:
        pulse = 0.5 + 0.5 * math.sin(self.time * 2.0)
        veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        veil.fill((6, 10, 8, 168))
        screen.blit(veil, (0, 0))

        panel = pygame.Rect(262, 128, 500, 344)
        pygame.draw.rect(screen, COLOR_INK, panel.move(0, 6), border_radius=10)
        body = pygame.Surface(panel.size, pygame.SRCALPHA)
        pygame.draw.rect(body, (*COLOR_BARK, 230), body.get_rect(), border_radius=10)
        screen.blit(body, panel.topleft)
        pygame.draw.rect(screen, COLOR_GOLD_SHADOW, panel, 3, border_radius=10)
        pygame.draw.rect(screen, COLOR_GOLD_LEAF, panel.inflate(-10, -10), 1, border_radius=8)

        title_color = _mix(COLOR_GOLD_LEAF, COLOR_GOLD_BRIGHT, 0.3 + 0.4 * pulse)
        title = self.font_title.render("PAUSA", True, title_color)
        blit_centered(screen, title, (panel.centerx, panel.y + 58))
        sub = self.font_sub.render("O tempo da floresta se detém.", True, COLOR_PARCHMENT)
        blit_centered(screen, sub, (panel.centerx, panel.y + 104))

        self.resume_rect = self._draw_choice(
            screen, "Continuar a jornada", panel.centerx, panel.y + 176, pulse
        )
        self.menu_rect = self._draw_choice(
            screen, "Retornar ao menu", panel.centerx, panel.y + 236, 0.25
        )
        hint = self.font_hint.render("ESC · P · ESPAÇO  continuar    ·    M  menu", True, COLOR_GOLD_LEAF)
        blit_centered(screen, hint, (panel.centerx, panel.bottom - 36))

    def _draw_choice(
        self,
        screen: pygame.Surface,
        label: str,
        cx: int,
        cy: int,
        pulse: float,
    ) -> pygame.Rect:
        text = self.font_btn.render(label, True, COLOR_PARCHMENT)
        rect = text.get_rect(center=(cx, cy)).inflate(48, 16)
        fill = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(fill, (*COLOR_INK, 160 + int(30 * pulse)), fill.get_rect(), border_radius=6)
        pygame.draw.rect(fill, (*COLOR_GOLD_LEAF, 150), fill.get_rect(), 1, border_radius=6)
        screen.blit(fill, rect.topleft)
        screen.blit(text, text.get_rect(center=rect.center))
        return rect


HP_FILL = (168, 36, 38)
HP_GHOST = (120, 72, 48)
HP_CRIT = (220, 48, 42)
HP_SHINE = (214, 92, 86)
STM_FILL = (196, 158, 62)
STM_GHOST = (92, 70, 32)
STM_SHINE = (232, 208, 118)
HERB_LIT = (86, 168, 72)
HERB_DIM = (48, 52, 40)


class RitualHUD:
    """Barras de vida, stamina e selos do guerreiro."""

    def __init__(self) -> None:
        self.font_name = load_font(_TITLE_FONTS, 16, bold=True)
        self.font_label = load_font(_BODY_FONTS, 12, bold=True)
        self.font_num = load_font(_BODY_FONTS, 13, bold=True)
        self.font_zone = load_font(_BODY_FONTS, 14, bold=True)
        self.font_hint = load_font(_BODY_FONTS, 12)
        self.hp_ghost = 100.0
        self.stm_ghost = 100.0
        self.time = 0.0
        self.hurt_pulse = 0.0

    def update(self, game, dt: float = 1 / 60) -> None:
        self.time += dt
        player = game.player
        hp = float(player.health)
        stm = float(player.stamina)
        if hp < self.hp_ghost:
            self.hp_ghost = max(hp, self.hp_ghost - player.max_health * dt * 0.55)
            self.hurt_pulse = 1.0
        else:
            self.hp_ghost = hp
        if stm < self.stm_ghost:
            self.stm_ghost = max(stm, self.stm_ghost - player.max_stamina * dt * 0.7)
        else:
            self.stm_ghost = stm
        self.hurt_pulse = max(0.0, self.hurt_pulse - dt * 2.4)

    def draw(self, game, screen: pygame.Surface, zone: str) -> None:
        self._draw_player_plate(game, screen)
        self._draw_chrome(screen, zone)
        self._draw_enemy_bars(game, screen)

    def _draw_player_plate(self, game, screen: pygame.Surface) -> None:
        player = game.player
        plate = pygame.Rect(16, 14, 368, 118)
        body = pygame.Surface(plate.size, pygame.SRCALPHA)
        pygame.draw.rect(body, (*COLOR_BARK, 200), body.get_rect(), border_radius=8)
        screen.blit(body, plate.topleft)
        pygame.draw.rect(screen, COLOR_GOLD_SHADOW, plate, 2, border_radius=8)
        pygame.draw.rect(screen, COLOR_GOLD_LEAF, plate.inflate(-6, -6), 1, border_radius=6)

        name = self.font_name.render("YÁGUAR", True, COLOR_GOLD_BRIGHT)
        screen.blit(name, (plate.x + 16, plate.y + 8))
        hp_txt = self.font_num.render(
            f"{max(0, int(player.health))}/{player.max_health}", True, COLOR_PARCHMENT
        )
        screen.blit(hp_txt, (plate.right - hp_txt.get_width() - 14, plate.y + 10))

        crit = player.health / player.max_health <= 0.3
        pulse = 0.5 + 0.5 * math.sin(self.time * 7.0) if crit else 0.0
        hp_color = _mix(HP_FILL, HP_CRIT, 0.45 + 0.55 * pulse) if crit else HP_FILL
        if self.hurt_pulse > 0:
            hp_color = _mix(hp_color, (255, 220, 200), self.hurt_pulse * 0.55)

        self._draw_bar(
            screen,
            plate.x + 16,
            plate.y + 34,
            336,
            16,
            player.health / player.max_health,
            self.hp_ghost / player.max_health,
            hp_color,
            HP_GHOST,
            HP_SHINE,
            ticks=10,
        )
        stm_label = self.font_label.render("FÔLEGO", True, COLOR_GOLD_LEAF)
        screen.blit(stm_label, (plate.x + 16, plate.y + 54))
        self._draw_bar(
            screen,
            plate.x + 16,
            plate.y + 70,
            336,
            10,
            player.stamina / player.max_stamina,
            self.stm_ghost / player.max_stamina,
            STM_FILL,
            STM_GHOST,
            STM_SHINE,
            ticks=5,
        )

        self._draw_herb_slots(screen, plate.x + 16, plate.y + 88, game.herbs_collected)
        self._draw_garra_seal(screen, plate.right - 118, plate.y + 86, player.has_garra_espiritual)

    def _draw_bar(
        self,
        screen: pygame.Surface,
        x: int,
        y: int,
        w: int,
        h: int,
        ratio: float,
        ghost: float,
        fill: tuple[int, int, int],
        ghost_color: tuple[int, int, int],
        shine: tuple[int, int, int],
        ticks: int,
    ) -> None:
        ratio = max(0.0, min(1.0, ratio))
        ghost = max(0.0, min(1.0, ghost))
        back = pygame.Rect(x, y, w, h)
        pygame.draw.rect(screen, COLOR_INK, back, border_radius=3)
        inner = back.inflate(-4, -4)
        if ghost > 0:
            g = pygame.Rect(inner.x, inner.y, max(0, int(inner.w * ghost)), inner.h)
            pygame.draw.rect(screen, ghost_color, g, border_radius=2)
        if ratio > 0:
            f = pygame.Rect(inner.x, inner.y, max(0, int(inner.w * ratio)), inner.h)
            pygame.draw.rect(screen, fill, f, border_radius=2)
            if f.h >= 6 and f.w > 6:
                pygame.draw.rect(screen, shine, pygame.Rect(f.x, f.y, f.w, max(2, f.h // 3)), border_radius=2)
        for i in range(1, ticks):
            tx = inner.x + int(inner.w * i / ticks)
            pygame.draw.line(screen, (12, 8, 6), (tx, inner.y), (tx, inner.bottom), 1)
        pygame.draw.rect(screen, COLOR_GOLD_SHADOW, back, 1, border_radius=3)

    def _draw_herb_slots(self, screen: pygame.Surface, x: int, y: int, collected: int) -> None:
        label = self.font_label.render("ERVAS", True, COLOR_GOLD_LEAF)
        screen.blit(label, (x, y + 2))
        for i in range(TOTAL_HERBS_TO_COLLECT):
            cx = x + 58 + i * 22
            cy = y + 10
            filled = i < collected
            color = HERB_LIT if filled else HERB_DIM
            pygame.draw.circle(screen, COLOR_INK, (cx, cy), 8)
            pygame.draw.circle(screen, color, (cx, cy), 6)
            pygame.draw.circle(screen, COLOR_GOLD_LEAF if filled else COLOR_GOLD_SHADOW, (cx, cy), 8, 1)

    def _draw_garra_seal(self, screen: pygame.Surface, x: int, y: int, unlocked: bool) -> None:
        pulse = 0.5 + 0.5 * math.sin(self.time * 2.6) if unlocked else 0.0
        color = _mix(COLOR_GOLD_LEAF, COLOR_GOLD_BRIGHT, pulse) if unlocked else (90, 86, 78)
        text = "GARRA LIVRE" if unlocked else "GARRA SELADA"
        label = self.font_label.render(text, True, color)
        screen.blit(label, (x, y + 2))
        if unlocked:
            pygame.draw.circle(screen, color, (x - 10, y + 10), 4)

    def _draw_chrome(self, screen: pygame.Surface, zone: str) -> None:
        banner = self.font_zone.render(zone, True, COLOR_GOLD_LEAF)
        screen.blit(banner, (32, 136))
        hint = self.font_hint.render("ESC  pausar", True, COLOR_PARCHMENT)
        screen.blit(hint, (SCREEN_WIDTH - hint.get_width() - 18, 18))

    def _draw_enemy_bars(self, game, screen: pygame.Surface) -> None:
        ox, oy = game.fx.ox, game.fx.oy
        for enemy in game.enemies:
            max_hp = max(1, getattr(enemy, "max_health", enemy.health))
            ratio = max(0.0, min(1.0, enemy.health / max_hp))
            cls = enemy.__class__.__name__
            if cls == "MapinguariBoss":
                width = 168
            elif cls == "SpectralJaguar":
                width = 128
            else:
                width = 110
            cx = enemy.hurtbox.centerx + ox
            top = enemy.rect.top + oy - 14
            self._draw_bar(
                screen,
                cx - width // 2,
                top,
                width,
                8,
                ratio,
                ratio,
                HP_FILL if ratio > 0.3 else HP_CRIT,
                HP_GHOST,
                HP_SHINE,
                ticks=4,
            )


class SynopsisPlate:
    """Tela de sinopse estática — floresta, letterbox e texto ritual."""

    def __init__(
        self,
        kicker: str,
        title: str,
        lines: tuple[str, ...],
        hint: str,
        scene: int = 0,
        veil: bool = False,
        accent: tuple[int, int, int] = COLOR_GOLD_BRIGHT,
    ) -> None:
        self.kicker = kicker
        self.title = title
        self.lines = lines
        self.hint = hint
        self.scene = scene
        self.veil = veil
        self.accent = accent
        self.font_kicker = load_font(_BODY_FONTS, 14, bold=True)
        self.font_title = load_font(_TITLE_FONTS, 32, bold=True)
        self.font_body = load_font(_TITLE_FONTS, 18)
        self.font_hint = load_font(_BODY_FONTS, 14)

    def draw(self, game, screen: pygame.Surface) -> None:
        game.parallax.use_scene(self.scene)
        game.parallax.draw_back(screen, (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))
        if self.veil:
            game.parallax.draw_corrupt_veil(screen)

        wash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        wash.fill((6, 10, 8, 150))
        screen.blit(wash, (0, 0))

        pygame.draw.rect(screen, COLOR_INK, (0, 0, SCREEN_WIDTH, 52))
        pygame.draw.rect(screen, COLOR_INK, (0, SCREEN_HEIGHT - 52, SCREEN_WIDTH, 52))
        pygame.draw.line(screen, COLOR_GOLD_SHADOW, (48, 52), (SCREEN_WIDTH - 48, 52), 1)
        pygame.draw.line(screen, COLOR_GOLD_SHADOW, (48, SCREEN_HEIGHT - 52), (SCREEN_WIDTH - 48, SCREEN_HEIGHT - 52), 1)

        kicker = self.font_kicker.render(self.kicker, True, COLOR_GOLD_LEAF)
        blit_centered(screen, kicker, (SCREEN_WIDTH // 2, 26))

        panel = pygame.Rect(88, 78, SCREEN_WIDTH - 176, SCREEN_HEIGHT - 156)
        body = pygame.Surface(panel.size, pygame.SRCALPHA)
        pygame.draw.rect(body, (*COLOR_BARK, 214), body.get_rect(), border_radius=10)
        screen.blit(body, panel.topleft)
        pygame.draw.rect(screen, COLOR_GOLD_SHADOW, panel, 3, border_radius=10)
        pygame.draw.rect(screen, COLOR_GOLD_LEAF, panel.inflate(-10, -10), 1, border_radius=8)

        title = self.font_title.render(self.title, True, self.accent)
        blit_centered(screen, title, (panel.centerx, panel.y + 42))
        pygame.draw.line(screen, COLOR_GOLD_SHADOW, (panel.centerx - 120, panel.y + 68), (panel.centerx - 16, panel.y + 68), 2)
        pygame.draw.line(screen, COLOR_GOLD_LEAF, (panel.centerx + 16, panel.y + 68), (panel.centerx + 120, panel.y + 68), 2)
        pygame.draw.polygon(
            screen,
            COLOR_GOLD_LEAF,
            ((panel.centerx, panel.y + 62), (panel.centerx + 8, panel.y + 68), (panel.centerx, panel.y + 74), (panel.centerx - 8, panel.y + 68)),
        )

        y = panel.y + 100
        for line in self.lines:
            if not line:
                y += 18
                continue
            color = self.accent if line.startswith("«") or line.startswith("RECOMPENSAS") or line.startswith("—") else COLOR_PARCHMENT
            surf = self.font_body.render(line, True, color)
            blit_centered(screen, surf, (panel.centerx, y))
            y += 32

        hint = self.font_hint.render(self.hint, True, COLOR_GOLD_LEAF)
        blit_centered(screen, hint, (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 26))

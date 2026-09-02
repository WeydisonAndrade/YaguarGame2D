"""Máquina de estados da sessão: menu, intro, partida, pausa, vitória e derrota.

Cada estado implementa handle_events, update e draw. A PlayingState concentra
o combate: golpes do jogador, ataques dos inimigos, coleta e transições de onda.
"""
from __future__ import annotations

import math
import pygame
from src import audio
from src.config import (SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_TEXT, COLOR_GOLD,
                        COLOR_RED, COLOR_SCARLET, TOTAL_HERBS_TO_COLLECT, GROUND_Y,
                        ONCA_WAVE_TOTAL, ONCA_WAVE_KINDS, MAPINGUARI_GATE_X, TRAIL_FALL_DAMAGE,
                        TRAIL_FALL_Y, FOREST_CROSSING_PLATFORMS, FOREST_WORLD_WIDTH,
                        TRAIL_ORIGIN_X, SAND_ORIGIN_X, CONTINUE_ORIGIN_X,
                        TRAIL_DRAW_X, SAND_DRAW_X, CONTINUE_DRAW_X,
                        CAMERA_ANCHOR_FWD, CAMERA_ANCHOR_BACK,
                        CAMERA_DEADZONE, CAMERA_LERP,
                        KEY_ATTACK, KEY_COLOR_COMPARE, MOUSE_ATTACK, MOUSE_HEAVY,
                        BOW_LOOKAHEAD, FPS)
from src.entities import YaguarPlayer, SpectralJaguar, MapinguariBoss, HerbItem, Arrow
from src.fx import blit_flashed
from src import quicksand
from src import rope_swing
from src.ui import PauseOverlay, RitualHUD, RitualMenu, SynopsisPlate
from src.cinematic import CinematicSequence

_ONCA_ZONE_NAMES = {
    "normal": "Onça Espectral",
    "pantera": "Onça Espectral",
    "espectral": "Onça Espectral",
}


def _onca_zone_label(wave_index: int) -> str:
    kind = ONCA_WAVE_KINDS[min(wave_index, len(ONCA_WAVE_KINDS) - 1)]
    nome = _ONCA_ZONE_NAMES.get(kind, "Onça")
    return f"Floresta — {nome} {wave_index + 1}/{ONCA_WAVE_TOTAL}"


HERB_HEAL = 25
HERB_REACH = 56


def _herbs_in_reach(player, herbs) -> list:
    """Ervas ao alcance dos pés — não exige encostar o sprite inteiro no ícone 32px."""
    reach = player.hurtbox.inflate(HERB_REACH * 2, HERB_REACH)
    reach.bottom = max(reach.bottom, player.rect.bottom + 8)
    return [herb for herb in list(herbs) if reach.colliderect(herb.rect)]


def _pickup_herbs(game, herbs) -> int:
    """Colhe para o bolso. A cura só acontece ao pressionar E."""
    taken = 0
    for herb in herbs:
        if getattr(game, "herbs_held", 0) >= TOTAL_HERBS_TO_COLLECT:
            break
        cx, cy = herb.rect.center
        herb.kill()
        game.herbs_held = getattr(game, "herbs_held", 0) + 1
        game.herbs_collected += 1
        taken += 1
        game.fx._burst(cx, cy, 0, (86, 168, 72), (214, 172, 78), 10, speed=3.2)
        game.fx._popup(cx, cy - 18, "ERVA", (168, 220, 120))
    if taken:
        audio.play_herb()
    return taken


def _use_sacred_herb(game) -> bool:
    """Consome uma erva guardada e cura. E é esta função."""
    if getattr(game, "herbs_held", 0) <= 0:
        return False
    body = game.player.hurtbox
    if game.player.health >= game.player.max_health:
        game.fx._popup(body.centerx, body.top - 8, "VIDA CHEIA", (214, 172, 78))
        return False
    game.herbs_held -= 1
    game.player.health = min(game.player.max_health, game.player.health + HERB_HEAL)
    game.fx._burst(body.centerx, body.centery, 0, (86, 168, 72), (214, 172, 78), 14, speed=4.0)
    game.fx._popup(body.centerx, body.top - 8, f"+{HERB_HEAL}", (168, 220, 120))
    audio.play_herb()
    return True


def _separate(player, enemy) -> None:
    """Empurra jogador e inimigo para lados opostos quando os corpos se sobrepõem."""
    if player.hurtbox.centerx <= enemy.hurtbox.centerx:
        player.rect.x -= 10
        enemy.rect.x += 14
    else:
        player.rect.x += 10
        enemy.rect.x -= 14


def _on_enemy_slain(game, playing, enemy) -> bool:
    """Rugido, onda de onças ou vitória. True se o estado da sessão mudou."""
    game.player.roar()
    if getattr(game.player, "_roar_fx", False):
        game.fx.yaguar_roar(game.player)
        game.player._roar_fx = False
    if isinstance(enemy, SpectralJaguar):
        game.jaguars_defeated += 1
        if game.jaguars_defeated < ONCA_WAVE_TOTAL:
            playing.current_zone = _onca_zone_label(game.jaguars_defeated)
            game.spawn_spectral_jaguar()
        else:
            game.player.has_garra_espiritual = True
            enemy.kill()
            game.begin_forest_crossing()
            playing.current_zone = "Floresta — o caminho se abre"
            return True
    elif isinstance(enemy, MapinguariBoss):
        game.change_state(VictoryCinematicState())
        enemy.kill()
        return True
    enemy.kill()
    return False


def _defeat_player(game) -> bool:
    """Encerra a partida se o Yáguar caiu; True quando o estado já mudou."""
    if game.player.health <= 0:
        game.change_state(GameOverState())
        return True
    return False


def _respawn_from_fall(game) -> None:
    """Devolve Yáguar ao checkpoint após cair na fenda."""
    feet = getattr(game.player, "checkpoint", None) or (TRAIL_ORIGIN_X + 80, GROUND_Y)
    game.player.health = max(0.0, game.player.health - TRAIL_FALL_DAMAGE)
    game.player.rect.midbottom = (int(feet[0]), int(feet[1]))
    game.player.vel_y = 0
    game.player.on_ground = True
    game.player.air_state = "grounded"
    game.player.invuln = 26
    quicksand.reset(game.player)
    rope_swing.reset(game.player)
    max_cam = max(0, FOREST_WORLD_WIDTH - SCREEN_WIDTH)
    game.camera_x = max(0, min(max_cam, game.player.rect.centerx - SCREEN_WIDTH // 2))
    game.fx.player_hurt(game.player.hurtbox.centerx, game.player.hurtbox.centery, TRAIL_FALL_DAMAGE, False)


def _smooth_aim_look(game) -> None:
    """Look-ahead vertical suave; não dá snap."""
    player = game.player
    if getattr(player, "bow_state", None):
        target_y = math.sin(getattr(player, "aim_angle", 0.0)) * 36.0
    else:
        target_y = 0.0
    prev = float(getattr(game, "cam_look_y", 0.0))
    game.cam_look_y = prev + (target_y - prev) * 0.16


def _follow_camera(game) -> None:
    """Câmera lateral com look-ahead: o guerreiro fica ~40% da tela ao avançar."""
    _smooth_aim_look(game)
    facing = getattr(game.player, "facing", 1)
    look_x = 0.0
    if getattr(game.player, "bow_state", None):
        look_x = math.cos(getattr(game.player, "aim_angle", 0.0)) * BOW_LOOKAHEAD
    anchor = CAMERA_ANCHOR_FWD if facing >= 0 else CAMERA_ANCHOR_BACK
    max_cam = max(0, FOREST_WORLD_WIDTH - SCREEN_WIDTH)
    cur = float(getattr(game, "camera_x", 0))
    screen_x = game.player.rect.centerx - cur
    ratio = screen_x / SCREEN_WIDTH if SCREEN_WIDTH else 0.5
    lo, hi = anchor - CAMERA_DEADZONE, anchor + CAMERA_DEADZONE
    if not getattr(game.player, "bow_state", None):
        if lo <= ratio <= hi and 0 < cur < max_cam:
            return
    target = game.player.rect.centerx - SCREEN_WIDTH * anchor + look_x
    margin = 110
    px = game.player.rect.centerx
    target = max(px - (SCREEN_WIDTH - margin), min(px - margin, target))
    target = max(0.0, min(float(max_cam), float(target)))
    game.camera_x = cur + (target - cur) * CAMERA_LERP


def _update_trail_checkpoint(player) -> None:
    """Grava o último ponto seguro no miolo de uma laje, para o respawn da queda."""
    if not player.on_ground:
        return
    if quicksand.feet_in_quicksand(player.rect):
        return
    for x, y, w, _h in FOREST_CROSSING_PLATFORMS:
        inset = 16 if w < 160 else 40
        left, right = x + inset, x + w - inset
        if left <= player.rect.centerx <= right:
            player.checkpoint = (int(max(left, min(right, player.rect.centerx))), y)
            return


def _crossing_zone_label(player) -> str:
    """Nome da região no HUD conforme o X do Yáguar na travessia."""
    x = player.rect.centerx
    if x >= MAPINGUARI_GATE_X - 80:
        return "Caminho da Montanha Sagrada"
    if x >= CONTINUE_ORIGIN_X:
        return "Floresta — areia no caminho"
    if x >= SAND_ORIGIN_X:
        return "Areia movediça — pule as fendas"
    if x >= TRAIL_ORIGIN_X:
        return "Clareira — pule sobre as fendas"
    return "Floresta — o caminho se abre"


def _draw_fendas_debug(game, screen) -> None:
    """F3: colliders, câmera e origem das regiões."""
    cam = int(getattr(game, "camera_x", 0))
    ox, oy = game.fx.ox - cam, game.fx.oy
    font = pygame.font.SysFont("consolas", 13)
    for box in FOREST_CROSSING_PLATFORMS:
        pygame.draw.rect(screen, (80, 220, 255), pygame.Rect(*box).move(ox, oy), 2)
    pygame.draw.line(screen, (220, 50, 50), (0, TRAIL_FALL_Y), (SCREEN_WIDTH, TRAIL_FALL_Y), 1)
    for seam, color in (
        (TRAIL_DRAW_X, (255, 200, 90)),
        (TRAIL_ORIGIN_X, (255, 180, 40)),
        (SAND_DRAW_X, (230, 180, 80)),
        (SAND_ORIGIN_X, (210, 160, 70)),
        (CONTINUE_DRAW_X, (120, 190, 80)),
        (CONTINUE_ORIGIN_X, (160, 210, 90)),
        (MAPINGUARI_GATE_X, (220, 80, 80)),
    ):
        sx = seam - cam
        if 0 <= sx <= SCREEN_WIDTH:
            pygame.draw.line(screen, color, (sx, 0), (sx, SCREEN_HEIGHT), 1)
    ck = game.player.checkpoint
    pygame.draw.circle(screen, (255, 220, 80), (int(ck[0] + ox), int(ck[1] - 8 + oy)), 6, 2)
    rope_swing.draw_debug(screen, cam, oy)
    p = game.player
    lines = (
        f"world_x={p.rect.centerx}  cam={cam}  feet={p.rect.bottom}",
        f"vel_y={p.vel_y:.1f}  {p.air_state}  bow={p.bow_state}  F3",
    )
    for i, text in enumerate(lines):
        screen.blit(font.render(text, True, (245, 240, 210)), (16, SCREEN_HEIGHT - 48 + i * 16))


def _draw_combat_debug(game, screen) -> None:
    """F3: ângulo, spawn, flechas, hurtboxes e look-ahead. Nunca no modo normal."""
    cam = int(getattr(game, "camera_x", 0))
    ox, oy = game.fx.ox - cam, game.fx.oy
    font = pygame.font.SysFont("consolas", 13)
    p = game.player
    pygame.draw.rect(screen, (80, 220, 120), p.hurtbox.move(ox, oy), 1)
    ax, ay = p.bow_anchor()
    pygame.draw.circle(screen, (255, 200, 80), (int(ax + ox), int(ay + oy)), 4, 1)
    sx, sy = p.arrow_spawn()
    pygame.draw.circle(screen, (255, 80, 80), (int(sx + ox), int(sy + oy)), 3)
    if p.bow_state:
        length = 48
        ex = sx + math.cos(p.aim_angle) * length
        ey = sy + math.sin(p.aim_angle) * length
        pygame.draw.line(screen, (242, 214, 132), (sx + ox, sy + oy), (ex + ox, ey + oy), 1)
        for tx, ty in p.trajectory_preview():
            pygame.draw.circle(screen, (200, 180, 90), (int(tx + ox), int(ty + oy)), 2)
        look = math.cos(p.aim_angle) * BOW_LOOKAHEAD
        pygame.draw.line(
            screen,
            (120, 180, 255),
            (p.rect.centerx + ox, 8),
            (p.rect.centerx + look + ox, 8),
            2,
        )
    for enemy in game.enemies:
        pygame.draw.rect(screen, (220, 70, 70), enemy.hurtbox.move(ox, oy), 1)
        weak = getattr(enemy, "weak_hurtbox", None)
        if weak is not None:
            pygame.draw.rect(screen, (255, 210, 40), weak.move(ox, oy), 1)
    for proj in game.projectiles:
        if isinstance(proj, Arrow):
            pygame.draw.rect(screen, (255, 140, 60), proj.tip_rect().move(ox, oy), 1)
            pygame.draw.line(
                screen,
                (180, 220, 255),
                (proj.prev_x + ox, proj.prev_y + oy),
                (proj.fx + ox, proj.fy + oy),
                1,
            )
    info = (
        f"state={p.bow_state}  ang={math.degrees(p.aim_angle):.0f}  "
        f"charge={p.bow_charge:.2f}  cam={cam}"
    )
    screen.blit(font.render(info, True, (245, 240, 210)), (16, 8))


class GameState:
    """Interface mínima de uma tela. Subclasses preenchem só o que precisam."""

    def handle_events(self, game, event): pass
    def update(self, game): pass
    def draw(self, game, screen): pass


class MenuState(GameState):
    """Tela inicial ritual: floresta viva, ritos e chamada para a sinopse."""

    def __init__(self):
        self.ui = RitualMenu()
        audio.play_menu()

    def handle_events(self, game, event):
        start = (
            event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE
        ) or (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.ui.cta_rect.collidepoint(event.pos)
        )
        if start:
            game.change_state(CinematicIntroState())

    def update(self, game):
        self.ui.update()
        game.parallax.update()

    def draw(self, game, screen):
        t = pygame.time.get_ticks() / 1000.0
        # O foco caminha devagar para o fundo da floresta parecer vivo.
        focus = (
            SCREEN_WIDTH / 2 + math.sin(t * 0.18) * 220,
            SCREEN_HEIGHT / 2 + math.cos(t * 0.14) * 70,
        )
        self.ui.draw_backdrop(screen, game, focus)
        self.ui.draw(screen)


class CinematicIntroState(GameState):
    """Pinturas da origem: após o menu, antes da floresta. Espaço pula; clique avança."""

    def __init__(self):
        audio.play_cinematic()
        self.cine = CinematicSequence()

    def _begin_play(self, game) -> None:
        game.reset_level()
        game.change_state(PlayingState())

    def handle_events(self, game, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            self._begin_play(game)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._begin_play(game)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.cine.done or self.cine.index >= max(0, self.cine.shot_count - 1):
                self._begin_play(game)
            else:
                self.cine.advance()

    def update(self, game):
        self.cine.update()
        if self.cine.done:
            self._begin_play(game)

    def draw(self, game, screen):
        self.cine.draw(screen)


class BossCinematicState(GameState):
    """Pinturas da arena do Mapinguari; ao terminar, o chefe entra na partida."""

    def __init__(self, playing: PlayingState):
        self.playing = playing
        audio.play_mapinguari()
        self.cine = CinematicSequence.mapinguari()

    def _begin_boss(self, game) -> None:
        if not any(isinstance(e, MapinguariBoss) for e in game.enemies):
            game.spawn_mapinguari()
        self.playing.current_zone = "Cume — entrada da grande Caverna"
        game.change_state(self.playing)

    def handle_events(self, game, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_ESCAPE):
            self._begin_boss(game)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.cine.done or self.cine.index >= max(0, self.cine.shot_count - 1):
                self._begin_boss(game)
            else:
                self.cine.advance()

    def update(self, game):
        self.cine.update()
        if self.cine.done:
            self._begin_boss(game)

    def draw(self, game, screen):
        self.cine.draw(screen)


class PlayingState(GameState):
    """Combate da Fase 1: onda de onças e, em seguida, o Mapinguari."""

    def __init__(self):
        # play_fight() carrega a trilha de combate e encerra o epic_music da cinemática.
        audio.play_fight()
        audio.play_onca_roar()
        self.current_zone = _onca_zone_label(0)
        self.hud = RitualHUD()

    def handle_events(self, game, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
            game.change_state(PauseState(self))
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_F3:
            game.debug_draw = not getattr(game, "debug_draw", False)
            return

        if event.type == pygame.KEYDOWN and event.key == KEY_COLOR_COMPARE:
            from src.color_profile import toggle_raw_bow_color

            toggle_raw_bow_color()
            game.player._set_pose(getattr(game.player, "_pose_name", "idle"))
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == MOUSE_ATTACK:
                if not game.player.bow_state:
                    game.player.queue_attack(heavy=False)
            elif event.button == MOUSE_HEAVY:
                game.player.queue_attack(heavy=True)

        if event.type == pygame.KEYDOWN and event.key == KEY_ATTACK:
            if not game.player.bow_state:
                game.player.queue_attack(heavy=False)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
            near = _herbs_in_reach(game.player, game.herbs)
            if near and getattr(game, "herbs_held", 0) < TOTAL_HERBS_TO_COLLECT:
                _pickup_herbs(game, near)
            else:
                _use_sacred_herb(game)

    def update(self, game):
        keys = pygame.key.get_pressed()
        mouse_pressed = pygame.mouse.get_pressed()
        dt = max(1e-4, min(0.05, float(getattr(game, "dt", 1.0 / FPS))))

        # Jogador e hitboxes da lança
        game.player.camera_x = getattr(game, "camera_x", 0)
        game.player.update(keys, mouse_pressed, dt)
        if getattr(game.player, "_roar_fx", False):
            game.fx.yaguar_roar(game.player)
            game.player._roar_fx = False
        arrow = game.player.pop_arrow()
        if arrow:
            game.projectiles.add(arrow)
            sx, sy = arrow.fx, arrow.fy
            game.fx._burst(sx, sy, game.player.facing, (236, 228, 210), (168, 118, 52), 4, speed=2.4)
        strike = game.player.pop_strike()
        if strike:
            game.attack_hitboxes.add(strike)
            heavy = getattr(game.player, "_heavy", False)
            enchanted = getattr(game.player, "spear_magic", 0) > 0
            game.fx.slash_attack(strike.rect, game.player.facing, heavy=heavy, enchanted=enchanted)
        game.attack_hitboxes.update()
        game.enemies.update(game.player.hurtbox.center)

        # Golpes corpo a corpo dos inimigos e tronco do Mapinguari
        for enemy in list(game.enemies):
            if hasattr(enemy, "pop_melee"):
                melee = enemy.pop_melee()
                if melee and melee.colliderect(game.player.hurtbox):
                    extra = getattr(enemy, "pending_damage", enemy.damage)
                    blocked = game.player.blocking
                    dealt = game.player.take_damage(extra, enemy.hurtbox.centerx)
                    if dealt:
                        game.fx.player_hurt(game.player.hurtbox.centerx, game.player.hurtbox.centery, dealt, blocked)
                    if _defeat_player(game):
                        return
            if isinstance(enemy, MapinguariBoss):
                log = enemy.pop_log()
                if log:
                    game.projectiles.add(log)

        for proj in list(game.projectiles):
            if getattr(proj, "friendly", False) or isinstance(proj, Arrow):
                proj.update(dt)
                if getattr(proj, "world_hit", False):
                    proj.world_hit = False
                    game.fx.arrow_impact(proj.fx, proj.fy, 0, 0, flesh=False)
                    audio.play_arrow_hit("rock")
                    continue
                if getattr(proj, "anchor_hit", False):
                    proj.anchor_hit = False
                    rope_swing.attach(game.player, proj)
                    continue
                if getattr(proj, "spent", False):
                    continue
                for enemy in list(game.enemies):
                    reaction = enemy.on_projectile_approach(proj)
                    if reaction == "dodge":
                        continue
                    if reaction == "deflect":
                        proj.deflect()
                        break
                    hit, weak = proj.try_hit_enemy(enemy)
                    if not hit:
                        continue
                    dmg = proj.resolve_hit(weak)
                    if dmg:
                        enemy.take_hit(dmg, game.player.hurtbox.centerx)
                        game.fx.arrow_impact(
                            enemy.hurtbox.centerx,
                            enemy.hurtbox.centery,
                            game.player.facing,
                            dmg,
                            flesh=True,
                        )
                        audio.play_arrow_hit("flesh")
                        if enemy.health <= 0:
                            if _on_enemy_slain(game, self, enemy):
                                return
                    break
            else:
                proj.update()
                if proj.rect.colliderect(game.player.hurtbox):
                    blocked = game.player.blocking
                    dealt = game.player.take_damage(proj.damage, proj.rect.centerx)
                    if dealt:
                        game.fx.player_hurt(game.player.hurtbox.centerx, game.player.hurtbox.centery, dealt, blocked)
                    proj.kill()
                    if _defeat_player(game):
                        return

        # Lança do jogador contra hurtboxes inimigas
        for hb in list(game.attack_hitboxes):
            for enemy in list(game.enemies):
                if hb.rect.colliderect(enemy.hurtbox):
                    enemy.take_hit(hb.damage, game.player.hurtbox.centerx)
                    heavy = getattr(game.player, "_heavy", False)
                    game.fx.hit_enemy(enemy.hurtbox.centerx, enemy.hurtbox.centery, game.player.facing, hb.damage, heavy)
                    hb.kill()
                    if enemy.health <= 0:
                        if _on_enemy_slain(game, self, enemy):
                            return
                    break

        near = _herbs_in_reach(game.player, game.herbs)
        if near:
            _pickup_herbs(game, near)

        # Contato corpo a corpo: dano de empurrão, exceto no meio do ataque do jogador
        for enemy in list(game.enemies):
            if game.player.hurtbox.colliderect(enemy.hurtbox):
                if game.player.attacking:
                    _separate(game.player, enemy)
                    continue
                blocked = game.player.blocking
                dealt = game.player.take_damage(enemy.damage, enemy.hurtbox.centerx)
                if dealt:
                    game.fx.player_hurt(game.player.hurtbox.centerx, game.player.hurtbox.centery, dealt, blocked)
                _separate(game.player, enemy)
                if _defeat_player(game):
                    return

        if game.zone_stage == 0 and game.jaguars_defeated >= ONCA_WAVE_TOTAL and len(game.enemies) == 0:
            game.player.has_garra_espiritual = True
            game.begin_forest_crossing()
            self.current_zone = "Floresta — o caminho se abre"

        if game.zone_stage == 1:
            _follow_camera(game)
            self.current_zone = _crossing_zone_label(game.player)
            _update_trail_checkpoint(game.player)
            if not game.player.on_ground and game.player.rect.bottom > TRAIL_FALL_Y:
                _respawn_from_fall(game)
                if _defeat_player(game):
                    return
            elif quicksand.swallowed(game.player):
                _respawn_from_fall(game)
                if _defeat_player(game):
                    return
            if game.player.rect.centerx >= MAPINGUARI_GATE_X:
                game.zone_stage = 2
                self.current_zone = "Caminho da Montanha Sagrada"
                game.change_state(BossCinematicState(self))
                return
        else:
            _smooth_aim_look(game)

        game.fx.tick_flashes(game.all_sprites)
        game.fx.tick_spear_magic(game.player)
        game.fx.update()
        game.parallax.update()
        self.hud.update(game)

    def draw(self, game, screen):
        cam = int(getattr(game, "camera_x", 0))
        look_y = float(getattr(game, "cam_look_y", 0.0))
        focus = (game.player.rect.centerx - cam, GROUND_Y - 90 + look_y)
        game.parallax.draw_back(screen, focus, cam)
        if game.zone_stage >= 2 and not game.parallax.is_boss_arena():
            game.parallax.draw_corrupt_veil(screen)

        ox, oy = game.fx.ox - cam, game.fx.oy
        for herb in game.herbs:
            screen.blit(herb.image, herb.rect.move(ox, oy))
        sinking = getattr(game.player, "sand_sink", 0) > 0
        if not sinking:
            game.fx.draw_contact_shadow(screen, game.player, (ox, oy))
        for spr in game.all_sprites:
            if (
                spr is game.player
                and game.player.invuln > 0
                and not game.player.blocking
                and game.player.invuln % 4 < 2
                and getattr(game.player, "flash_timer", 0) <= 0
            ):
                continue
            if spr is game.player and sinking:
                quicksand.draw(screen, game.player, (ox, oy))
                continue
            blit_flashed(screen, spr, (ox, oy))
        rope_swing.draw(screen, game.player, game.projectiles, cam, (ox, oy))
        if game.player.bow_state:
            game.player.draw_bow(screen, (ox, oy))
        game.fx.draw_spear_magic(screen, game.player, cam)
        for proj in game.projectiles:
            screen.blit(proj.image, proj.rect.move(ox, oy))
        if game.player.bow_state:
            game.player.draw_reticle(screen, cam, (ox, oy))

        game.fx.draw_world(screen, cam)
        game.fx.draw_veils(screen)
        game.parallax.draw_front(screen, focus)
        self.hud.draw(game, screen, self.current_zone)
        if getattr(game, "debug_draw", False):
            _draw_combat_debug(game, screen)
            if game.zone_stage == 1:
                _draw_fendas_debug(game, screen)
        from src.color_profile import using_raw_bow_color

        if using_raw_bow_color():
            font = pygame.font.SysFont("georgia", 16)
            screen.blit(font.render("F4  arco ORIGINAL", True, (242, 214, 132)), (16, SCREEN_HEIGHT - 24))


class PauseState(GameState):
    """Congela a partida e desenha o overlay; guarda o PlayingState para retomar."""

    def __init__(self, playing: PlayingState):
        self.playing = playing
        self.overlay = PauseOverlay()

    def handle_events(self, game, event):
        resume = event.type == pygame.KEYDOWN and event.key in (
            pygame.K_ESCAPE,
            pygame.K_p,
            pygame.K_SPACE,
        )
        to_menu = event.type == pygame.KEYDOWN and event.key == pygame.K_m
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            choice = self.overlay.hit(event.pos)
            resume = resume or choice == "resume"
            to_menu = to_menu or choice == "menu"
        if resume:
            game.change_state(self.playing)
        elif to_menu:
            game.change_state(MenuState())

    def update(self, game):
        self.overlay.update()

    def draw(self, game, screen):
        self.playing.draw(game, screen)
        self.overlay.draw(screen)


class VictoryCinematicState(GameState):
    """Sinopse de missão concluída; R volta ao menu."""

    def __init__(self):
        audio.play_menu()
        self.page = SynopsisPlate(
            "MISSÃO CONCLUÍDA",
            "A primeira prova",
            (
                "O espírito do Mapinguari foi purificado. A barreira da caverna caiu.",
                "Na Caverna Encantada, o Antigo Pajé revela:",
                "",
                "«Você venceu apenas a primeira prova, Yáguar.",
                "O Coração foi levado além deste mundo.»",
                "",
                "RECOMPENSAS",
                "— Amuleto ancestral do Pajé",
                "— Garra Espiritual desbloqueada",
            ),
            "Pressione  R  para retornar ao menu",
            scene=1,
        )

    def handle_events(self, game, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            game.change_state(MenuState())

    def draw(self, game, screen):
        self.page.draw(game, screen)


class GameOverState(GameState):
    """Sinopse de derrota com véu escarlate; R volta ao menu."""

    def __init__(self):
        audio.play_menu()
        self.page = SynopsisPlate(
            "DERROTA",
            "A floresta cai",
            (
                "A corrupção cobre o chão. Os rios calam.",
                "Sem o seu protetor, o coração da Amazônia se apaga.",
                "",
                "Yáguar ainda pode renascer e responder ao chamado.",
            ),
            "Pressione  R  para tentar novamente",
            scene=1,
            veil=True,
            accent=COLOR_SCARLET,
        )

    def handle_events(self, game, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            game.change_state(MenuState())

    def draw(self, game, screen):
        self.page.draw(game, screen)

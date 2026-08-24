"""Máquina de estados da sessão: menu, intro, partida, pausa, vitória e derrota.

Cada estado implementa handle_events, update e draw. A PlayingState concentra
o combate: golpes do jogador, ataques dos inimigos, coleta e transições de onda.
"""
import math
import pygame
import random
from src import audio
from src.config import (SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_TEXT, COLOR_GOLD,
                        COLOR_RED, COLOR_SCARLET, TOTAL_HERBS_TO_COLLECT, GROUND_Y, ONCA_WAVE_TOTAL)
from src.entities import YaguarPlayer, SpectralJaguar, MapinguariBoss, HerbItem
from src.fx import blit_flashed
from src.ui import PauseOverlay, RitualHUD, RitualMenu, SynopsisPlate


def _separate(player, enemy) -> None:
    """Empurra jogador e inimigo para lados opostos quando os corpos se sobrepõem."""
    if player.hurtbox.centerx <= enemy.hurtbox.centerx:
        player.rect.x -= 10
        enemy.rect.x += 14
    else:
        player.rect.x += 10
        enemy.rect.x -= 14


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
    """Placa estática da sinopse; Espaço ou clique inicia a floresta."""

    def __init__(self):
        audio.play_menu()
        self.page = SynopsisPlate(
            "FASE I  ·  O CORAÇÃO DA FLORESTA",
            "O Chamado",
            (
                "Há milhares de anos, a tribo recebeu o Coração da Floresta.",
                "Na noite da Lua Escarlate, uma entidade cósmica invadiu o templo.",
                "O antigo Pajé foi derrotado e o artefato, roubado.",
                "A corrupção se espalha. Os rios secam. Os animais enlouquecem.",
                "",
                "Yáguar, o maior guerreiro da tribo, jura salvar a Amazônia.",
            ),
            "Pressione  ESPAÇO  para avançar à floresta",
            scene=0,
        )

    def handle_events(self, game, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            game.reset_level()
            game.change_state(PlayingState())
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            game.reset_level()
            game.change_state(PlayingState())

    def draw(self, game, screen):
        self.page.draw(game, screen)


class PlayingState(GameState):
    """Combate da Fase 1: onda de onças e, em seguida, o Mapinguari."""

    def __init__(self):
        audio.play_fight()
        audio.play_onca_roar()
        self.current_zone = f"Floresta — Onça Espectral 1/{ONCA_WAVE_TOTAL}"
        self.hud = RitualHUD()

    def handle_events(self, game, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
            game.change_state(PauseState(self))
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                game.player.queue_attack(heavy=False)
            elif event.button == 3:
                game.player.queue_attack(heavy=True)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_j:
            game.player.queue_attack(heavy=False)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
            collected = pygame.sprite.spritecollide(game.player, game.herbs, True)
            if collected:
                game.herbs_collected += len(collected)
                game.player.health = min(game.player.max_health, game.player.health + 25)

    def update(self, game):
        keys = pygame.key.get_pressed()
        mouse_pressed = pygame.mouse.get_pressed()

        # Jogador e hitboxes da lança
        game.player.update(keys, mouse_pressed)
        if getattr(game.player, "_roar_fx", False):
            game.fx.yaguar_roar(game.player)
            game.player._roar_fx = False
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
            if isinstance(enemy, MapinguariBoss):
                log = enemy.pop_log()
                if log:
                    game.projectiles.add(log)

        game.projectiles.update()
        for log in list(game.projectiles):
            if log.rect.colliderect(game.player.hurtbox):
                blocked = game.player.blocking
                dealt = game.player.take_damage(log.damage, log.rect.centerx)
                if dealt:
                    game.fx.player_hurt(game.player.hurtbox.centerx, game.player.hurtbox.centery, dealt, blocked)
                log.kill()
                if game.player.health <= 0:
                    game.change_state(GameOverState())
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
                        game.player.roar()
                        if getattr(game.player, "_roar_fx", False):
                            game.fx.yaguar_roar(game.player)
                            game.player._roar_fx = False
                        if isinstance(enemy, SpectralJaguar):
                            game.jaguars_defeated += 1
                            if game.jaguars_defeated < ONCA_WAVE_TOTAL:
                                proxima = game.jaguars_defeated + 1
                                self.current_zone = f"Floresta — Onça Espectral {proxima}/{ONCA_WAVE_TOTAL}"
                                game.spawn_spectral_jaguar()
                            else:
                                game.player.has_garra_espiritual = True
                                game.zone_stage = 2
                                self.current_zone = "Caminho da Montanha Sagrada"
                                game.spawn_mapinguari()
                        elif isinstance(enemy, MapinguariBoss):
                            game.change_state(VictoryCinematicState())
                        enemy.kill()
                    break

        collected = pygame.sprite.spritecollide(game.player, game.herbs, True)
        if collected:
            game.herbs_collected += len(collected)
            game.player.health = min(game.player.max_health, game.player.health + 25)

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
                if game.player.health <= 0:
                    game.change_state(GameOverState())
                    return

        if game.zone_stage == 0 and len(game.enemies) == 0:
            game.zone_stage = 1

        game.fx.tick_flashes(game.all_sprites)
        game.fx.tick_spear_magic(game.player)
        game.fx.update()
        game.parallax.update()
        self.hud.update(game)

    def draw(self, game, screen):
        focus = (game.player.rect.centerx, GROUND_Y - 90)
        game.parallax.draw_back(screen, focus)
        if game.zone_stage > 0:
            game.parallax.draw_corrupt_veil(screen)

        ox, oy = game.fx.ox, game.fx.oy
        for herb in game.herbs:
            screen.blit(herb.image, herb.rect.move(ox, oy))
        for spr in game.all_sprites:
            # Pisca o jogador nos i-frames, a menos que esteja no flash de hit
            if (
                spr is game.player
                and game.player.invuln > 0
                and not game.player.blocking
                and game.player.invuln % 4 < 2
                and getattr(game.player, "flash_timer", 0) <= 0
            ):
                continue
            blit_flashed(screen, spr, (ox, oy))
        game.fx.draw_spear_magic(screen, game.player)
        for proj in game.projectiles:
            screen.blit(proj.image, proj.rect.move(ox, oy))

        game.fx.draw_world(screen)
        game.fx.draw_veils(screen)
        self.hud.draw(game, screen, self.current_zone)


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

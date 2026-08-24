import math
import pygame
import random
from src.config import (SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_TEXT, COLOR_GOLD, 
                        COLOR_RED, TOTAL_HERBS_TO_COLLECT, GROUND_Y, ONCA_WAVE_TOTAL)
from src.entities import YaguarPlayer, SpectralJaguar, MapinguariBoss, HerbItem
from src.ui import PauseOverlay, RitualMenu

def _separate(player, enemy) -> None:
    if player.hurtbox.centerx <= enemy.hurtbox.centerx:
        player.rect.x -= 10
        enemy.rect.x += 14
    else:
        player.rect.x += 10
        enemy.rect.x -= 14


class GameState:
    def handle_events(self, game, event): pass
    def update(self, game): pass
    def draw(self, game, screen): pass

class MenuState(GameState):
    def __init__(self):
        self.ui = RitualMenu()

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

    def draw(self, game, screen):
        t = pygame.time.get_ticks() / 1000.0
        focus = (
            SCREEN_WIDTH / 2 + math.sin(t * 0.18) * 220,
            SCREEN_HEIGHT / 2 + math.cos(t * 0.14) * 70,
        )
        self.ui.draw_backdrop(screen, game, focus)
        self.ui.draw(screen)

class CinematicIntroState(GameState):
    """Cinemática inicial baseada no Roteiro"""
    def __init__(self):
        self.story_lines = [
            "Há milhares de anos, a tribo recebeu o CORAÇÃO DA FLORESTA.",
            "Na noite da Lua Escarlate... uma entidade cósmica invadiu o templo.",
            "O antigo Pajé foi derrotado e o artefato roubado.",
            "A corrupção se espalha. Os rios secam. Os animais enlouquecem.",
            "YÁGUAR, o maior guerreiro da tribo, jura salvar a Amazônia...",
            "",
            "[ Pressione ESPAÇO para avançar à Aldeia ]"
        ]

    def handle_events(self, game, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            game.reset_level()
            game.change_state(PlayingState())

    def draw(self, game, screen):
        screen.fill((5, 5, 10))
        font = pygame.font.SysFont("arial", 22)
        y = 180
        for line in self.story_lines:
            t = font.render(line, True, COLOR_GOLD if "ESPAÇO" in line else COLOR_TEXT)
            screen.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, y))
            y += 45

class PlayingState(GameState):
    def __init__(self):
        self.current_zone = f"Floresta — Onça Espectral 1/{ONCA_WAVE_TOTAL}"

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
            # Coleta de Ervas Medicinais
            collected = pygame.sprite.spritecollide(game.player, game.herbs, True)
            if collected:
                game.herbs_collected += len(collected)
                game.player.health = min(game.player.max_health, game.player.health + 25)

    def update(self, game):
        keys = pygame.key.get_pressed()
        mouse_pressed = pygame.mouse.get_pressed()
        
        game.player.update(keys, mouse_pressed)
        strike = game.player.pop_strike()
        if strike:
            game.attack_hitboxes.add(strike)
        game.attack_hitboxes.update()
        game.enemies.update(game.player.hurtbox.center)

        for enemy in list(game.enemies):
            if hasattr(enemy, "pop_melee"):
                melee = enemy.pop_melee()
                if melee and melee.colliderect(game.player.hurtbox):
                    extra = getattr(enemy, "pending_damage", enemy.damage)
                    game.player.take_damage(extra, enemy.hurtbox.centerx)
            if isinstance(enemy, MapinguariBoss):
                log = enemy.pop_log()
                if log:
                    game.projectiles.add(log)

        game.projectiles.update()
        for log in list(game.projectiles):
            if log.rect.colliderect(game.player.hurtbox):
                game.player.take_damage(log.damage, log.rect.centerx)
                log.kill()
                if game.player.health <= 0:
                    game.change_state(GameOverState())
                    return

        for hb in list(game.attack_hitboxes):
            for enemy in list(game.enemies):
                if hb.rect.colliderect(enemy.hurtbox):
                    enemy.take_hit(hb.damage, game.player.hurtbox.centerx)
                    hb.kill()
                    if enemy.health <= 0:
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

        for enemy in list(game.enemies):
            if game.player.hurtbox.colliderect(enemy.hurtbox):
                if game.player.attacking:
                    _separate(game.player, enemy)
                    continue
                game.player.take_damage(enemy.damage, enemy.hurtbox.centerx)
                _separate(game.player, enemy)
                if game.player.health <= 0:
                    game.change_state(GameOverState())
                    return

        if game.zone_stage == 0 and len(game.enemies) == 0:
            game.zone_stage = 1

    def draw(self, game, screen):
        focus = (game.player.rect.centerx, GROUND_Y - 90)
        game.parallax.draw_back(screen, focus)
        if game.zone_stage > 0:
            game.parallax.draw_corrupt_veil(screen)

        # Desenhar Elementos
        game.herbs.draw(screen)
        game.all_sprites.draw(screen)
        game.projectiles.draw(screen)
        game.parallax.draw_front(screen, focus)

        # HUD de Status
        font = pygame.font.SysFont("arial", 18, bold=True)
        hud_zone = font.render(f"Local: {self.current_zone}", True, COLOR_GOLD)
        hud_hp = font.render(f"Vida: {int(game.player.health)}/{game.player.max_health}", True, COLOR_RED)
        hud_stm = font.render(f"Stamina: {int(game.player.stamina)}", True, COLOR_TEXT)
        hud_herbs = font.render(f"Ervas Sagradas: {game.herbs_collected}/{TOTAL_HERBS_TO_COLLECT}", True, (50, 255, 50))
        
        garra_txt = "Garra Espiritual: LIBERADA (Botão Direito)" if game.player.has_garra_espiritual else "Garra Espiritual: BLOQUEADA"
        hud_garra = font.render(garra_txt, True, COLOR_GOLD if game.player.has_garra_espiritual else (150, 150, 150))

        screen.blit(hud_zone, (20, 20))
        screen.blit(hud_hp, (20, 45))
        screen.blit(hud_stm, (20, 70))
        screen.blit(hud_herbs, (20, 95))
        screen.blit(hud_garra, (20, 120))
        hud_pause = font.render("ESC / P  pausar", True, COLOR_TEXT)
        screen.blit(hud_pause, (SCREEN_WIDTH - hud_pause.get_width() - 20, 20))


class PauseState(GameState):
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
    """Encerramento e Gancho para a Fase 2"""
    def handle_events(self, game, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            game.change_state(MenuState())

    def draw(self, game, screen):
        screen.fill((10, 20, 35))
        f_title = pygame.font.SysFont("arial", 32, bold=True)
        f_txt = pygame.font.SysFont("arial", 18)

        t1 = f_title.render("MISSÃO CONCLUÍDA: O Chamado da Floresta", True, COLOR_GOLD)
        screen.blit(t1, (SCREEN_WIDTH // 2 - t1.get_width() // 2, 100))

        lines = [
            "O espírito do Mapinguari foi purificado e a barreira da Caverna caiu.",
            "Dentro da Caverna Encantada, o Antigo Pajé revela:",
            "'Você venceu apenas a primeira prova, Yáguar. O Coração foi levado além deste mundo.'",
            "",
            "RECOMPENSAS DA FASE 1:",
            "- Amuleto Ancestral do Pajé",
            "- Habilidade 'Garra Espiritual' Desbloqueada",
            "",
            "Pressione [ R ] para retornar ao Menu Principal"
        ]

        y = 200
        for line in lines:
            t = f_txt.render(line, True, COLOR_TEXT)
            screen.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, y))
            y += 35

class GameOverState(GameState):
    def handle_events(self, game, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            game.change_state(MenuState())

    def draw(self, game, screen):
        screen.fill((40, 10, 10))
        f = pygame.font.SysFont("arial", 36, bold=True)
        f_sub = pygame.font.SysFont("arial", 20)

        t = f.render("A CORRUPÇÃO DOMINOU A FLORESTA!", True, COLOR_RED)
        sub = f_sub.render("Pressione [ R ] para Renascer e Tentar Novamente", True, COLOR_TEXT)
        
        screen.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, 300))
        screen.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, 380))

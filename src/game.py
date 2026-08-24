import random

import pygame
from src.config import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TOTAL_HERBS_TO_COLLECT, GROUND_Y
from src.entities import YaguarPlayer, SpectralJaguar, MapinguariBoss, HerbItem
from src.game_states import MenuState
from src.parallax import ParallaxBackground


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("YÁGUAR — Fase 1: O Chamado da Floresta")
        self.clock = pygame.time.Clock()
        self.running = True
        self.parallax = ParallaxBackground()

        self.state = MenuState()
        self.reset_level()

    def reset_level(self):
        self.zone_stage = 0  # 0: onças, 2: Mapinguari
        self.herbs_collected = 0
        self.jaguars_defeated = 0

        self.all_sprites = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.attack_hitboxes = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        self.herbs = pygame.sprite.Group()

        # Instanciar Jogador no chão da aldeia
        self.player = YaguarPlayer(150, GROUND_Y)
        self.all_sprites.add(self.player)

        self.spawn_spectral_jaguar()

        herb_spots = ((220, GROUND_Y), (510, GROUND_Y), (820, GROUND_Y))
        for x, y in herb_spots[:TOTAL_HERBS_TO_COLLECT]:
            h = HerbItem(x, y)
            self.herbs.add(h)

    def spawn_spectral_jaguar(self) -> None:
        jaguar = SpectralJaguar(SCREEN_WIDTH - 200, GROUND_Y)
        self.enemies.add(jaguar)
        self.all_sprites.add(jaguar)

    def spawn_mapinguari(self):
        boss = MapinguariBoss(SCREEN_WIDTH - 220, GROUND_Y)
        self.enemies.add(boss)
        self.all_sprites.add(boss)

    def change_state(self, new_state):
        self.state = new_state

    def run(self):
        while self.running:
            self.clock.tick(FPS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                self.state.handle_events(self, event)

            self.state.update(self)
            self.state.draw(self, self.screen)

            pygame.display.flip()

        pygame.quit()

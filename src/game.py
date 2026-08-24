"""Núcleo do jogo: janela, spawn da fase e loop principal.

A classe Game guarda os grupos de sprites e troca de estados
(menu, intro, partida, pausa, vitória, derrota) sem conhecer a lógica
de cada tela — isso fica em game_states.py.
"""

import random

import pygame
from src import audio
from src.config import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TOTAL_HERBS_TO_COLLECT, GROUND_Y
from src.entities import YaguarPlayer, SpectralJaguar, MapinguariBoss, HerbItem
from src.fx import CombatFX
from src.game_states import MenuState
from src.parallax import ParallaxBackground


class Game:
    """Instância única da sessão: display, relógio, mundo e estado atual."""

    def __init__(self):
        audio.init()
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("YÁGUAR — Fase 1: O Chamado da Floresta")
        self.clock = pygame.time.Clock()
        self.running = True
        self.parallax = ParallaxBackground()
        self.fx = CombatFX()

        # Começa no menu ritual; o nível já é montado para a primeira partida.
        self.state = MenuState()
        self.reset_level()

    def reset_level(self):
        """Recria jogador, onça inicial e ervas — usado na intro e ao recomeçar."""
        self.zone_stage = 0  # 0: onças, 2: Mapinguari
        self.herbs_collected = 0
        self.jaguars_defeated = 0

        self.all_sprites = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.attack_hitboxes = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        self.herbs = pygame.sprite.Group()
        self.fx.clear()

        self.player = YaguarPlayer(150, GROUND_Y)
        self.all_sprites.add(self.player)
        self.parallax.use_scene(0)

        self.spawn_spectral_jaguar(roar=False)

        herb_spots = ((220, GROUND_Y), (510, GROUND_Y), (820, GROUND_Y))
        for x, y in herb_spots[:TOTAL_HERBS_TO_COLLECT]:
            h = HerbItem(x, y)
            self.herbs.add(h)

    def spawn_spectral_jaguar(self, roar: bool = True) -> None:
        """Coloca a próxima onça espectral à direita da tela."""
        jaguar = SpectralJaguar(SCREEN_WIDTH - 200, GROUND_Y)
        self.enemies.add(jaguar)
        self.all_sprites.add(jaguar)
        if roar:
            audio.play_onca_roar()

    def spawn_mapinguari(self):
        """Troca o cenário, instancia o chefe e inicia o tema da batalha."""
        self.parallax.use_scene(1)
        boss = MapinguariBoss(SCREEN_WIDTH - 220, GROUND_Y)
        self.enemies.add(boss)
        self.all_sprites.add(boss)
        audio.play_mapinguari()

    def change_state(self, new_state):
        """Substitui a tela ativa (menu, partida, pausa, etc.)."""
        self.state = new_state

    def run(self):
        """Loop clássico: eventos → update (ou hitstop) → draw → flip."""
        while self.running:
            self.clock.tick(FPS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                self.state.handle_events(self, event)

            # Hitstop congela a lógica por alguns frames no impacto, mas o draw segue.
            if getattr(self, "fx", None) and self.fx.hitstop > 0:
                self.fx.hitstop -= 1
            else:
                self.state.update(self)
            self.state.draw(self, self.screen)

            pygame.display.flip()

        pygame.quit()

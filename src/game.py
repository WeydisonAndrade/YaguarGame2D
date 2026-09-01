"""Núcleo do jogo: janela, spawn da fase e loop principal.

A classe Game guarda os grupos de sprites e troca de estados
(menu, intro, partida, pausa, vitória, derrota) sem conhecer a lógica
de cada tela — isso fica em game_states.py.
"""

import random

import pygame
from src import audio
from src.config import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    FPS,
    TOTAL_HERBS_TO_COLLECT,
    FOREST_CROSSING_PLATFORMS,
    FOREST_WORLD_WIDTH,
    GROUND_Y,
    ONCA_WAVE_KINDS,
    PLATFORMS,
)
from src.entities import (
    YaguarPlayer,
    SpectralJaguar,
    MapinguariBoss,
    HerbItem,
    set_physics_world,
)
from src.fx import CombatFX
from src.game_states import MenuState
from src.parallax import ParallaxBackground


class Game:
    """Instância única da sessão: display, relógio, mundo e estado atual."""

    def __init__(self):
        audio.init()
        pygame.init()
        try:
            pygame.joystick.init()
        except pygame.error:
            pass
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("YÁGUAR — Fase 1: O Chamado da Floresta")
        self.clock = pygame.time.Clock()
        self.running = True
        self.parallax = ParallaxBackground()
        self.fx = CombatFX()
        self.debug_draw = False
        self.dt = 1.0 / FPS
        self.cam_look_y = 0.0

        self.state = MenuState()
        self.reset_level()

    def reset_level(self):
        """Recria jogador, onça inicial e ervas — usado na intro e ao recomeçar."""
        set_physics_world(PLATFORMS, SCREEN_WIDTH, allow_pits=False)
        self.zone_stage = 0
        self.camera_x = 0
        self.herbs_collected = 0
        self.herbs_held = 0
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
        """Coloca a próxima onça da onda (normal, pantera ou espectral) à direita."""
        idx = min(self.jaguars_defeated, len(ONCA_WAVE_KINDS) - 1)
        kind = ONCA_WAVE_KINDS[idx]
        jaguar = SpectralJaguar(SCREEN_WIDTH - 200, GROUND_Y, kind=kind)
        self.enemies.add(jaguar)
        self.all_sprites.add(jaguar)
        if roar:
            audio.play_onca_roar()

    def begin_forest_crossing(self) -> None:
        """Abre o caminho à direita: a clareira continua a mesma floresta."""
        if self.zone_stage == 1:
            return
        self.zone_stage = 1
        set_physics_world(FOREST_CROSSING_PLATFORMS, FOREST_WORLD_WIDTH, allow_pits=True)
        self.parallax.use_crossing()
        self.player.checkpoint = (int(self.player.rect.centerx), GROUND_Y)
        self.player.safe_feet = (int(self.player.rect.centerx), GROUND_Y)

    def spawn_mapinguari(self):
        """Troca o cenário, instancia o chefe e inicia o tema da batalha."""
        set_physics_world(PLATFORMS, SCREEN_WIDTH, allow_pits=False)
        self.camera_x = 0
        self.zone_stage = 2
        self.player.rect.midbottom = (180, GROUND_Y)
        self.player.vel_y = 0
        self.player.on_ground = True
        self.player.air_state = "grounded"
        self.parallax.use_boss_arena()
        boss = MapinguariBoss(SCREEN_WIDTH - 220, GROUND_Y)
        self.enemies.add(boss)
        self.all_sprites.add(boss)
        audio.play_mapinguari()

    def change_state(self, new_state):
        self.state = new_state

    def run(self):
        while self.running:
            raw_ms = self.clock.tick(FPS)
            self.dt = min(raw_ms / 1000.0, 0.05) if raw_ms else (1.0 / FPS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                self.state.handle_events(self, event)

            if getattr(self, "fx", None) and self.fx.hitstop > 0:
                self.fx.hitstop -= 1
            else:
                self.state.update(self)
            self.state.draw(self, self.screen)

            pygame.display.flip()

        pygame.quit()

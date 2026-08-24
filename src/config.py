"""Constantes globais da Fase 1: janela, paleta, física e metas de missão."""

# ---------------------------------------------------------------------------
# Janela
# ---------------------------------------------------------------------------
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 600
FPS = 60

# ---------------------------------------------------------------------------
# Cores gerais (HUD antigo, textos e fundos de fallback)
# ---------------------------------------------------------------------------
COLOR_BG_VILLAGE = (34, 112, 34)      # Verde aldeia / floresta
COLOR_BG_CORRUPT = (20, 30, 25)       # Floresta corrompida
COLOR_TEXT = (245, 245, 220)
COLOR_GOLD = (255, 215, 0)
COLOR_RED = (200, 30, 30)
COLOR_PURPLE = (128, 0, 128)
COLOR_BLUE = (0, 191, 255)

# Paleta ritual do menu e das placas de sinopse (ouro velho, musgo, pergaminho)
COLOR_GOLD_LEAF = (214, 172, 78)
COLOR_GOLD_BRIGHT = (242, 214, 132)
COLOR_GOLD_SHADOW = (118, 76, 28)
COLOR_PARCHMENT = (232, 218, 188)
COLOR_INK = (22, 16, 12)
COLOR_BARK = (46, 30, 18)
COLOR_MOSS = (58, 86, 52)
COLOR_SCARLET = (156, 38, 34)

# ---------------------------------------------------------------------------
# Metas da Fase 1
# ---------------------------------------------------------------------------
TOTAL_HERBS_TO_COLLECT = 3
VICTORY_PROGRESS_MAX = 3  # 1: aldeia, 2: onça, 3: Mapinguari

# ---------------------------------------------------------------------------
# Física e combate (side-scroller 2D)
# ---------------------------------------------------------------------------
GRAVITY = 0.78
JUMP_VELOCITY = -15.5
PLAYER_WALK_SPEED = 4.4
PLAYER_RUN_SPEED = 7.2
PLAYER_ATTACK_FRAMES = 18          # Duração do golpe da lança, em frames
PLAYER_INVULN_FRAMES = 26          # I-frames após levar dano sem bloquear
BLOCK_DAMAGE_FACTOR = 0.22         # Fração de dano que passa no bloqueio
ATTACK_ACTIVE_START = 13           # Janela em que a hitbox da lança existe
ATTACK_ACTIVE_END = 6
HITSTUN_FRAMES = 16
KNOCKBACK = 22
GROUND_Y = 478                     # Linha do chão na pintura da floresta

# Onça espectral: escala visual, onda de 3 e galope
ONCA_SCALE = 0.78
ONCA_WAVE_TOTAL = 3
ONCA_WALK_SPEED = 3.4
ONCA_RUN_SPEED = 7.6
ONCA_RUN_DISTANCE = 150            # Distância a partir da qual ela galopa

# Plataforma única: laje de pedra que cobre a largura da tela
PLATFORMS = (
    (0, GROUND_Y, SCREEN_WIDTH, 170),
)

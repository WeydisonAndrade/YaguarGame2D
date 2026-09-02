"""Constantes globais da Fase 1: janela, paleta, física e metas de missão."""

import pygame as _pg

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
SPEAR_ROAR_EVERY = 10              # Rugido do Yáguar a cada N golpes de lança
PLAYER_INVULN_FRAMES = 26          # I-frames após levar dano sem bloquear
BLOCK_DAMAGE_FACTOR = 0.22         # Fração de dano que passa no bloqueio
BLOCK_RECOVERY_FRAMES = 12         # I-frames curtos no bloqueio (chip, não 60 hits/s)
ATTACK_ACTIVE_START = 13           # Janela em que a hitbox da lança existe
ATTACK_ACTIVE_END = 6
HITSTUN_FRAMES = 16
KNOCKBACK = 22
GROUND_Y = 478                     # Linha do chão na pintura da floresta

# ---------------------------------------------------------------------------
# Controles (um único lugar — não hardcode teclas nos estados)
# ---------------------------------------------------------------------------
KEY_BOW_AIM = _pg.K_q              # Segurar: sacar flecha, nock e mirar
KEY_ATTACK = _pg.K_j               # Lança, ou disparo com o arco sacado
MOUSE_ATTACK = 1                   # event.button esquerdo
MOUSE_ATTACK_HELD = 0              # índice em mouse.get_pressed()
MOUSE_HEAVY = 3                    # event.button direito
MOUSE_HEAVY_HELD = 2               # índice em mouse.get_pressed()

# ---------------------------------------------------------------------------
# Arco e flecha (tempos em segundos; a física da flecha usa dt)
# ---------------------------------------------------------------------------
BOW_AIM_SPEED = 0.52               # Fração da caminhada durante a mira
BOW_AIM_PITCH_UP = 1.22            # ~70° acima da horizontal
BOW_AIM_PITCH_DOWN = 0.92          # ~53° abaixo
BOW_AIM_DEADZONE = 14              # px: evita tremer com o cursor na mão
BOW_NOCK = 0.42                    # Sacar da aljava e encaixar a flecha
BOW_MAX_CHARGE = 0.55
BOW_RECOVER = 0.20
BOW_MIN_SPEED = 1080.0             # px/s — disparo forte
BOW_MAX_SPEED = 1580.0
BOW_GRAVITY = 0.0                  # Linear, como na pose de tiro
BOW_DAMAGE_MIN = 12
BOW_DAMAGE_MAX = 24
BOW_WEAK_MULT = 1.35
BOW_LIFETIME = 2.6
BOW_STUCK_TIME = 1.15
BOW_LOOKAHEAD = 150

# Poses de arco: RGB do corpo = trigger01.png. Só recorte do fundo preto.
YAGUAR_COLOR_PROFILE = {
    "ref_poses": ("trigger01",),
    "sharp_ref": "trigger01",
    "target_height": 168,
    "preserve_rgb": True,
}
BOW_GRADE_POSES = ("bow", "bow_quiver", "bow_nock")
KEY_COLOR_COMPARE = _pg.K_F4       # Debug: original vs grade do arco

# Onça espectral: escala visual, onda de 3 e galope
ONCA_SCALE = 0.78
ONCA_WAVE_TOTAL = 3
ONCA_WAVE_KINDS = ("normal", "pantera", "espectral")
ONCA_WALK_SPEED = 3.4
ONCA_RUN_SPEED = 7.6
ONCA_RUN_DISTANCE = 150            # Distância a partir da qual ela galopa

# Plataforma única: laje de pedra que cobre a largura da tela (arena das onças)
PLATFORMS = (
    (0, GROUND_Y, SCREEN_WIDTH, 170),
)

# ---------------------------------------------------------------------------
# Clareira das fendas — continua a arena à direita (mesmo chão, câmera segue).
# Colisão na grama da pintura, alinhada a GROUND_Y. Medida na arte 1024×600:
#   A 0–257 | fenda 147 | B 404–523 | fenda 186 | C 709–1024
# Física: andar ≈ 156 px, correr ≈ 273 px. 1ª fenda dá para pular a pé;
# a 2ª exige corrida. Pilar estreito como na arte (~119 px).
# A pintura sobrepõe a última árvore da arena (≤ largura de A) para a
# costura não ser dois quadros colados.
# ---------------------------------------------------------------------------
TRAIL_SEAM_OVERLAP = 180
TRAIL_ORIGIN_X = SCREEN_WIDTH
TRAIL_DRAW_X = TRAIL_ORIGIN_X - TRAIL_SEAM_OVERLAP
TRAIL_ART_GROUND_Y = 264
TRAIL_DRAW_Y = GROUND_Y - TRAIL_ART_GROUND_Y
TRAIL_GROUND_Y = GROUND_Y
TRAIL_A_X = TRAIL_DRAW_X + 0
TRAIL_PLATFORM_A_WIDTH = 257
TRAIL_B_X = TRAIL_DRAW_X + 404
TRAIL_PLATFORM_B_WIDTH = 119
TRAIL_C_X = TRAIL_DRAW_X + 709
TRAIL_PLATFORM_C_WIDTH = 315
TRAIL_GAP_1_WIDTH = TRAIL_B_X - (TRAIL_A_X + TRAIL_PLATFORM_A_WIDTH)
TRAIL_GAP_2_WIDTH = TRAIL_C_X - (TRAIL_B_X + TRAIL_PLATFORM_B_WIDTH)
TRAIL_LEDGE_HEIGHT = 170
TRAIL_MID_LEDGE_HEIGHT = 80
TRAIL_FALL_Y = TRAIL_GROUND_Y + 96
TRAIL_FALL_DAMAGE = 22
TRAIL_SPAWN_X = TRAIL_A_X + 150
TRAIL_WORLD_WIDTH = TRAIL_DRAW_X + SCREEN_WIDTH
TRAIL_CHECKPOINT_X = TRAIL_A_X + 190
TRAIL_EXIT_X = TRAIL_C_X + 70
TRAIL_PLATFORMS = (
    (TRAIL_A_X, TRAIL_GROUND_Y, TRAIL_PLATFORM_A_WIDTH, TRAIL_LEDGE_HEIGHT),
    (TRAIL_B_X, TRAIL_GROUND_Y, TRAIL_PLATFORM_B_WIDTH, TRAIL_MID_LEDGE_HEIGHT),
    (TRAIL_C_X, TRAIL_GROUND_Y, TRAIL_PLATFORM_C_WIDTH, TRAIL_LEDGE_HEIGHT),
)

# ---------------------------------------------------------------------------
# Areia movediça — continua a clareira à direita (mesmo chão, mesmas fendas).
# Arte 1024×600: A 0–241 | fenda 71 | B 312–502 | fenda 58 | C 560–1024
# O corpo do Yáguar (~92 px, pés ~68 px) é mais largo que essas fendas pintadas:
# a colisão recua os lábios (~20 px) para ele cair no vão, não andar no ar.
# Os dois vãos ainda cabem no pulo a pé (~156 px).
# Sobreposição na última árvore da clareira (≤ largura de A).
# ---------------------------------------------------------------------------
SAND_SEAM_OVERLAP = 200
SAND_ORIGIN_X = TRAIL_WORLD_WIDTH
SAND_DRAW_X = SAND_ORIGIN_X - SAND_SEAM_OVERLAP
SAND_ART_GROUND_Y = 252
SAND_A_X = SAND_DRAW_X + 0
SAND_PLATFORM_A_WIDTH = 221
SAND_B_X = SAND_DRAW_X + 332
SAND_PLATFORM_B_WIDTH = 150
SAND_C_X = SAND_DRAW_X + 580
SAND_PLATFORM_C_WIDTH = SCREEN_WIDTH - 580
SAND_GAP_1_WIDTH = SAND_B_X - (SAND_A_X + SAND_PLATFORM_A_WIDTH)
SAND_GAP_2_WIDTH = SAND_C_X - (SAND_B_X + SAND_PLATFORM_B_WIDTH)
SAND_PLATFORMS = (
    (SAND_A_X, TRAIL_GROUND_Y, SAND_PLATFORM_A_WIDTH, TRAIL_LEDGE_HEIGHT),
    (SAND_B_X, TRAIL_GROUND_Y, SAND_PLATFORM_B_WIDTH, TRAIL_MID_LEDGE_HEIGHT),
    (SAND_C_X, TRAIL_GROUND_Y, SAND_PLATFORM_C_WIDTH, TRAIL_LEDGE_HEIGHT),
)
SAND_WORLD_WIDTH = SAND_DRAW_X + SCREEN_WIDTH

# ---------------------------------------------------------------------------
# Floresta após a areia — chão contínuo, poças pintadas no caminho.
# Fonte 1536×1024: superfície das poças ~706, para os pés caírem na areia.
# A pintura começa na última árvore da clareira: sobrepõe 320 px para o
# tronco não aparecer duas vezes na costura.
# ---------------------------------------------------------------------------
CONTINUE_SEAM_OVERLAP = 320
CONTINUE_ORIGIN_X = SAND_WORLD_WIDTH
CONTINUE_DRAW_X = CONTINUE_ORIGIN_X - CONTINUE_SEAM_OVERLAP
CONTINUE_SRC_GROUND_Y = 706
CONTINUE_A_X = CONTINUE_ORIGIN_X + 0
CONTINUE_WORLD_WIDTH = CONTINUE_DRAW_X + SCREEN_WIDTH
CONTINUE_PLATFORM_WIDTH = CONTINUE_WORLD_WIDTH - CONTINUE_ORIGIN_X
CONTINUE_PLATFORMS = (
    (CONTINUE_A_X, TRAIL_GROUND_Y, CONTINUE_PLATFORM_WIDTH, TRAIL_LEDGE_HEIGHT),
)

# Poças pintadas na arte 1024×600 (após o overlap da árvore). O piso sobe até
# os pés e só então engole — não é fenda: a laje continua sólida.
CONTINUE_SAND_POOLS = (
    (CONTINUE_DRAW_X + 338, 178),
    (CONTINUE_DRAW_X + 538, 218),
    (CONTINUE_DRAW_X + 786, 228),
)
QUICKSAND_RECESS = 16
QUICKSAND_RISE_SPEED = 52.0
QUICKSAND_SINK_SPEED = 26.0
QUICKSAND_SWALLOW_DEPTH = 78
QUICKSAND_SLOW = 0.34

# Galho da árvore à direita (quadro 1024 da continuação). Só neste trecho a
# flecha leva corda, para o Yáguar se balançar sobre as poças.
ROPE_BRANCH_X = CONTINUE_DRAW_X + 500
ROPE_BRANCH_Y = 108
ROPE_BRANCH_W = 360
ROPE_BRANCH_H = 86
ROPE_HANG_CLEARANCE = 96
ROPE_REEL_TIME = 0.34
ROPE_MAX_ANGLE = 1.34
ROPE_DAMPING = 0.993
ROPE_OMEGA_MAX = 0.10
ROPE_PUMP = 0.0022


FOREST_WORLD_WIDTH = CONTINUE_WORLD_WIDTH
MAPINGUARI_GATE_X = FOREST_WORLD_WIDTH - 72
FOREST_CROSSING_PLATFORMS = PLATFORMS + TRAIL_PLATFORMS + SAND_PLATFORMS + CONTINUE_PLATFORMS

# Câmera da travessia: Yáguar fica ~40% da tela ao avançar, para ver o caminho.
CAMERA_ANCHOR_FWD = 0.40
CAMERA_ANCHOR_BACK = 0.58
CAMERA_DEADZONE = 0.055
CAMERA_LERP = 0.14
CROSSING_BLEND_PX = 220
CROSSING_OVERHANG_PX = 200

# ---------------------------------------------------------------------------
# Cinemática da introdução (após o menu, antes da partida)
# ---------------------------------------------------------------------------
CINEMATIC_HOLD_FRAMES = 170        # Tempo de cada quadro visível (~2,8 s)
CINEMATIC_FADE_FRAMES = 36         # Crossfade entre quadros
CINEMATIC_ZOOM = 1.12              # Ken Burns: cobertura extra para o zoom
CINEMATIC_FILES = (
    "img01.png",
    "img02.png",
    "img03.png",
    "img04.png",
    "img05.png",
    "img06.png",
)
CINEMATIC_CAPTIONS = (
    "Há milhares de anos, a tribo recebeu o Coração da Floresta.",
    "Na noite da Lua Escarlate, o céu se partiu.",
    "Uma entidade cósmica invadiu o templo.",
    "O antigo Pajé foi derrotado. O artefato foi roubado.",
    "A corrupção se espalha. Os rios secam. Os animais enlouquecem.",
    "Yáguar, o maior guerreiro da tribo, jura salvar a Amazônia.",
)
CINEMATIC_PANS = (
    (0.35, -0.25),
    (-0.30, 0.20),
    (0.40, 0.10),
    (-0.20, -0.35),
    (0.15, 0.30),
    (0.00, -0.40),
)

# ---------------------------------------------------------------------------
# Cinemática do Mapinguari (após a 3ª onça, antes do combate com o chefe)
# ---------------------------------------------------------------------------
BOSS_CINEMATIC_FOLDER = "battleBoss"
BOSS_CINEMATIC_FILES = (
    "imgBattle01.png",
    "imgBattle02.png",
    "imgBattle03.png",
    "imgBattle04.png",
    "imgBattle05.png",
    "imgBattle06.png",
    "imgBaattle07.png",
)
BOSS_CINEMATIC_CAPTIONS = (
    "O Caminho da Montanha Sagrada se abre.",
    "Yáguar avança à arena do Guardião.",
    "A caverna chama. O templo espera.",
    "O Mapinguari salta das trevas.",
    "Ninguém passa sem provar seu valor.",
    "«Eu sou o Mapinguari, o Guardião deste portal.»",
    "Se queres a verdade... terás que me enfrentar.",
)
BOSS_CINEMATIC_PANS = (
    (0.40, -0.20),
    (-0.25, 0.15),
    (0.10, -0.35),
    (0.00, -0.45),
    (-0.15, 0.25),
    (0.30, 0.10),
    (0.00, -0.30),
)
BOSS_CINEMATIC_KICKER = "FASE I  ·  O MAPINGUARI"

# ---------------------------------------------------------------------------
# Cinemática da areia movediça (antes das poças, na travessia)
# ---------------------------------------------------------------------------
SAND_CINEMATIC_GATE_X = CONTINUE_DRAW_X
SAND_CINEMATIC_FOLDER = "cinematic_sand"
SAND_CINEMATIC_FILES = (
    "img01.png",
    "img02.png",
    "img03.png",
    "img04.png",
    "img05.png",
    "img06.png",
)
SAND_CINEMATIC_CAPTIONS = (
    "Yáguar chega à clareira. O chão dourado esconde a morte.",
    "Areia movediça. Não há passagem segura.",
    "Uma pantera negra bloqueia o caminho.",
    "A fera ataca. Yáguar recua.",
    "A areia prende as patas. A caçadora é a presa.",
    "A floresta engole a pantera. Yáguar observa, assustado.",
)
SAND_CINEMATIC_PANS = (
    (0.35, -0.20),
    (-0.25, 0.15),
    (0.30, 0.10),
    (0.00, -0.25),
    (-0.15, 0.20),
    (0.00, -0.30),
)
SAND_CINEMATIC_KICKER = "FASE I  ·  A AREIA MOVEDIÇA"

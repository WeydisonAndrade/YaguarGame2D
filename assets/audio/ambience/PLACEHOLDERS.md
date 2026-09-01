# PLACEHOLDERS DE ÁUDIO

Estes arquivos **ainda não existem**. Não foram criados WAV/MP3/OGG vazios.

O jogo sobe sem eles: o bus de ambience simplesmente não toca o clipe.

Quando produzir, grave com os nomes abaixo (OGG 44.1 kHz, loop seamless, sem clipping).

## ambience (loops)

- `assets/audio/ambience/sfx_forest_birds_loop.ogg`
- `assets/audio/ambience/sfx_forest_leaves_loop.ogg`
- `assets/audio/ambience/sfx_forest_water_loop.ogg`
- `assets/audio/ambience/sfx_forest_insects_loop.ogg`
- `assets/audio/ambience/sfx_vine_wind_loop.ogg`
- `assets/audio/ambience/sfx_mountain_wind_loop.ogg`
- `assets/audio/ambience/sfx_mountain_echo_loop.ogg`
- `assets/audio/ambience/sfx_rock_ambient_loop.ogg`
- `assets/audio/ambience/sfx_distant_rumble_loop.ogg`
- `assets/audio/ambience/sfx_boss_rumble_loop.ogg`
- `assets/audio/ambience/sfx_boss_breath_loop.ogg`
- `assets/audio/ambience/sfx_cave_ambience_loop.ogg`
- `assets/audio/ambience/sfx_low_wind_loop.ogg`

## sfx (one-shots)

- `assets/audio/sfx/sfx_vine_creak_01.ogg`
- `assets/audio/sfx/sfx_rope_tension_01.ogg`
- `assets/audio/sfx/sfx_leaf_rustle_01.ogg`
- `assets/audio/sfx/sfx_stone_debris_01.ogg`

Detalhe de loudness, duração e mix: `ASSET_SPECIFICATIONS.md`.
Código: `src/audio.py` (`tick_world`, canais reservados 0–7).

# Especificações de assets — Yáguar: O Guardião da Floresta

Padrão de resolução determinado pelo runtime:

| Grandeza | Valor |
|---|---|
| Viewport | **1024 × 600** |
| Escala de mundo | 1 px = 1 unidade |
| Altura do Yáguar | **168 px** (crouch 140 px) |
| Âncora do personagem | midbottom |
| Hurtbox | 54 × 110, independente do sprite |
| GROUND_Y | 478 |
| Largura do mundo contínuo | 4656 px |

Backgrounds horizontais longos: múltiplos da viewport (1024, 2048, 3072).
Não esticar concept art. Não usar JPG em elementos com alpha.

Direção de luz: difusa da esquerda-frente, névoa fria, pintura digital oleosa.
Paleta: floresta verde úmido → fendas verde+luz → cipós verde profundo → montanha verde-escuro+cinza → caverna cinza/verde + luz espiritual → Mapinguari escuridão + corrupção.

Não misturar cartoon, pixel art, pintura realista e render 3D na mesma camada.

---

## Já produzido neste pipeline

Camadas derivadas de `forest2` / `forest_far` / `forest_mid` / `forest_fg`, recortes com chroma magenta, midground 2048×600 e tiles de cipó. Ver `assets/manifest.json`.

---

## char_yaguar_grab — `assets/player/grab.png`

- Resolução: altura **168 px**, largura livre (autocrop). Formato PNG RGBA.
- Alpha: sim. Sem halo branco.
- Função: pose no instante em que as mãos fecham o cipó (~8–12 frames).
- Camada: character.
- Direção: mesmo modelo 3D/pintura dos sprites atuais (pele bronze, cocar, lança/arco).
- Pose: braços acima/frente, mãos no cipó, tronco tensionado, pernas prontas para o balanço.
- Bordas: recorte justo. Sem chão.
- Escala: pés no mesmo plano dos outros sprites. Pivot **midbottom**.
- Hand anchor (offset da hurtbox): `(facing * 8, -42)`.
- Não alterar collider. Se o sprite for mais alto, compensar só com pivot/offset.
- Fallback atual: `jump.png`.

## char_yaguar_swing_left / _center / _right

- Resolução: altura 168 px, PNG RGBA.
- Função: corpo acompanha θ do pêndulo. Left = θ < −0.28; center = |θ| pequeno; right = θ > 0.28.
- Pose: tronco inclinado na direção do balanço, pernas no momentum, mãos ainda no cipó.
- Pivot midbottom. Hand anchors em `entities.py`.
- Ideal: 3 frames. Aceitável: 1 frame por lado + center.
- Fallback: `jump.png`.

## char_yaguar_release

- Resolução: altura 168 px, PNG RGBA.
- Função: 8 frames após soltar, antes de jump/fall.
- Pose: braços liberando, corpo projetado, pernas no momentum.
- Pivot midbottom. Hand anchor `(facing * 20, -18)`.
- Fallback: `jump.png`.

---

## Áudio a produzir (não gerar arquivos binários falsos)

Loops discretos, sem clipping, pico < −1 dBFS, loudness alvo **−18 LUFS** (ambience) / **−14 LUFS** (one-shots). Preferir **OGG Vorbis 44.1 kHz estéreo**. WAV 16-bit também entra no loader se o nome for o mesmo com extensão `.ogg` substituída — o código procura `.ogg`.

| ID | Path | Duração | Notas |
|---|---|---|---|
| sfx_forest_birds_loop | audio/ambience/sfx_forest_birds_loop.ogg | 20–40 s | Loop seamless, baixo na mix. |
| sfx_forest_leaves_loop | audio/ambience/sfx_forest_leaves_loop.ogg | 15–30 s | Folhas, vento leve. |
| sfx_forest_water_loop | audio/ambience/sfx_forest_water_loop.ogg | 20–40 s | Rio distante (fendas). |
| sfx_forest_insects_loop | audio/ambience/sfx_forest_insects_loop.ogg | 15–30 s | Insetos, não estridentes. |
| sfx_vine_wind_loop | audio/ambience/sfx_vine_wind_loop.ogg | 15–30 s | Caverna úmida. |
| sfx_vine_creak_01 | audio/sfx/sfx_vine_creak_01.ogg | 0.3–0.8 s | One-shot. Código: cooldown 420 ms. |
| sfx_rope_tension_01 | audio/sfx/sfx_rope_tension_01.ogg | 0.4–1.0 s | Balanço forte. |
| sfx_leaf_rustle_01 | audio/sfx/sfx_leaf_rustle_01.ogg | 0.2–0.5 s | Movimento fraco. |
| sfx_mountain_wind_loop | audio/ambience/sfx_mountain_wind_loop.ogg | 20–40 s | Vazio, grave. |
| sfx_mountain_echo_loop | audio/ambience/sfx_mountain_echo_loop.ogg | 15–30 s | Eco de pedra. |
| sfx_rock_ambient_loop | audio/ambience/sfx_rock_ambient_loop.ogg | 20–40 s | Pedras, goteira rara. |
| sfx_distant_rumble_loop | audio/ambience/sfx_distant_rumble_loop.ogg | 20–40 s | Muito baixo. |
| sfx_boss_rumble_loop | audio/ambience/sfx_boss_rumble_loop.ogg | 15–30 s | Tensão, abaixo da música. |
| sfx_boss_breath_loop | audio/ambience/sfx_boss_breath_loop.ogg | 10–20 s | Respiração enorme, distante. |
| sfx_cave_ambience_loop | audio/ambience/sfx_cave_ambience_loop.ogg | 20–40 s | Interior da caverna. |
| sfx_stone_debris_01 | audio/sfx/sfx_stone_debris_01.ogg | 0.5–1.2 s | One-shot esparso na arena. |
| sfx_low_wind_loop | audio/ambience/sfx_low_wind_loop.ogg | 20–40 s | Vento grave. |

Arquitetura: `mixer.music` permanece na trilha. Ambience usa `Sound` nos canais 0–7, volume interpolado por região (não há crossfade de duas músicas no mesmo canal).

---

## Recriação profissional (se um artista substituir os derivados)

### bg_mountain_far_01

- 2048 × 600, PNG, alpha na base.
- Montanhas/floresta distante, névoa, baixo contraste. Sem gameplay.
- Parallax factor 0.10. Pivot canto superior esquerdo.

### bg_mountain_mid_01

- ~1300 × 600, PNG RGBA.
- Árvores antigas, rochas, raízes, sem chão inseparável.
- Parallax 0.28.

### env_cave_entrance_01

- Altura 600, largura ~900–1100, PNG RGBA.
- Boca monumental, rochas, raízes, musgo, estalactites. Interior = alpha (furo).
- Sem Yáguar/Mapinguari. Overlay em `ARENA_ORIGIN_X`.

### plat_* / fg_*

- PNG RGBA, topo legível, tileable quando possível.
- Colliders independentes em `GROUND_Y`.

### bg_mid_fendas_vines_01

- **2048 × 600** RGB ou RGBA.
- Horizonte coerente: clareira aberta → árvores → raízes → umidade → cipós.
- Sem personagem, HUD ou plataformas inseparáveis.
- Bordas sem objetos cortados. Recorte horizontal permitido.

### vine_segment_* / vine_anchor_*

- PNG RGBA, fundo vazio, espessura ~36 px, orientáveis.
- Pivot centro (segmento) / midbottom (âncora).

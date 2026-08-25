# Yáguar — O Guardião da Floresta

Side-scroller 2D em Pygame. Você controla **Yáguar**, guerreiro da tribo, na **Fase 1: O Chamado da Floresta**.

Na noite da Lua Escarlate, uma entidade cósmica roubou o Coração da Floresta. A corrupção se espalha; o guerreiro responde ao chamado para purificar o caminho até a Caverna Encantada.

Janela: **1024×600** a **60 FPS**.

---

## Como rodar

É preciso executar **de dentro** desta pasta (`yaguar_game`). O jogo carrega sprites, música e efeitos a partir de `assets/`.

### Requisitos

- Python 3.10 ou superior
- [Pygame](https://www.pygame.org/) e [Pillow](https://pillow.readthedocs.io/)

```powershell
pip install pygame pillow
```

### Iniciar o jogo

Entre na pasta que contém o `main.py` (não na pasta do usuário `C:\Users\...`). No Desktop deste projeto:

```powershell
cd $HOME\Desktop\Yaguar_O_Guardiao_da_Floresta\yaguar_game
python main.py
```

Se você clonou o repositório `YaguarGame2D`, a raiz do clone já é essa pasta — basta `cd` até ela e rodar `python main.py`.

O `main.py` gera placeholders em `assets/` se faltarem e abre o menu ritual.

Para enviar o projeto a outra pessoa, zipar **esta pasta inteira** (código + `assets/`). Sem `assets/player`, `assets/onca`, `assets/mapinguari`, `assets/parallax` e `assets/cinematic_animation` o jogo não desenha corretamente.

---

## Sistema do jogo

A sessão é uma máquina de estados. `Game` guarda a janela, o mundo e os grupos de sprites; cada tela (menu, partida, pausa…) trata eventos, lógica e desenho.

```
Menu  →  Cinemática  →  Partida  →  Pausa
                           ↓    ↓
                      Vitória  Derrota  →  Menu (tecla R)
```

| Tela | O que acontece |
|---|---|
| **Menu** | Floresta viva, ritos do guerreiro. `Espaço` ou clique no chamado abre a cinemática. |
| **Cinemática** | Seis pinturas da origem. Clique avança o quadro; `Espaço` ou `ESC` pula para a floresta. |
| **Partida** | Combate: três onças espectrais, depois o Mapinguari. |
| **Pausa** | Congela a luta. `Espaço` / `ESC` / `P` continua; `M` volta ao menu. |
| **Vitória** | O espírito do Mapinguari foi purificado. `R` retorna ao menu. |
| **Derrota** | A vida chegou a zero. `R` tenta de novo pelo menu. |

### Missão da Fase 1

1. Derrotar **3 onças espectrais** (uma de cada vez).
2. A terceira onça **libera a Garra Espiritual**.
3. O cenário muda e surge o **Mapinguari**.
4. Derrotar o chefe conclui a prova.

Três **ervas sagradas** estão no chão. Andar sobre elas (ou `E`) cura **25** de vida, até o máximo de 100.

### Combate

- **Lança** (golpe leve): hitbox só na janela ativa do ataque. A cada 10 golpes, Yáguar **ruge** e encanta a lança por alguns instantes.
- **Garra Espiritual** (golpe pesado): mais alcance e dano; só depois da terceira onça.
- **Defesa**: reduz o dano a 22% e ganha uma recuperação curta (não é invencível; ainda passa chip).
- **I-frames** após hit sem bloqueio. Vida não desce abaixo de zero; HP 0 vai para a derrota, inclusive se o golpe for só a hitbox da onça (sem encostar o corpo).

**Onça espectral** — persegue, galopa de longe e alterna garra e mordida de perto.

**Mapinguari** — combo de dois braços de perto e arremesso de tronco de longe. Abaixo de 200 e 100 de vida fica mais rápido e agressivo.

---

## Controles

| Ação | Teclas / mouse |
|---|---|
| Andar | `A` / `D` ou setas |
| Correr | `Shift` (gasta fôlego) |
| Pular | `W`, `↑` ou `Espaço` |
| Agachar | `S` ou `↓` |
| Ataque com lança | `J` ou clique esquerdo |
| Garra espiritual | Clique direito (após a 3ª onça) |
| Defesa ancestral | `K` ou `Ctrl` |
| Ervas sagradas | `E` (também coleta ao encostar) |
| Pausar | `ESC` ou `P` |

---

## Estrutura

```
yaguar_game/
  main.py              ponto de entrada
  src/
    game.py            janela, spawn, loop
    game_states.py     menu, intro, partida, pausa, vitória, derrota
    entities.py        Yáguar, onça, Mapinguari, erva, tronco
    config.py          constantes da Fase 1
    ui.py              menu ritual, HUD, sinopse, pausa
    audio.py           trilhas e rugidos
    parallax.py        pinturas da floresta
    fx.py              cortes, shake, flash
    player_anim.py     poses do protagonista
    cinematic.py       introdução em seis pinturas
    asset_generator.py placeholders PNG
  assets/              sprites, parallax, cinemática, música, SFX
  tests/               pirâmide de testes (unidade → integração → sistema)
```

---

## Testes

Com Pygame, Pillow e pytest instalados, ainda dentro de `yaguar_game`:

```powershell
pip install pytest
python -m pytest
```

A suíte cobre física, combate, ondas da fase e o fluxo de telas, sem abrir uma janela real (`SDL` dummy).

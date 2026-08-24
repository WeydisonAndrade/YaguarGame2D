"""Ponto de entrada do Yáguar — O Guardião da Floresta.

Execute este arquivo a partir da pasta yaguar_game:
    python main.py
"""

from src.asset_generator import generate_assets
from src.game import Game

if __name__ == "__main__":
    # Garante que os placeholders PNG existam em assets/ antes de abrir a janela.
    generate_assets()

    # Cria a janela, o mixer e o estado inicial (menu) e entra no loop principal.
    yaguar_game = Game()
    yaguar_game.run()

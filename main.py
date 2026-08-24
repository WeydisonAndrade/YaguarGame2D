from src.asset_generator import generate_assets
from src.game import Game

if __name__ == "__main__":
    # 1. Gera ou valida a pasta assets com as imagens do jogo
    generate_assets()

    # 2. Executa a engine do jogo
    yaguar_game = Game()
    yaguar_game.run()

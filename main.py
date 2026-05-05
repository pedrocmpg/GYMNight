"""
main.py - GYMNight
Entry point da aplicação.
"""
import sys
from dotenv import load_dotenv

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from src.ui.theme import DARK_QSS
from src.ui.window import MainWindow


def main():
    # Carrega variáveis de ambiente do arquivo .env
    load_dotenv()
    
    app = QApplication(sys.argv)

    # Escala global 1.5x — fonte base de 20px (era 13px)
    font = QFont("Segoe UI")
    font.setWeight(QFont.Medium)
    font.setWordSpacing(0)
    font.setLetterSpacing(QFont.AbsoluteSpacing, 0)
    app.setFont(font)

    app.setStyleSheet(DARK_QSS)
    MainWindow().show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

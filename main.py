"""
main.py - GYMNight
Entry point da aplicação.
"""
import sys

from PySide6.QtWidgets import QApplication

from ui.theme import DARK_QSS
from ui.window import MainWindow


def main():
    app = QApplication(sys.argv)

    # Escala global 1.5x — fonte base de 20px (era 13px)
    from PySide6.QtGui import QFont, QFontDatabase

    # Garante fallback para emojis coloridos (Segoe UI Emoji no Windows)
    QFontDatabase.addApplicationFont.__doc__  # no-op, só para importar
    font = QFont()
    font.setFamilies(["Inter", "Segoe UI", "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji"])
    font.setPointSize(20)
    font.setWeight(QFont.Medium)
    app.setFont(font)

    app.setStyleSheet(DARK_QSS)
    MainWindow().show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

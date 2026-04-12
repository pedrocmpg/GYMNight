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

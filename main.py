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
    app.setStyleSheet(DARK_QSS)
    MainWindow().show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

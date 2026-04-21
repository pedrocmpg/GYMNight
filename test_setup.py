"""Quick test of the setup wizard"""
import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import Qt
from ui.screens.setup import SetupScreen
from ui.theme import DARK_QSS

app = QApplication(sys.argv)
app.setStyleSheet(DARK_QSS)

# Create a frameless window to hold the setup
win = QMainWindow()
win.setWindowTitle("GYMNight Setup")
win.setWindowFlags(Qt.WindowType.FramelessWindowHint)
win.setAttribute(Qt.WA_TranslucentBackground)
win.resize(600, 700)

setup = SetupScreen()
win.setCentralWidget(setup)
win.show()

sys.exit(app.exec())

"""
Script de teste para a tela de Estatísticas
"""
import sys
from PySide6.QtWidgets import QApplication
from database import DatabaseConnection
from src.ui.screens.statistics import StatisticsTab

def main():
    app = QApplication(sys.argv)
    
    # Conecta ao banco de dados
    db = DatabaseConnection("gymnight.db")
    
    # Cria a tela de estatísticas
    stats_tab = StatisticsTab(db)
    stats_tab.setWindowTitle("GYMNight - Estatísticas")
    stats_tab.resize(1000, 800)
    stats_tab.show()
    
    # Atualiza os dados
    stats_tab.refresh()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

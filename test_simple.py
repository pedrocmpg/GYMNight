#!/usr/bin/env python3
"""
Teste simples para verificar se a aplicação inicia sem erros.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from src.ui.theme import DARK_QSS

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_QSS)
    
    print("✓ QApplication criada")
    print("✓ Stylesheet aplicado")
    
    # Testa import da CardioPage
    from src.ui.screens.cardio_widget import CardioPage
    print("✓ CardioPage importada")
    
    # Cria a página
    page = CardioPage(user_weight_kg=75)
    print("✓ CardioPage instanciada")
    
    page.show()
    print("✓ CardioPage exibida")
    print("\n🎉 Tudo funcionando! Feche a janela para sair.")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

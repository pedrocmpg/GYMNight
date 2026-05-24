#!/usr/bin/env python3
"""
Script de teste para visualizar as melhorias na tela de Cardio Avulso.
Agora mostra a CardioPage como uma aba ao invés de um diálogo popup.
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QStackedWidget
from src.ui.screens.cardio_widget import CardioPage, CardioRow
from src.ui.theme import DARK_QSS, C_GREEN, RADIUS_MD


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Teste - Cardio Avulso como Aba")
        self.setMinimumSize(900, 700)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Stack para simular navegação entre páginas
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        
        # Página principal com botão
        main_page = QWidget()
        main_layout = QVBoxLayout(main_page)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)
        
        btn = QPushButton("🏃 Adicionar Cardio (Abre como Aba)")
        btn.setFixedHeight(60)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {C_GREEN};
                color: #000;
                border: none;
                border-radius: {RADIUS_MD}px;
                font-size: 18px;
                font-weight: 800;
            }}
            QPushButton:hover {{
                background: #b5f542;
            }}
        """)
        btn.clicked.connect(self.open_cardio_page)
        main_layout.addWidget(btn)
        
        # Container para mostrar os cardios adicionados
        self.cardio_container = QVBoxLayout()
        main_layout.addLayout(self.cardio_container)
        main_layout.addStretch()
        
        self.stack.addWidget(main_page)  # index 0
        
        # Página de cardio (será adicionada quando necessário)
        self.cardio_page = None
        
    def open_cardio_page(self):
        """Navega para a página de adicionar cardio."""
        if self.cardio_page is None:
            self.cardio_page = CardioPage(user_weight_kg=75)
            self.cardio_page.cardio_added.connect(self.on_cardio_added)
            self.cardio_page.cancelled.connect(lambda: self.stack.setCurrentIndex(0))
            self.stack.addWidget(self.cardio_page)  # index 1
        
        self.stack.setCurrentIndex(1)
    
    def on_cardio_added(self, data: dict):
        """Chamado quando um cardio é adicionado."""
        # Cria e adiciona o CardioRow
        row = CardioRow(data)
        row.remove_requested.connect(lambda r: r.deleteLater())
        self.cardio_container.addWidget(row)
        print(f"✓ Cardio adicionado: {data}")
        
        # Volta para a página principal
        self.stack.setCurrentIndex(0)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_QSS)
    
    window = TestWindow()
    window.show()
    
    print("=" * 60)
    print("🎉 Teste da CardioPage como Aba")
    print("=" * 60)
    print("1. Clique no botão para abrir a página de cardio")
    print("2. A página abre como uma aba, não como popup!")
    print("3. Preencha os dados e clique em 'Adicionar Cardio'")
    print("4. Você volta automaticamente para a página principal")
    print("5. O cardio aparece na lista")
    print("=" * 60)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Script de diagnóstico para verificar por que a janela não aparece.
"""
import sys
import os

print("=== Diagnóstico GYMNight ===\n")

# 1. Variáveis de ambiente
print("1. Variáveis de ambiente:")
print(f"   DISPLAY: {os.environ.get('DISPLAY', 'NÃO DEFINIDA')}")
print(f"   QT_QPA_PLATFORM: {os.environ.get('QT_QPA_PLATFORM', 'NÃO DEFINIDA')}")
print(f"   WAYLAND_DISPLAY: {os.environ.get('WAYLAND_DISPLAY', 'NÃO DEFINIDA')}")
print()

# 2. Importar PySide6
print("2. Testando importação PySide6:")
try:
    from PySide6.QtWidgets import QApplication, QLabel, QMainWindow
    from PySide6.QtCore import Qt
    print("   ✓ PySide6 importado com sucesso")
except ImportError as e:
    print(f"   ❌ Erro ao importar PySide6: {e}")
    sys.exit(1)
print()

# 3. Criar QApplication
print("3. Criando QApplication:")
try:
    app = QApplication(sys.argv)
    print("   ✓ QApplication criada")
except Exception as e:
    print(f"   ❌ Erro ao criar QApplication: {e}")
    sys.exit(1)
print()

# 4. Verificar tela
print("4. Verificando tela disponível:")
screen = app.primaryScreen()
if screen:
    print(f"   ✓ Tela detectada: {screen.name()}")
    print(f"   Geometria: {screen.geometry().width()}x{screen.geometry().height()}")
    print(f"   DPI: {screen.logicalDotsPerInch()}")
else:
    print("   ❌ Nenhuma tela detectada!")
    print("   PROBLEMA: O Qt não consegue acessar o servidor X")
print()

# 5. Tentar criar e mostrar janela
print("5. Testando criação de janela:")
try:
    window = QMainWindow()
    window.setWindowTitle("Teste GYMNight")
    window.resize(400, 300)
    
    label = QLabel("Se você vê esta janela, o Qt está funcionando!")
    label.setAlignment(Qt.AlignCenter)
    window.setCentralWidget(label)
    
    window.show()
    print("   ✓ Janela criada e show() chamado")
    print("   A janela deve aparecer agora...")
    print()
    print("   Pressione Ctrl+C para fechar")
    
    sys.exit(app.exec())
    
except Exception as e:
    print(f"   ❌ Erro ao criar janela: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

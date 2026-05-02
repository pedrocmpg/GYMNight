#!/bin/bash

echo "=== Diagnóstico GYMNight ==="
echo ""

echo "1. Verificando variáveis de ambiente:"
echo "   DISPLAY: $DISPLAY"
echo "   QT_QPA_PLATFORM: $QT_QPA_PLATFORM"
echo ""

echo "2. Verificando Python e PySide6:"
source .venv/bin/activate
python --version
python -c "from PySide6.QtWidgets import QApplication; print('PySide6 OK')" 2>&1
echo ""

echo "3. Verificando servidor X:"
if command -v xdpyinfo &> /dev/null; then
    xdpyinfo -display :0 &> /dev/null && echo "   Servidor X está rodando" || echo "   ❌ Servidor X não está acessível"
else
    echo "   xdpyinfo não instalado (instale com: sudo apt install x11-utils)"
fi
echo ""

echo "4. Testando QApplication com debug:"
export QT_DEBUG_PLUGINS=1
python -c "
import sys
from PySide6.QtWidgets import QApplication, QLabel

app = QApplication(sys.argv)
label = QLabel('Teste')
label.show()
print('Janela criada com sucesso!')
print(f'Tela disponível: {app.primaryScreen()}')
print(f'Geometria da tela: {app.primaryScreen().geometry() if app.primaryScreen() else \"N/A\"}')
" 2>&1
echo ""

echo "5. Verificando WSLg:"
if [ -d "/mnt/wslg" ]; then
    echo "   ✓ WSLg está disponível"
    echo "   WAYLAND_DISPLAY: $WAYLAND_DISPLAY"
else
    echo "   ❌ WSLg não detectado"
fi
echo ""

echo "=== Fim do diagnóstico ==="

#!/bin/bash

echo "🚀 Iniciando GYMNight..."
echo ""

# Ativa o ambiente virtual
source .venv/bin/activate

# Verifica se WSLg está disponível
if [ -d "/mnt/wslg" ]; then
    echo "✓ WSLg detectado"
    export DISPLAY=:0
    export QT_QPA_PLATFORM=xcb
else
    echo "⚠ WSLg não detectado - tentando configuração alternativa"
    # Tenta detectar IP do host Windows para VcXsrv
    export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0
    export QT_QPA_PLATFORM=xcb
fi

echo "  DISPLAY: $DISPLAY"
echo "  QT_QPA_PLATFORM: $QT_QPA_PLATFORM"
echo ""

# Executa o aplicativo
echo "Executando aplicativo..."
python main.py

# Captura o código de saída
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "❌ O aplicativo encerrou com erro (código: $EXIT_CODE)"
    echo ""
    echo "💡 Dicas:"
    echo "   1. Execute 'python test_display.py' para diagnosticar"
    echo "   2. Leia SOLUCAO_JANELA.md para mais ajuda"
    echo "   3. Verifique se o WSL está atualizado: wsl --update (no Windows)"
fi

exit $EXIT_CODE

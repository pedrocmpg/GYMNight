#!/bin/bash

echo "🚀 Iniciando GYMNight..."
echo ""

# Ativa o ambiente virtual
if [ -d ".venv" ]; then
    echo "✓ Ativando ambiente virtual..."
    source .venv/bin/activate
else
    echo "❌ Ambiente virtual não encontrado!"
    echo "💡 Execute: python3 -m venv .venv"
    exit 1
fi

echo ""

# Executa o aplicativo
echo "Executando aplicativo..."
python main.py

# Captura o código de saída
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "❌ O aplicativo encerrou com erro (código: $EXIT_CODE)"
fi

exit $EXIT_CODE

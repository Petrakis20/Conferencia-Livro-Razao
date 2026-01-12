#!/bin/bash

# Script de inicialização do Sistema de Conferência Input Fiscal
# Uso: ./start.sh

echo "🚀 Iniciando Sistema de Conferência Input Fiscal..."
echo ""

# Verificar se o ambiente virtual existe
if [ ! -d "venv" ]; then
    echo "⚠️  Ambiente virtual não encontrado. Criando..."
    python3 -m venv venv
    echo "✅ Ambiente virtual criado!"
    echo ""
fi

# Verificar se as dependências estão instaladas
if [ ! -f "venv/bin/streamlit" ]; then
    echo "📦 Instalando dependências..."
    ./venv/bin/pip install -r requirements.txt
    echo "✅ Dependências instaladas!"
    echo ""
fi

# Iniciar o Streamlit
echo "🌐 Iniciando servidor Streamlit..."
echo "📍 Acesse: http://localhost:8501"
echo ""
echo "💡 Para parar o servidor, pressione Ctrl+C"
echo ""

./venv/bin/streamlit run app.py

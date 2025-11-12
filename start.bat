@echo off
REM ========================================
REM Sistema de Conferência Input Fiscal
REM Script de inicialização Windows
REM ========================================

echo.
echo ========================================
echo  Sistema de Conferencia Input Fiscal
echo ========================================
echo.

REM Muda para o diretório do script
cd /d "%~dp0"

REM Verifica se Python está instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado!
    echo.
    echo Por favor, instale Python 3.8 ou superior:
    echo https://www.python.org/downloads/
    echo.
    echo Certifique-se de marcar "Add Python to PATH" durante instalacao.
    echo.
    pause
    exit /b 1
)

echo [OK] Python encontrado
echo.

REM Verifica se ambiente virtual existe
if not exist "venv\Scripts\activate.bat" (
    echo [AVISO] Ambiente virtual nao encontrado.
    echo Criando ambiente virtual...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERRO] Falha ao criar ambiente virtual
        pause
        exit /b 1
    )
    echo [OK] Ambiente virtual criado
    echo.
)

REM Ativa ambiente virtual
echo Ativando ambiente virtual...
call venv\Scripts\activate.bat

REM Verifica se dependências estão instaladas
pip show streamlit >nul 2>&1
if %errorlevel% neq 0 (
    echo [AVISO] Dependencias nao instaladas.
    echo Instalando dependencias...
    echo.
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERRO] Falha ao instalar dependencias
        pause
        exit /b 1
    )
    echo.
    echo [OK] Dependencias instaladas
    echo.
)

REM Verifica se arquivo .env existe
if not exist "Alterdata_BI\.env" (
    echo [AVISO] Arquivo .env nao encontrado em Alterdata_BI
    echo.
    echo Configure as credenciais em Alterdata_BI\.env
    echo Use Alterdata_BI\.env.example como modelo
    echo.
    pause
)

echo ========================================
echo  Iniciando sistema...
echo ========================================
echo.
echo Sistema rodando em: http://localhost:8501
echo.
echo Pressione Ctrl+C para parar o servidor
echo.

REM Inicia Streamlit
streamlit run app.py

REM Se streamlit falhar
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Falha ao iniciar Streamlit
    echo.
    pause
    exit /b 1
)

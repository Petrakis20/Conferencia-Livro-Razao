@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem ============================================================
rem  Robo BI Contábil - Executor (diagnóstico reforçado)
rem ============================================================

set "PROJECT_DIR=C:\script\Robo_BI_Contabil\Alterdata_BI"
set "CFG_FILE=C:\script\Robo_BI_Contabil\params.txt"
set "LOG_DIR=C:\scripts\log_BI_Contabil"
set "NODE_HOME=C:\Program Files\nodejs"

chcp 65001 >nul 2>&1

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

for /f "tokens=1-3 delims=/- " %%a in ("%date%") do ( set _D=%%c-%%b-%%a )
for /f "tokens=1-3 delims=:." %%h in ("%time%") do ( set _T=%%h-%%i-%%j )
set "RUN_LOG=%LOG_DIR%\run_%_D%_%_T%.log"

echo [INFO] Iniciando execução em %date% %time% > "%RUN_LOG%"
echo [INFO] Projeto: "%PROJECT_DIR%" >> "%RUN_LOG%"
echo [INFO] Params:  "%CFG_FILE%" >> "%RUN_LOG%"

rem --- PATH do Node ---
if exist "%NODE_HOME%\node.exe" (
  set "PATH=%NODE_HOME%;%NODE_HOME%\node_modules\npm\bin;%PATH%"
  echo [INFO] NODE_HOME: "%NODE_HOME%" >> "%RUN_LOG%"
) else (
  echo [WARN] NODE_HOME nao encontrado em "%NODE_HOME%". Tentando PATH atual... >> "%RUN_LOG%"
)

rem --- Verifica Node/NPM ---
where node >> "%RUN_LOG%" 2>&1
set "EC=%ERRORLEVEL%"
echo [DEBUG] where node -> EC=%EC% >> "%RUN_LOG%"
if errorlevel 1 (
  echo [ERRO] Node.js nao encontrado no PATH. >> "%RUN_LOG%"
  exit /b 1
)
for /f %%v in ('node -v') do set NODEVER=%%v
echo [INFO] node -v: %NODEVER% >> "%RUN_LOG%"

where npm >> "%RUN_LOG%" 2>&1
echo [DEBUG] where npm -> EC=%ERRORLEVEL% >> "%RUN_LOG%"

rem --- Checa index.js e lista conteúdo da pasta (sempre) ---
if not exist "%PROJECT_DIR%" (
  echo [ERRO] PROJECT_DIR nao existe: "%PROJECT_DIR%" >> "%RUN_LOG%"
  exit /b 1
)
pushd "%PROJECT_DIR%"
echo [INFO] Diretório atual: %cd% >> "%RUN_LOG%"
echo [INFO] Conteudo da pasta: >> "%RUN_LOG%"
dir /-c >> "%RUN_LOG%" 2>&1

if not exist "index.js" (
  echo [ERRO] index.js NAO encontrado em "%PROJECT_DIR%". >> "%RUN_LOG%"
  popd & exit /b 1
)

rem --- Dependencias (apenas se existir package.json) ---
if exist "package.json" (
  if not exist "node_modules" (
    echo [INFO] node_modules ausente. Instalando dependencias... >> "%RUN_LOG%"
    call "%NODE_HOME%\npm.cmd" ci >> "%RUN_LOG%" 2>&1
    set "EC=%ERRORLEVEL%"
    echo [DEBUG] npm ci -> EC=%EC% >> "%RUN_LOG%"
    if not "%EC%"=="0" (
      echo [WARN] npm ci falhou. Tentando npm install... >> "%RUN_LOG%"
      call "%NODE_HOME%\npm.cmd" install >> "%RUN_LOG%" 2>&1
      set "EC=%ERRORLEVEL%"
      echo [DEBUG] npm install -> EC=%EC% >> "%RUN_LOG%"
      if not "%EC%"=="0" (
        echo [ERRO] Falha ao instalar dependencias. >> "%RUN_LOG%"
        rem não aborta — vamos tentar rodar mesmo assim
      )
    )
  ) else (
    echo [INFO] node_modules presente. Pulando instalacao. >> "%RUN_LOG%"
  )
) else (
  echo [WARN] package.json NAO encontrado. Pulando instalacao de dependencias. >> "%RUN_LOG%"
)

rem --- Mostra .env (apenas chaves, sem valores) ---
if exist ".env" (
  echo [INFO] .env encontrado. Chaves: >> "%RUN_LOG%"
  for /f "usebackq tokens=1* delims==" %%A in (".env") do (
    set "K=%%A"
    if not "!K!"=="" if not "!K:~0,1!"=="#" echo    - %%A >> "%RUN_LOG%"
  )
) else (
  echo [WARN] .env NAO encontrado. >> "%RUN_LOG%"
)

rem --- Executa o robô (SEMPRE) ---
echo [INFO] Executando: "%NODE_HOME%\node.exe" index.js --cfg "%CFG_FILE%" >> "%RUN_LOG%"
"%NODE_HOME%\node.exe" index.js --cfg "%CFG_FILE%" >> "%RUN_LOG%" 2>&1
set "EXITCODE=%ERRORLEVEL%"
echo [DEBUG] node index.js EC=%EXITCODE% >> "%RUN_LOG%"

if "%EXITCODE%"=="0" (
  echo [OK] Execucao concluida com sucesso. >> "%RUN_LOG%"
) else (
  echo [ERRO] Execucao terminou com codigo %EXITCODE%. >> "%RUN_LOG%"
)

popd
echo [INFO] Fim em %date% %time% >> "%RUN_LOG%"
exit /b %EXITCODE%

@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ============================================================
echo   PIMS UNSA - Agente #8 Formacion y Conciencia
echo   Instalador y Lanzador Automatico (Windows)
echo ============================================================
echo.

cd /d "%~dp0"

REM 1. Verificar Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python no esta instalado o no se encuentra en el PATH.
    echo Por favor instale Python 3.10 o superior: https://www.python.org/
    pause
    exit /b 1
)

REM 2. Verificar Node.js y npm
npm --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js / npm no esta instalado o no se encuentra en el PATH.
    echo Por favor instale Node.js 18 o superior: https://nodejs.org/
    pause
    exit /b 1
)

REM 3. Configurar Backend y Entorno Virtual
echo [1/5] Configurando entorno virtual de Python en backend...
if not exist "backend\venv" (
    echo Creando entorno virtual en backend\venv...
    python -m venv backend\venv
)

call backend\venv\Scripts\activate.bat

echo [2/5] Instalando / verificando dependencias de Python (requirements.txt)...
python -m pip install --upgrade pip --quiet
pip install -r backend\requirements.txt

REM 4. Verificar archivo .env
if not exist "backend\.env" (
    echo [AVISO] backend\.env no encontrado. Copiando desde .env.example...
    copy backend\.env.example backend\.env > nul
    echo Creado backend\.env. Por favor revisa tus claves de API si es necesario.
)

REM 5. Inicializar Base de Datos SQLite y ChromaDB
echo [3/5] Inicializando base de datos SQLite y usuarios precargados...
cd backend
python init_db.py
if not exist "chroma_db" (
    echo [4/5] Indexando base de conocimiento RAG en ChromaDB...
    python ingesta.py
) else (
    echo [4/5] Base de conocimiento ChromaDB lista.
)
cd ..

REM 6. Configurar Frontend
echo [5/5] Verificando dependencias del Frontend (npm install)...
cd frontend
if not exist "node_modules" (
    echo Instalando paquetes de Node...
    call npm install
)
cd ..

echo.
echo ============================================================
echo   Todo instalado y configurado correctamente!
echo   Levantando Backend (puerto 8000) y Frontend (puerto 5173)...
echo ============================================================
echo.

REM Iniciar Backend en una nueva ventana de terminal
start "PIMS Backend - FastAPI" cmd /k "cd /d %~dp0backend && call venv\Scripts\activate.bat && uvicorn main:app --reload --port 8000"

REM Iniciar Frontend en una nueva ventana de terminal
start "PIMS Frontend - Vite" cmd /k "cd /d %~dp0frontend && npm run dev"

REM Esperar 3 segundos y abrir el navegador en http://localhost:5173
timeout /t 3 > nul
start http://localhost:5173

echo.
echo ============================================================
echo   Aplicación disponible en:
echo   - Frontend: http://localhost:5173
echo   - Backend:  http://localhost:8000
echo   - Swagger:  http://localhost:8000/docs
echo ============================================================
echo.
pause

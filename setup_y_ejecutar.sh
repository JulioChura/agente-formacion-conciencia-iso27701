#!/usr/bin/env bash
# ============================================================
#   PIMS UNSA - Agente #8 Formacion y Conciencia
#   Instalador y Lanzador Automatico (Linux / macOS)
# ============================================================

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "============================================================"
echo "  PIMS UNSA - Agente #8 Formacion y Conciencia"
echo "  Instalador y Lanzador Automatico (Linux / macOS)"
echo "============================================================"
echo ""

# 1. Verificar Python 3
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 no esta instalado o no se encuentra en el PATH."
    exit 1
fi

# 2. Verificar Node.js y npm
if ! command -v npm &> /dev/null; then
    echo "[ERROR] Node.js / npm no esta instalado o no se encuentra en el PATH."
    exit 1
fi

# 3. Configurar Backend y Entorno Virtual
echo "[1/5] Configurando entorno virtual de Python en backend..."
if [ ! -d "backend/venv" ]; then
    echo "Creando entorno virtual en backend/venv..."
    python3 -m venv backend/venv
fi

source backend/venv/bin/activate

echo "[2/5] Instalando dependencias de Python (requirements.txt)..."
python -m pip install --upgrade pip --quiet
pip install -r backend/requirements.txt

# 4. Verificar archivo .env
if [ ! -f "backend/.env" ]; then
    echo "[AVISO] backend/.env no encontrado. Copiando desde .env.example..."
    cp backend/.env.example backend/.env
    echo "Creado backend/.env. Por favor revisa tus claves de API."
fi

# 5. Inicializar Base de Datos SQLite y ChromaDB
echo "[3/5] Inicializando base de datos SQLite y usuarios precargados..."
cd backend
python init_db.py
if [ ! -d "chroma_db" ]; then
    echo "[4/5] Indexando base de conocimiento RAG en ChromaDB..."
    python ingesta.py
else
    echo "[4/5] Base de conocimiento ChromaDB lista."
fi
cd ..

# 6. Configurar Frontend
echo "[5/5] Verificando dependencias del Frontend (npm install)..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "Instalando paquetes de Node..."
    npm install
fi
cd ..

echo ""
echo "============================================================"
echo "  Todo instalado y configurado correctamente!"
echo "  Levantando Backend (puerto 8000) y Frontend (puerto 5173)..."
echo "============================================================"
echo ""

# Función para limpiar procesos al presionar Ctrl+C
cleanup() {
    echo ""
    echo "Deteniendo servicios..."
    kill $(jobs -p) 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Iniciar Backend
echo "Iniciando Backend en http://127.0.0.1:8000 ..."
(cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000) &

# Iniciar Frontend
echo "Iniciando Frontend en http://localhost:5173 ..."
(cd frontend && npm run dev) &

sleep 3
echo ""
echo "============================================================"
echo "  Servicios activos:"
echo "  - Frontend: http://localhost:5173"
echo "  - Backend:  http://127.0.0.1:8000"
echo "  - Swagger:  http://127.0.0.1:8000/docs"
echo "  Presiona Ctrl+C para detener ambos servicios."
echo "============================================================"
echo ""

wait

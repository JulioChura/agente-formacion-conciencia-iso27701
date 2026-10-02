#!/bin/bash
set -e
echo "=== Instalando dependencias ==="
pip install -r requirements.txt

echo "=== Descargando modelos de Ollama ==="
ollama pull qwen2.5:7b || true
ollama pull nomic-embed-text || true

echo "=== Indexando documentos ==="
python backend/indexar.py || true

echo "=== Levantando backend ==="
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "=== Levantando frontend ==="
python -m http.server 5500 --directory frontend &
FRONTEND_PID=$!

echo "Aplicacion lista."
echo "Frontend: http://localhost:5500"
echo "Backend:  http://localhost:8000"
echo "MCP:      python backend/mcp_server.py"
wait $BACKEND_PID $FRONTEND_PID

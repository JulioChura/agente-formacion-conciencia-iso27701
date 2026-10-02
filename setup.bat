@echo off
echo === Instalando dependencias ===
pip install -r requirements.txt

echo === Descargando modelos de Ollama ===
ollama pull qwen2.5:7b
ollama pull nomic-embed-text

echo === Indexando documentos ===
python backend\indexar.py

echo === Levantando backend ===
start cmd /k uvicorn backend.main:app --host 0.0.0.0 --port 8000

echo === Levantando frontend ===
start cmd /k python -m http.server 5500 --directory frontend

echo Aplicacion lista. Frontend: http://localhost:5500

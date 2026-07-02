#!/bin/bash
set -e

echo "🌭 Salchicha - Tickets de Entrega"
echo "================================="

# Backend
echo "→ Iniciando backend..."
cd backend
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

# Frontend
echo "→ Iniciando frontend..."
cd frontend
if [ ! -d "node_modules" ]; then
  npm install
fi
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Listo!"
echo "   Frontend: http://localhost:5173"
echo "   Backend:  http://localhost:8000"
echo ""
echo "Ctrl+C para detener ambos procesos"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait

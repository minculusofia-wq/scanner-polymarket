#!/bin/bash

# ============================================
# 🚀 POLYMARKET SCANNER - QUICK LAUNCHER
# ============================================
# Port fixe: 3333 (pour éviter les conflits)
# ============================================

cd "$(dirname "$0")"
PROJECT_DIR=$(pwd)
PORT=3333

clear
echo ""
echo "╔════════════════════════════════════════════════════╗"
echo "║     🐋 POLYMARKET SCANNER - DÉMARRAGE              ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# Fonction de nettoyage
cleanup() {
    echo ""
    echo "👋 Arrêt du scanner..."
    pkill -f "uvicorn main:app --reload --port 8000" 2>/dev/null
    lsof -ti:$PORT | xargs kill -9 2>/dev/null
    exit 0
}
trap cleanup INT TERM

# Vérification Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 requis. Installe avec: brew install python3"
    read -p "Appuie sur Entrée pour fermer..."
    exit 1
fi

# Vérification Node
if ! command -v npm &> /dev/null; then
    echo "❌ Node.js requis. Installe avec: brew install node"
    read -p "Appuie sur Entrée pour fermer..."
    exit 1
fi

echo "✅ Python3 et Node.js détectés"

# Créer .env si nécessaire
if [ ! -f "backend/.env" ]; then
    echo "📋 Création du fichier .env..."
    cp .env.example backend/.env 2>/dev/null
fi

# Installation backend si nécessaire
if [ ! -d "backend/venv" ]; then
    echo ""
    echo "📦 Installation backend (première fois)..."
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt -q
    cd "$PROJECT_DIR"
    echo "✅ Backend installé"
fi

# Installation frontend si nécessaire
if [ ! -d "frontend/node_modules" ]; then
    echo ""
    echo "📦 Installation frontend (première fois)..."
    cd frontend
    npm install --silent 2>/dev/null
    cd "$PROJECT_DIR"
    echo "✅ Frontend installé"
fi

# Libérer le port 3333 si utilisé
echo ""
echo "🧹 Libération du port $PORT..."
lsof -ti:$PORT | xargs kill -9 2>/dev/null
sleep 1

# Démarrer le backend
echo "🔌 Démarrage du backend (port 8000)..."
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000 > /dev/null 2>&1 &
cd "$PROJECT_DIR"
sleep 2

# Démarrer le frontend sur le port fixe
echo "🎨 Démarrage du frontend (port $PORT)..."
cd frontend
npm run dev > /dev/null 2>&1 &
cd "$PROJECT_DIR"

# Attendre que le frontend démarre
echo "⏳ Attente du démarrage..."
sleep 5

echo ""
echo "╔════════════════════════════════════════════════════╗"
echo "║     ✅ SCANNER PRÊT !                              ║"
echo "╠════════════════════════════════════════════════════╣"
echo "║                                                    ║"
echo "║   📊 Dashboard: http://localhost:$PORT             ║"
echo "║   🔌 API:       http://localhost:8000              ║"
echo "║                                                    ║"
echo "║   Ferme cette fenêtre pour arrêter le scanner      ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# Ouvrir Brave automatiquement
sleep 1
open "http://localhost:$PORT"

echo "🌐 Brave ouvert sur http://localhost:$PORT"
echo ""
echo "Le scanner tourne en arrière-plan..."
echo "Ferme cette fenêtre pour arrêter."
echo ""

# Garder le script actif
while true; do
    sleep 60
done

# 🦅 Polymarket Scanner Bot

Un bot de trading algorithmique avancé pour scanner, analyser et tracker les opportunités sur Polymarket en temps réel.

![Dashboard Preview](frontend/public/dashboard-preview.png)

## 🚀 Fonctionnalités Principales

### 1. 🔍 Scanner d'Opportunités
- **Analyse Temps Réel** : Scanne des milliers de marchés Polymarket instantanément.
- **Scoring Intelligent** : Algorithme propriétaire (0-100) basé sur le volume, la liquidité et la volatilité.
- **Filtres Avancés** : Filtrage par score, volume minimum, liquidité et niveau d'opportunité.

### 2. ⚖️ Mode Équilibrage (Nouveau)
- **Scanning Global** : Analyse l'intégralité du marché (plus de 3000 marchés actifs) sans limite.
- **Détection "Coin Flip"** : Isole spécifiquement les opportunités où les probabilités sont entre 45% et 55%.
- **Vue Simplifiée** : Interface dédiée sans scoring complexe, focalisée uniquement sur le prix et le volume.

### 3. 🐋 Whale Tracking (Amélioré)
- **Détection des Gros Trades** : Identifie les transactions supérieures à $10,000.
- **Profilage des Whales** : Analyse le comportement des gros investisseurs.
- **NOUVEAU : Filtrage Avancé** : Configurez le nombre minimum de trades et de whales uniques pour filtrer le bruit.

### 4. 📊 Quant Analysis (Monte Carlo)
- **Simulations Bootstrap** : 10,000 simulations de prix basées sur l'historique (Binance).
- **Détection d'Edge** : Compare les probabilités réelles aux prix Polymarket.
- **Support Multi-Actifs** : Analyse BTC, ETH et SOL pour trouver des divergences de prix.
- **Visualisation dédiée** : Nouvel onglet "Quant" pour voir les opportunités mathématiques.

### 5. ⚡ Performance & Résilience
- **Architecture WebSocket** : Mises à jour en push instantané.
- **Système de Cache** : Continue de fonctionner même si l'API Polymarket est en panne.
- **Base de Données SQLite** : Historique complet des signaux.

### 6. 📰 Analyse de News Multi-sources
- **Agrégateur IA** : Combine Google News, NewsAPI et SerpAPI.
- **Analyse de Sentiment** : Corrélation entre les news et les mouvements de prix.
- **Détection de Catalyseurs** : Identifie les événements majeurs impactant les marchés.

## 🛠 Architecture Technique

Le projet est divisé en deux parties principales :

### Backend (Python/FastAPI)
- **API REST & WebSocket** : `FastAPI`, `Uvicorn`
- **Data Processing** : `Pandas`, `NumPy`
- **Base de Données** : `SQLite`, `SQLAlchemy`
- **Services** :
  - `WhaleTracker` : Surveillance de la blockchain/CLOB.
  - `NewsAggregator` : Collecte et analyse de news.
  - `CacheService` : Persistance et résilience.

### Frontend (Next.js/React)
- **Interface** : `React 18`, `TailwindCSS`
- **Visualisation** : `Recharts`, `Lucide Icons`
- **Temps Réel** : Hooks WebSocket personnalisés.

## 📦 Installation

### Prérequis
- Python 3.11+
- Node.js 18+
- Clés API (Optionnel pour les news) : NewsAPI, SerpAPI

### 1. Installation du Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate sur Windows
pip install -r requirements.txt
```

### 2. Configuration
Créez un fichier `.env` dans le dossier `backend` :
```env
NEWSAPI_KEY=votre_cle_ici
SERPAPI_KEY=votre_cle_ici
```

### 3. Installation du Frontend
```bash
cd frontend
npm install
```

## 🚀 Démarrage

### Lancement Rapide (Mac/Linux)
Utilisez le script de lancement automatique :
```bash
./LANCER.command
```

### Lancement Manuel
**Terminal 1 (Backend) :**
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

**Terminal 2 (Frontend) :**
```bash
cd frontend
npm run dev
```

Accédez ensuite à `http://localhost:3333`

## 📊 Structure du Projet

```
scanner-polymarket/
├── backend/
│   ├── app/
│   │   ├── api/          # Endpoints (signals, whales, news...)
│   │   ├── core/         # Config, DB, Cache, WebSocket
│   │   └── services/     # Logique métier (Tracker, Aggregator)
│   ├── data/             # Base de données SQLite
│   └── main.py           # Point d'entrée
├── frontend/
│   ├── src/
│   │   ├── app/          # Pages Next.js
│   │   ├── components/   # Composants React
│   │   └── hooks/        # Custom Hooks (useWebSocket)
│   └── public/           # Assets
└── LANCER.command        # Script de démarrage
```

## 🛡️ Sécurité & Performance
- **Rate Limiting** : Respectueux des APIs publiques.
- **Error Handling** : Gestion robuste des pannes réseaux.
- **Data Persistence** : Sauvegarde locale pour ne jamais perdre l'historique.

---
*Développé avec ❤️ pour la communauté Polymarket.*

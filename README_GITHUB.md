# 🦅 Polymarket Scanner Bot

An advanced algorithmic trading bot designed to scan, analyze, and track real-time opportunities on Polymarket.

![Dashboard Preview](frontend/public/dashboard-preview.png)

## 🚀 Core Features

### 1. 🔍 Opportunity Scanner
- **Real-Time Analysis**: Instantly scans thousands of Polymarket markets.
- **Intelligent Scoring**: Proprietary algorithm (0–100) based on volume, liquidity, and volatility.
- **Advanced Filters**: Filter by score, minimum volume, liquidity, and opportunity level.

### 2. ⚖️ Balancing Mode (New)
- **Global Scanning**: Analyzes the entire market (3,000+ active markets) with no limits.
- **Coin Flip Detection**: Specifically isolates opportunities where probabilities are between 45% and 55%.
- **Simplified View**: Dedicated interface without complex scoring, focused only on price and volume.

### 3. 🐋 Whale Tracking (Improved)
- **Large Trade Detection**: Identifies transactions above $10,000.
- **Whale Profiling**: Analyzes the behavior of large investors.
- **NEW: Advanced Filtering**: Configure minimum trade count and unique whales to reduce noise.

### 4. 📊 Quant Analysis (Monte Carlo)
- **Bootstrap Simulations**: 10,000 price simulations based on historical data (Binance).
- **Edge Detection**: Compares real probabilities against Polymarket prices.
- **Multi-Asset Support**: BTC, ETH, and SOL analysis to identify price divergences.
- **Dedicated Visualization**: New "Quant" tab for mathematical opportunities.

### 5. 🐻 Contrarian Strategy (Fade)
- **Hype Detection**: Identifies overheated markets (Price > $0.60 + euphoria).
- **Fade Scanner**: Dedicated tab to find opportunities to bet "NO" against the crowd.
- **Crypto Sentiment**: Integration of the Fear & Greed Index for market context.

### 6. 🌍 Macro Data & TradFi Sentiment
- **Alpha Vantage**: News sentiment for S&P 500, Gold, and Oil.
- **Finnhub**: Economic calendar to adjust simulation volatility.
- **Sentiment Analysis**: Correlation between news and price movements.

### 7. ⚡ Performance & Resilience
- **WebSocket Architecture**: Instant push-based updates.
- **Caching System**: Continues operating even if the Polymarket API is down.
- **SQLite Database**: Full signal history storage.

## 🛠 Technical Architecture

The project is divided into two main components:

### Backend (Python / FastAPI)
- **REST & WebSocket API**: FastAPI, Uvicorn
- **Data Processing**: Pandas, NumPy
- **Database**: SQLite, SQLAlchemy
- **Services**:
  - `WhaleTracker`: Blockchain / CLOB monitoring
  - `NewsAggregator`: News collection and analysis
  - `CacheService`: Persistence and resilience

### Frontend (Next.js / React)
- **UI**: React 18, TailwindCSS
- **Visualization**: Recharts, Lucide Icons
- **Real-Time**: Custom WebSocket hooks

## 📦 Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- API keys (optional for news features): NewsAPI, SerpAPI

### 1. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 2. Configuration
Create a `.env` file inside the `backend` directory:
```env
NEWSAPI_KEY=your_key_here
SERPAPI_KEY=your_key_here
# Optional (advanced features)
ALPHA_VANTAGE_KEY=your_key_here
FINNHUB_KEY=your_key_here
```

### 3. Frontend Setup
```bash
cd frontend
npm install
```

## 🚀 Running the Project

### Quick Start (Mac / Linux)
Use the automatic launch script:
```bash
./LANCER.command
```

### Manual Start

**Terminal 1 (Backend):**
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev
```

Then open:
```
http://localhost:3333
```

## 📊 Project Structure

```
scanner-polymarket/
├── backend/
│   ├── app/
│   │   ├── api/          # Endpoints (signals, whales, news...)
│   │   ├── core/         # Config, DB, Cache, WebSocket
│   │   └── services/     # Business logic
│   ├── data/             # SQLite database
│   └── main.py           # Entry point
├── frontend/
│   ├── src/
│   │   ├── app/          # Next.js pages
│   │   ├── components/   # React components
│   │   └── hooks/        # Custom hooks
│   └── public/           # Assets
└── LANCER.command        # Startup script
```

## 🛡️ Security & Performance
- **Rate Limiting**: Respectful use of public APIs.
- **Error Handling**: Robust handling of network failures.
- **Data Persistence**: Local backups to never lose historical data.

---
*Built with ❤️ for the Polymarket community.*

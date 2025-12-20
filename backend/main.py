"""
Polymarket Scanner Bot - Main Application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import asyncio
import os

# Load environment variables
load_dotenv()

from app.api import signals, whales, markets, volume, history, news, monte_carlo
from app.core.websocket import manager, MessageTypes
from app.core.database import db


# Background task for periodic updates
async def periodic_broadcast():
    """Broadcast updates to all connected clients every 30 seconds."""
    while True:
        await asyncio.sleep(30)
        
        if manager.connection_count > 0:
            try:
                # Import here to avoid circular imports
                from app.api.signals import fetch_markets, market_to_signal
                
                markets_data, error, is_cached, cache_age = await fetch_markets()
                
                if markets_data:
                    signals_list = []
                    for m in markets_data[:50]:
                        try:
                            if not m.get("closed") and m.get("question"):
                                sig = market_to_signal(m)
                                signals_list.append(sig.dict())
                        except Exception:
                            pass
                    
                    # Save snapshot to database
                    if signals_list and not is_cached:
                        try:
                            db.save_signals_batch(signals_list)
                        except Exception as e:
                            print(f"Database save error: {e}")
                    
                    await manager.broadcast({
                        "type": MessageTypes.SIGNALS_UPDATE,
                        "data": {
                            "signals": signals_list,
                            "total": len(signals_list),
                            "cached": is_cached,
                            "cache_age": cache_age
                        },
                        "error": error
                    })
            except Exception as e:
                print(f"Broadcast error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    print("🚀 Starting Polymarket Scanner Bot...")
    
    # Start background broadcast task
    broadcast_task = asyncio.create_task(periodic_broadcast())
    
    yield
    
    # Cleanup
    broadcast_task.cancel()
    print("👋 Shutting down Polymarket Scanner Bot...")


# FastAPI application
app = FastAPI(
    title="Polymarket Scanner Bot",
    description="Bot for scanning whales, volume, and news on Polymarket",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - Configure allowed origins via CORS_ORIGINS env var
# Default allows localhost for development
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(signals.router, prefix="/api/signals", tags=["Signals"])
app.include_router(whales.router, prefix="/api/whales", tags=["Whales"])
app.include_router(markets.router, prefix="/api/markets", tags=["Markets"])
app.include_router(volume.router, prefix="/api/volume", tags=["Volume"])
app.include_router(history.router, prefix="/api/history", tags=["History"])
app.include_router(news.router, prefix="/api/news", tags=["News"])
app.include_router(monte_carlo.router, prefix="/api/monte-carlo", tags=["Monte Carlo"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Polymarket Scanner Bot",
        "status": "running",
        "version": "1.0.0",
        "websocket": "/ws"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "websocket_connections": manager.connection_count
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.
    
    Message types received:
    - ping: Client heartbeat
    
    Message types sent:
    - connection_ack: Connection acknowledged
    - signals_update: Updated signals data
    - whale_trade: New whale trade detected
    - pong: Response to ping
    """
    await manager.connect(websocket)
    
    # Send initial acknowledgment
    await manager.send_personal(websocket, {
        "type": MessageTypes.CONNECTION_ACK,
        "message": "Connected to Polymarket Scanner"
    })
    
    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            
            try:
                import json
                message = json.loads(data)
                
                # Handle ping
                if message.get("type") == MessageTypes.PING:
                    await manager.send_personal(websocket, {
                        "type": MessageTypes.PONG
                    })
                    
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        await manager.disconnect(websocket)

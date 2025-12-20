"""
Binance OHLCV Data Fetcher for Monte Carlo simulations.
"""
import aiohttp
import asyncio
import os
import pandas as pd
import time
from math import ceil
from typing import Optional


def _get_ssl_context():
    """Get SSL context based on environment configuration."""
    import ssl
    if os.getenv("DISABLE_SSL_VERIFY", "").lower() == "true":
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context
    return None  # Use default SSL verification


# Interval to milliseconds mapping
INTERVAL_TO_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}


async def _fetch_klines_chunk(
    session: aiohttp.ClientSession,
    symbol: str,
    interval: str,
    start_time: int,
    limit: int,
) -> list:
    """Fetch a single chunk of klines from Binance."""
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": start_time,
        "limit": limit,
    }
    
    async with session.get(url, params=params) as response:
        if response.status == 200:
            return await response.json()
        else:
            print(f"Binance API error: {response.status}")
            return []


async def _get_klines_async(
    symbol: str,
    interval: str,
    n_candles: int
) -> pd.DataFrame:
    """
    Fetch OHLCV data from Binance asynchronously.
    
    Args:
        symbol: Trading pair (e.g., "BTCUSDT")
        interval: Candle interval (e.g., "1h")
        n_candles: Number of candles to fetch
        
    Returns:
        DataFrame with columns: date, open, high, low, close, volume
    """
    if interval not in INTERVAL_TO_MS:
        raise ValueError(f"Unsupported interval: {interval}")
    
    interval_ms = INTERVAL_TO_MS[interval]
    now_ms = int(time.time() * 1000)
    
    # Align to interval
    last_open_time = now_ms - (now_ms % interval_ms)
    earliest_open_time = last_open_time - (n_candles - 1) * interval_ms
    
    # Split into chunks of max 1000 candles (Binance limit)
    max_limit = 1000
    n_chunks = ceil(n_candles / max_limit)
    
    chunks = []
    for i in range(n_chunks):
        chunk_size = min(max_limit, n_candles - i * max_limit)
        chunk_start = earliest_open_time + i * max_limit * interval_ms
        chunks.append({
            "index": i,
            "start_time": chunk_start,
            "limit": chunk_size,
        })
    
    all_results = [None] * n_chunks
    ssl_context = _get_ssl_context()

    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Process in batches of 10 with 1s pause
        for batch_start in range(0, n_chunks, 10):
            batch = chunks[batch_start:batch_start + 10]
            
            tasks = [
                asyncio.create_task(
                    _fetch_klines_chunk(
                        session=session,
                        symbol=symbol,
                        interval=interval,
                        start_time=chunk["start_time"],
                        limit=chunk["limit"],
                    )
                )
                for chunk in batch
            ]
            
            results = await asyncio.gather(*tasks)
            
            for chunk, data in zip(batch, results):
                all_results[chunk["index"]] = data
            
            if batch_start + 10 < n_chunks:
                await asyncio.sleep(1)
    
    # Flatten all chunks
    klines = [item for sublist in all_results if sublist for item in sublist]
    
    if not klines:
        raise ValueError(f"No data returned for {symbol}")
    
    # Binance columns
    cols = [
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "n_trades",
        "taker_base_volume", "taker_quote_volume", "ignore",
    ]
    
    df = pd.DataFrame(klines, columns=cols)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    
    numeric_cols = ["open", "high", "low", "close", "volume"]
    df[numeric_cols] = df[numeric_cols].astype(float)
    
    df = df.sort_values("open_time").tail(n_candles).reset_index(drop=True)
    df = df[["open_time", "open", "high", "low", "close", "volume"]]
    df = df.rename(columns={"open_time": "date"})
    df.set_index("date", inplace=True)
    
    return df


async def get_binance_ohlcv(
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    n_candles: int = 8760  # 1 year of hourly data
) -> pd.DataFrame:
    """
    Get OHLCV data from Binance.
    
    Args:
        symbol: Trading pair (default: BTCUSDT)
        interval: Candle interval (default: 1h)
        n_candles: Number of candles (default: 8760 = 1 year hourly)
        
    Returns:
        DataFrame with OHLCV data
    """
    return await _get_klines_async(symbol, interval, n_candles)


def get_binance_ohlcv_sync(
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    n_candles: int = 8760
) -> pd.DataFrame:
    """Synchronous wrapper for get_binance_ohlcv."""
    return asyncio.run(_get_klines_async(symbol, interval, n_candles))

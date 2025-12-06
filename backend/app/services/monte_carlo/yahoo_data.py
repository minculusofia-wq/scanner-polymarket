"""
Yahoo Finance data fetcher for Monte Carlo simulations.
"""
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

def get_yahoo_ohlcv(
    symbol: str,
    interval: str = "1h",
    period: str = "2y"
) -> pd.DataFrame:
    """
    Fetch OHLCV data from Yahoo Finance.
    
    Args:
        symbol: Ticker symbol (e.g., "SPY", "^GSPC", "GC=F")
        interval: Candle interval (default: "1h")
        period: Data period to fetch (default: "2y")
        
    Returns:
        DataFrame with columns: date, open, high, low, close, volume
    """
    try:
        # Fetch data
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        
        if df.empty:
            raise ValueError(f"No data returned for {symbol}")
        
        # Reset index to get Date/Datetime as column
        df = df.reset_index()
        
        # Standardize column names
        # Yahoo returns: Date/Datetime, Open, High, Low, Close, Volume, Dividends, Stock Splits
        df.columns = [c.lower() for c in df.columns]
        
        # Rename 'datetime' or 'date' to 'date'
        if 'datetime' in df.columns:
            df = df.rename(columns={'datetime': 'date'})
        
        # Ensure we have required columns
        required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
        
        # Filter and reorder
        available_cols = [c for c in required_cols if c in df.columns]
        df = df[available_cols]
        
        # Set index to date for consistency with Binance data
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            # Remove timezone info if present to match Binance naive timestamps
            if df['date'].dt.tz is not None:
                df['date'] = df['date'].dt.tz_localize(None)
            df.set_index('date', inplace=True)
            
        return df
        
    except Exception as e:
        print(f"Error fetching Yahoo data for {symbol}: {e}")
        raise

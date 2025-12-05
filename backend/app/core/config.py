"""
Application configuration settings.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API URLs
    polymarket_api_url: str = "https://clob.polymarket.com"
    polymarket_gamma_api_url: str = "https://gamma-api.polymarket.com"
    
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/polymarket_scanner"
    redis_url: str = "redis://localhost:6379/0"
    
    # Whale Detection (configurable via API)
    whale_min_trade_usd: int = 10000
    whale_min_position_usd: int = 50000
    whale_win_rate_threshold: int = 60
    
    # Volume Analysis (configurable via API)
    volume_spike_threshold: int = 200
    volume_avg_window_days: int = 7
    unusual_volume_multiplier: int = 3
    
    # Signal Weights
    signal_weight_whale: int = 30
    signal_weight_volume: int = 30
    signal_weight_news: int = 20
    signal_weight_price: int = 20
    signal_alert_threshold: int = 70
    
    # Scanning
    scan_interval_seconds: int = 30
    max_markets_to_track: int = 100
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

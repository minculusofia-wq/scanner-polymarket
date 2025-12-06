"""
Database Service - SQLite for signal history and analytics.
"""
import sqlite3
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Optional, Any
from contextlib import contextmanager


class Database:
    """
    SQLite database for storing signal history.
    
    Features:
    - Signal snapshots for trend analysis
    - Market price history
    - Performance tracking
    """
    
    def __init__(self, db_path: str = None):
        if db_path:
            self._db_path = Path(db_path)
        else:
            self._db_path = Path(__file__).parent.parent.parent / "data" / "scanner.db"
        
        # Ensure directory exists
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_db()
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Signal snapshots table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS signal_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market_id TEXT NOT NULL,
                    slug TEXT,
                    question TEXT,
                    score INTEGER,
                    level TEXT,
                    yes_price REAL,
                    no_price REAL,
                    volume_24h REAL,
                    liquidity REAL,
                    whale_count INTEGER,
                    direction TEXT,
                    snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Market history table (for price trends)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market_id TEXT NOT NULL,
                    yes_price REAL,
                    no_price REAL,
                    volume_24h REAL,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Whale trades table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS whale_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT UNIQUE,
                    trader TEXT,
                    market_id TEXT,
                    market_question TEXT,
                    side TEXT,
                    size_usd REAL,
                    price REAL,
                    traded_at TIMESTAMP
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_signal_market ON signal_snapshots(market_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_signal_time ON signal_snapshots(snapshot_time)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_market ON market_history(market_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_whale_market ON whale_trades(market_id)')
    
    def save_signal_snapshot(self, signal: Dict) -> int:
        """Save a signal snapshot for trend analysis."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO signal_snapshots 
                (market_id, slug, question, score, level, yes_price, no_price, 
                 volume_24h, liquidity, whale_count, direction)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal.get('market_id', signal.get('id')),
                signal.get('slug', ''),
                signal.get('market_question', ''),
                signal.get('score', 0),
                signal.get('level', 'watch'),
                signal.get('yes_price', 0.5),
                signal.get('no_price', 0.5),
                signal.get('volume_24h', 0),
                signal.get('liquidity', 0),
                signal.get('whale_count', 0),
                signal.get('direction', 'YES')
            ))
            return cursor.lastrowid
    
    def save_signals_batch(self, signals: List[Dict]):
        """Save multiple signals at once."""
        for signal in signals:
            self.save_signal_snapshot(signal)
    
    def save_market_price(self, market_id: str, yes_price: float, no_price: float, volume_24h: float):
        """Save market price for history tracking."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO market_history (market_id, yes_price, no_price, volume_24h)
                VALUES (?, ?, ?, ?)
            ''', (market_id, yes_price, no_price, volume_24h))
    
    def save_whale_trade(self, trade: Dict) -> bool:
        """Save a whale trade. Returns False if already exists."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO whale_trades 
                    (trade_id, trader, market_id, market_question, side, size_usd, price, traded_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    trade.get('id'),
                    trade.get('trader', ''),
                    trade.get('market_id', ''),
                    trade.get('market_question', ''),
                    trade.get('side', 'YES'),
                    trade.get('size_usd', 0),
                    trade.get('price', 0.5),
                    trade.get('timestamp', datetime.now(timezone.utc).isoformat())
                ))
                return True
            except sqlite3.IntegrityError:
                return False  # Trade already exists
    
    def get_signal_history(self, market_id: str, hours: int = 24) -> List[Dict]:
        """Get signal history for a market."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            since = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            cursor.execute('''
                SELECT * FROM signal_snapshots 
                WHERE market_id = ? AND snapshot_time > ?
                ORDER BY snapshot_time ASC
            ''', (market_id, since.isoformat()))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_price_history(self, market_id: str, hours: int = 24) -> List[Dict]:
        """Get price history for a market."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            since = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            cursor.execute('''
                SELECT * FROM market_history 
                WHERE market_id = ? AND recorded_at > ?
                ORDER BY recorded_at ASC
            ''', (market_id, since.isoformat()))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_trending_markets(self, hours: int = 24, limit: int = 10) -> List[Dict]:
        """Get markets with biggest score changes."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            since = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Get markets with multiple snapshots and calculate score change
            cursor.execute('''
                SELECT 
                    market_id,
                    slug,
                    question,
                    MIN(score) as min_score,
                    MAX(score) as max_score,
                    MAX(score) - MIN(score) as score_change,
                    COUNT(*) as snapshot_count
                FROM signal_snapshots 
                WHERE snapshot_time > ?
                GROUP BY market_id
                HAVING snapshot_count > 1
                ORDER BY score_change DESC
                LIMIT ?
            ''', (since.isoformat(), limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_recent_whale_trades(self, limit: int = 20) -> List[Dict]:
        """Get recent whale trades from database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM whale_trades 
                ORDER BY traded_at DESC
                LIMIT ?
            ''', (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict:
        """Get database statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM signal_snapshots')
            signal_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM market_history')
            price_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM whale_trades')
            whale_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT market_id) FROM signal_snapshots')
            market_count = cursor.fetchone()[0]
            
            return {
                "signal_snapshots": signal_count,
                "price_records": price_count,
                "whale_trades": whale_count,
                "markets_tracked": market_count,
                "database_path": str(self._db_path)
            }
    
    def cleanup_old_data(self, days: int = 30):
        """Remove data older than specified days."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            since = datetime.now(timezone.utc) - timedelta(days=days)
            
            cursor.execute('DELETE FROM signal_snapshots WHERE snapshot_time < ?', (since.isoformat(),))
            cursor.execute('DELETE FROM market_history WHERE recorded_at < ?', (since.isoformat(),))
            
            conn.execute('VACUUM')


# Singleton instance
db = Database()

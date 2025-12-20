"""
Cache Service - In-memory cache with file backup.
Works without Redis for simplicity, with automatic persistence.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from pathlib import Path
from app.core.logger import get_logger

logger = get_logger(__name__)


class CacheService:
    """
    Simple cache service with:
    - In-memory storage for fast access
    - File backup for persistence across restarts
    - TTL (time-to-live) support
    - Automatic fallback to last known good data
    """
    
    def __init__(self, cache_dir: str = None):
        self._memory_cache: dict = {}
        self._cache_times: dict = {}
        
        # Cache directory for file backup
        if cache_dir:
            self._cache_dir = Path(cache_dir)
        else:
            self._cache_dir = Path(__file__).parent.parent.parent / "cache"
        
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing cache from disk on startup
        self._load_from_disk()
    
    def _get_cache_file(self, key: str) -> Path:
        """Get cache file path for a key."""
        safe_key = key.replace("/", "_").replace(":", "_")
        return self._cache_dir / f"{safe_key}.json"
    
    def _load_from_disk(self):
        """Load all cached data from disk."""
        try:
            for cache_file in self._cache_dir.glob("*.json"):
                try:
                    with open(cache_file, "r") as f:
                        data = json.load(f)
                        key = data.get("key")
                        if key:
                            self._memory_cache[key] = data.get("value")
                            # Parse cached_at and ensure it's timezone-aware
                            cached_at_str = data.get("cached_at", datetime.now(timezone.utc).isoformat())
                            parsed_time = datetime.fromisoformat(cached_at_str)
                            # Ensure timezone-aware (convert naive to UTC)
                            if parsed_time.tzinfo is None:
                                parsed_time = parsed_time.replace(tzinfo=timezone.utc)
                            self._cache_times[key] = parsed_time
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
        except OSError:
            pass
    
    def _save_to_disk(self, key: str, value: Any):
        """Save a cache entry to disk."""
        try:
            cache_file = self._get_cache_file(key)
            with open(cache_file, "w") as f:
                json.dump({
                    "key": key,
                    "value": value,
                    "cached_at": datetime.now(timezone.utc).isoformat()
                }, f)
        except (OSError, TypeError) as e:
            logger.warning(f"Cache write error: {e}")
    
    def get(self, key: str, max_age_seconds: int = 300) -> Optional[Any]:
        """
        Get a value from cache.
        
        Args:
            key: Cache key
            max_age_seconds: Maximum age in seconds (default 5 minutes)
        
        Returns:
            Cached value or None if not found/expired
        """
        if key not in self._memory_cache:
            return None
        
        cache_time = self._cache_times.get(key)
        if cache_time:
            age = (datetime.now(timezone.utc) - cache_time).total_seconds()
            if age > max_age_seconds:
                return None
        
        return self._memory_cache.get(key)
    
    def get_fallback(self, key: str) -> Optional[Any]:
        """
        Get cached value regardless of age (fallback mode).
        Use when API is down and we need any data.
        
        Returns:
            Cached value or None if not found
        """
        return self._memory_cache.get(key)
    
    def get_age(self, key: str) -> Optional[int]:
        """Get age of cached data in seconds."""
        cache_time = self._cache_times.get(key)
        if cache_time:
            return int((datetime.now(timezone.utc) - cache_time).total_seconds())
        return None
    
    def set(self, key: str, value: Any, persist: bool = True):
        """
        Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            persist: Whether to save to disk (default True)
        """
        self._memory_cache[key] = value
        self._cache_times[key] = datetime.now(timezone.utc)
        
        if persist:
            self._save_to_disk(key, value)
    
    def delete(self, key: str):
        """Delete a cache entry."""
        self._memory_cache.pop(key, None)
        self._cache_times.pop(key, None)
        
        cache_file = self._get_cache_file(key)
        if cache_file.exists():
            cache_file.unlink()
    
    def clear(self):
        """Clear all cache."""
        self._memory_cache.clear()
        self._cache_times.clear()
        
        for cache_file in self._cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
            except OSError:
                pass
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        stats = {
            "entries": len(self._memory_cache),
            "keys": list(self._memory_cache.keys()),
            "ages": {}
        }
        
        for key in self._memory_cache:
            age = self.get_age(key)
            if age is not None:
                stats["ages"][key] = f"{age}s ago"
        
        return stats


# Singleton instance
cache = CacheService()

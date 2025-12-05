"""
Polymarket API Client.

Handles communication with Polymarket's CLOB and Gamma APIs.
"""
import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio

from app.core.config import settings


class PolymarketClient:
    """Client for Polymarket APIs."""
    
    def __init__(self):
        self.clob_url = settings.polymarket_api_url
        self.gamma_url = settings.polymarket_gamma_api_url
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    # ========== Markets ==========
    
    async def get_markets(
        self,
        limit: int = 100,
        active: bool = True,
        closed: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Fetch markets from Gamma API.
        
        Args:
            limit: Maximum number of markets
            active: Include active markets
            closed: Include closed markets
            
        Returns:
            List of market data
        """
        client = await self._get_client()
        params = {
            "limit": limit,
            "active": active,
            "closed": closed
        }
        
        try:
            response = await client.get(
                f"{self.gamma_url}/markets",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"Error fetching markets: {e}")
            return []
    
    async def get_market(self, market_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a specific market by ID.
        
        Args:
            market_id: The market's condition ID
            
        Returns:
            Market data or None
        """
        client = await self._get_client()
        
        try:
            response = await client.get(
                f"{self.gamma_url}/markets/{market_id}"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"Error fetching market {market_id}: {e}")
            return None
    
    # ========== Trades ==========
    
    async def get_trades(
        self,
        market_id: Optional[str] = None,
        maker: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent trades.
        
        Args:
            market_id: Filter by market
            maker: Filter by maker address
            limit: Maximum number of trades
            
        Returns:
            List of trade data
        """
        client = await self._get_client()
        params = {"limit": limit}
        
        if market_id:
            params["market"] = market_id
        if maker:
            params["maker"] = maker
        
        try:
            response = await client.get(
                f"{self.clob_url}/trades",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"Error fetching trades: {e}")
            return []
    
    async def get_large_trades(
        self,
        min_size_usd: float = 10000,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Fetch large trades (whale trades).
        
        Args:
            min_size_usd: Minimum trade size in USD
            limit: Maximum number of trades
            
        Returns:
            List of large trades
        """
        # Fetch recent trades and filter by size
        trades = await self.get_trades(limit=limit * 5)
        
        large_trades = []
        for trade in trades:
            try:
                size = float(trade.get("size", 0))
                price = float(trade.get("price", 0))
                value_usd = size * price
                
                if value_usd >= min_size_usd:
                    trade["value_usd"] = value_usd
                    large_trades.append(trade)
                    
                    if len(large_trades) >= limit:
                        break
            except (ValueError, TypeError):
                continue
        
        return large_trades
    
    # ========== Order Book ==========
    
    async def get_order_book(
        self,
        token_id: str
    ) -> Dict[str, Any]:
        """
        Fetch order book for a token.
        
        Args:
            token_id: The token ID
            
        Returns:
            Order book with bids and asks
        """
        client = await self._get_client()
        
        try:
            response = await client.get(
                f"{self.clob_url}/book",
                params={"token_id": token_id}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"Error fetching order book: {e}")
            return {"bids": [], "asks": []}
    
    # ========== Prices ==========
    
    async def get_prices(
        self,
        token_ids: List[str]
    ) -> Dict[str, float]:
        """
        Fetch current prices for tokens.
        
        Args:
            token_ids: List of token IDs
            
        Returns:
            Dict mapping token ID to price
        """
        client = await self._get_client()
        
        try:
            response = await client.get(
                f"{self.clob_url}/prices",
                params={"token_ids": ",".join(token_ids)}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"Error fetching prices: {e}")
            return {}
    
    # ========== Timeseries ==========
    
    async def get_price_history(
        self,
        token_id: str,
        interval: str = "1h",
        fidelity: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Fetch price history for a token.
        
        Args:
            token_id: The token ID
            interval: Time interval
            fidelity: Data point frequency in minutes
            
        Returns:
            List of price points
        """
        client = await self._get_client()
        
        try:
            response = await client.get(
                f"{self.clob_url}/prices-history",
                params={
                    "token_id": token_id,
                    "interval": interval,
                    "fidelity": fidelity
                }
            )
            response.raise_for_status()
            return response.json().get("history", [])
        except httpx.HTTPError as e:
            print(f"Error fetching price history: {e}")
            return []


# Singleton instance
polymarket_client = PolymarketClient()

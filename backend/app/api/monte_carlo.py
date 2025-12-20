"""
Monte Carlo API endpoints for Polymarket Scanner.
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from app.services.monte_carlo.calculator import mc_calculator, EdgeOpportunity
from app.api.signals import fetch_markets, market_to_signal
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


class ProbabilityRequest(BaseModel):
    """Request model for probability calculation."""
    asset: str  # BTC, ETH, SOL
    target_price: float
    end_date: str  # YYYY-MM-DD or YYYY-MM-DD HH:MM:SS


class ProbabilityResponse(BaseModel):
    """Response model for probability calculation."""
    asset: str
    symbol: str
    current_price: float
    target_price: float
    end_date: str
    probability: float
    confidence_low: float
    confidence_high: float
    n_simulations: int
    percentiles: dict


class EdgeResponse(BaseModel):
    """Response model for edge calculation."""
    opportunities: List[dict]
    total: int
    crypto_markets_analyzed: int


@router.post("/probability", response_model=ProbabilityResponse)
async def calculate_probability(request: ProbabilityRequest):
    """
    Calculate Monte Carlo probability for a price target.
    
    - **asset**: Crypto asset code (BTC, ETH, SOL)
    - **target_price**: Target price level
    - **end_date**: End date for simulation (YYYY-MM-DD)
    """
    try:
        result = await mc_calculator.calculate_probability(
            asset=request.asset.upper(),
            target_price=request.target_price,
            end_date=request.end_date,
        )
        return ProbabilityResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")


@router.get("/edge", response_model=EdgeResponse)
async def get_edge_opportunities(
    min_edge: float = Query(default=0.05, ge=0, le=1, description="Minimum edge threshold"),
    limit: int = Query(default=1000, le=5000, description="Maximum opportunities to return"),
):
    """
    Scan Polymarket for edge opportunities using Monte Carlo analysis.
    
    Returns markets where Monte Carlo probability differs significantly
    from Polymarket price.
    """
    try:
        # Fetch all markets
        markets, error, _, _ = await fetch_markets()
        
        if not markets:
            return EdgeResponse(
                opportunities=[],
                total=0,
                crypto_markets_analyzed=0,
            )
        
        opportunities = []
        crypto_count = 0
        
        # Concurrency control
        import asyncio
        semaphore = asyncio.Semaphore(10)  # Max 10 concurrent tasks
        
        async def process_market(market):
            nonlocal crypto_count
            if market.get("closed"):
                return None
            
            # Convert to signal dict
            try:
                signal = market_to_signal(market)
                market_dict = signal.dict()
            except Exception:
                return None
            
            async with semaphore:
                # Calculate edge (this includes heavy simulation + API calls)
                edge_opp = await mc_calculator.calculate_edge(market_dict)
            
            if edge_opp:
                return edge_opp
            return None

        # Gather results with exception handling
        tasks = [process_market(m) for m in markets]
        # return_exceptions=True prevents one failure from crashing the whole request
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for res in results:
            if isinstance(res, Exception):
                logger.warning(f"Error processing market: {res}")
                continue
            if res:
                crypto_count += 1
                if abs(res.edge) >= min_edge:
                    opportunities.append(res.to_dict())
        
        # Sort by absolute edge (highest first)
        opportunities.sort(key=lambda x: abs(x["edge"]), reverse=True)
        
        return EdgeResponse(
            opportunities=opportunities[:limit],
            total=len(opportunities),
            crypto_markets_analyzed=crypto_count,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.critical(f"Error in get_edge_opportunities: {e}")
        raise HTTPException(status_code=500, detail=f"Error scanning markets: {str(e)}")


@router.get("/market/{market_id}")
async def get_market_edge(market_id: str):
    """
    Calculate Monte Carlo edge for a specific market.
    
    - **market_id**: Polymarket market ID
    """
    try:
        # Fetch all markets and find the one we want
        markets, error, _, _ = await fetch_markets()
        
        if not markets:
            raise HTTPException(status_code=404, detail="Could not fetch markets")
        
        # Find market
        market = None
        for m in markets:
            if str(m.get("id")) == market_id or m.get("conditionId") == market_id:
                market = m
                break
        
        if not market:
            raise HTTPException(status_code=404, detail=f"Market {market_id} not found")
        
        # Convert and calculate
        signal = market_to_signal(market)
        edge_opp = await mc_calculator.calculate_edge(signal.dict())
        
        if edge_opp is None:
            raise HTTPException(
                status_code=400,
                detail="This market is not a crypto price market (cannot calculate MC probability)"
            )
        
        return edge_opp.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/assets")
async def get_supported_assets():
    """Get list of supported assets for Monte Carlo analysis."""
    return {
        "assets": [
            {"code": "BTC", "name": "Bitcoin", "symbol": "BTCUSDT"},
            {"code": "ETH", "name": "Ethereum", "symbol": "ETHUSDT"},
            {"code": "SOL", "name": "Solana", "symbol": "SOLUSDT"},
            {"code": "SPX", "name": "S&P 500", "symbol": "^GSPC"},
            {"code": "NDX", "name": "NASDAQ 100", "symbol": "^IXIC"},
            {"code": "GOLD", "name": "Gold", "symbol": "GC=F"},
            {"code": "OIL", "name": "Crude Oil", "symbol": "CL=F"},
        ],
        "note": "Only Polymarket markets about these asset prices can be analyzed with Monte Carlo"
    }

"""
Bootstrap Monte Carlo Option Model.

Based on CryptoRobot's methodology for calculating probabilities
using historical price data and bootstrap resampling.
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple


@dataclass
class SimulationResult:
    """Result of a Monte Carlo simulation."""
    ST: np.ndarray           # Terminal prices (n_sims,)
    S0: float                # Initial spot price
    T: float                 # Time to maturity in years
    n_sims: int              # Number of simulations
    close_paths: Optional[np.ndarray] = None  # (n_sims, n_periods)
    
    def probability_above(self, target: float) -> float:
        """Calculate probability of ending above target price."""
        return float((self.ST >= target).mean())
    
    def probability_below(self, target: float) -> float:
        """Calculate probability of ending below target price."""
        return float((self.ST <= target).mean())
    
    def probability_touch(self, target: float) -> float:
        """Calculate probability of touching target at any point."""
        if self.close_paths is None:
            return self.probability_above(target)
        return float((self.close_paths.max(axis=1) >= target).mean())
    
    def get_percentiles(self, percentiles: list = [5, 25, 50, 75, 95]) -> dict:
        """Get price percentiles from simulation."""
        return {p: float(np.percentile(self.ST, p)) for p in percentiles}


class BootstrapOptionModel:
    """
    Bootstrap Monte Carlo model for price simulation.
    
    Uses historical log-returns resampling (bootstrap) to simulate
    future price paths without assuming a specific distribution.
    """
    
    def __init__(
        self,
        df: pd.DataFrame,
        *,
        col_close: str = "close",
        n_sims: int = 100_000,
        max_reuse: int = 3,
        noise_std: float = 0.0,
        centering: bool = True,
    ):
        """
        Initialize the bootstrap model.
        
        Args:
            df: DataFrame with OHLCV data (must have 'close', 'high', 'low')
            col_close: Name of close price column
            n_sims: Number of simulations to run
            max_reuse: Maximum times each historical return can be reused
            noise_std: Standard deviation of additional noise (0 = no noise)
            centering: Whether to center log-returns on mean
        """
        if col_close not in df.columns:
            raise ValueError(f"Column '{col_close}' not found in DataFrame.")
        if len(df[col_close]) < 2:
            raise ValueError("DataFrame must contain at least 2 data points.")
        
        self.df = df.copy()
        self.col_close = col_close
        self.n_sims = n_sims
        self.max_reuse = max_reuse
        self.noise_std = noise_std
        self.centering = centering
        
        # Pre-compute historical data
        close = self.df[self.col_close].astype(float).to_numpy()
        self.S0 = float(close[-1])  # Current price
        
        # Calculate log-returns
        self.logret_raw = np.diff(np.log(close))
        self.n_returns = len(self.logret_raw)
        
        if self.n_returns == 0:
            raise ValueError("Cannot calculate returns from this sample.")
        
        self.mu_hist = float(self.logret_raw.mean())
        
        # Store high/low factors for path simulation
        if "high" in df.columns and "low" in df.columns:
            high = self.df["high"].astype(float).to_numpy()
            low = self.df["low"].astype(float).to_numpy()
            self.high_factor = high[1:] / close[1:]
            self.low_factor = low[1:] / close[1:]
        else:
            self.high_factor = None
            self.low_factor = None
    
    @staticmethod
    def _sample_indices_with_cap(
        n_returns: int,
        horizon: int,
        max_reuse: int,
        rng: np.random.Generator
    ) -> np.ndarray:
        """Sample indices with maximum reuse cap."""
        pool = np.repeat(np.arange(n_returns), max_reuse)
        if horizon > len(pool):
            # If horizon exceeds pool, sample with replacement
            return rng.choice(n_returns, size=horizon, replace=True)
        return rng.choice(pool, size=horizon, replace=False)
    
    def _compute_horizon(self, end_date: str) -> Tuple[int, float]:
        """
        Compute number of periods until end_date.
        
        Args:
            end_date: Target date in format "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS"
            
        Returns:
            Tuple of (n_periods, T_years)
        """
        # Parse end date
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
            try:
                dt_end = datetime.strptime(end_date, fmt).replace(tzinfo=timezone.utc)
                break
            except ValueError:
                continue
        else:
            raise ValueError(f"Cannot parse date: {end_date}")
        
        now_utc = datetime.now(timezone.utc)
        delta = dt_end - now_utc
        
        # Assume hourly data
        n_periods = int(delta.total_seconds() / 3600)
        
        if n_periods <= 0:
            raise ValueError(f"end_date must be in the future. Got {end_date}")
        
        T_years = n_periods / (365 * 24)
        
        return n_periods, T_years
    
    def simulate(
        self,
        end_date: str,
        *,
        keep_paths: bool = False,
        seed: Optional[int] = None,
        noise_multiplier: float = 1.0,
    ) -> SimulationResult:
        """
        Run Monte Carlo simulation.
        
        Args:
            end_date: Target date
            keep_paths: Store full paths
            seed: Random seed
            noise_multiplier: Multiplier for added noise (e.g. 1.5 for high volatility events)
        """
        n_periods, T_years = self._compute_horizon(end_date)
        rng = np.random.default_rng(seed)
        
        # Prepare log-returns
        if self.centering:
            logret = self.logret_raw - self.mu_hist
        else:
            logret = self.logret_raw
        
        # Sample indices for all simulations
        all_indices = np.zeros((self.n_sims, n_periods), dtype=np.int64)
        for i in range(self.n_sims):
            all_indices[i] = self._sample_indices_with_cap(
                self.n_returns, n_periods, self.max_reuse, rng
            )
        
        # Get sampled returns
        sampled_returns = logret[all_indices]
        
        # Add noise if specified
        if self.noise_std > 0 or noise_multiplier > 1.0:
            # Base noise or minimum noise for multiplier effect
            std = max(self.noise_std, 0.001) * noise_multiplier
            noise = rng.normal(0, std, sampled_returns.shape)
            sampled_returns = sampled_returns + noise
        
        # Compute cumulative returns
        cumsum = np.cumsum(sampled_returns, axis=1)
        
        # Calculate price paths
        close_paths = self.S0 * np.exp(cumsum) if keep_paths else None
        
        # Terminal prices
        ST = self.S0 * np.exp(cumsum[:, -1])
        
        return SimulationResult(
            ST=ST,
            S0=self.S0,
            T=T_years,
            n_sims=self.n_sims,
            close_paths=close_paths,
        )
    
    def probability_above(self, target_price: float, end_date: str, **kwargs) -> float:
        """
        Calculate probability of price being above target at end_date.
        
        Args:
            target_price: Target price level
            end_date: Target date
            **kwargs: Additional arguments for simulate()
            
        Returns:
            Probability as float between 0 and 1
        """
        result = self.simulate(end_date, **kwargs)
        return result.probability_above(target_price)
    
    def probability_touch(self, target_price: float, end_date: str, **kwargs) -> float:
        """
        Calculate probability of price touching target at any point.
        
        Args:
            target_price: Target price level
            end_date: Target date
            **kwargs: Additional arguments for simulate()
            
        Returns:
            Probability as float between 0 and 1
        """
        result = self.simulate(end_date, keep_paths=True, **kwargs)
        return result.probability_touch(target_price)

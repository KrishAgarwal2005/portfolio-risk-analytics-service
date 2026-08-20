"""Pure, DB-free risk calculations.

Every function here operates on numpy/pandas primitives so it can be unit
tested against a hand-rolled NumPy reference implementation without touching
Postgres or Redis.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import norm

TRADING_DAYS_PER_YEAR = 252


def simple_returns(prices: np.ndarray) -> np.ndarray:
    """Day-over-day simple returns for a single price series."""
    prices = np.asarray(prices, dtype=float)
    if prices.size < 2:
        return np.array([], dtype=float)
    return prices[1:] / prices[:-1] - 1.0


def returns_frame(price_wide: pd.DataFrame) -> pd.DataFrame:
    """Convert a wide price frame (index=date, columns=symbol) to aligned returns.

    Rows with any missing symbol observation are dropped so every remaining
    row represents a date where every held asset actually traded.
    """
    return price_wide.sort_index().pct_change().dropna(how="any")


def weighted_portfolio_returns(asset_returns: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Combine a (T, N) return matrix with an (N,) weight vector into a (T,) series."""
    asset_returns = np.atleast_2d(np.asarray(asset_returns, dtype=float))
    weights = np.asarray(weights, dtype=float)
    if asset_returns.size == 0 or weights.size == 0:
        return np.array([], dtype=float)
    return asset_returns @ weights


def historical_var(returns: np.ndarray, confidence: float = 0.95) -> float:
    """Historical-simulation VaR: the loss at the (1 - confidence) empirical quantile.

    Returned as a positive fraction of portfolio value (0 if no losses observed).
    """
    returns = np.asarray(returns, dtype=float)
    if returns.size == 0:
        return 0.0
    loss_quantile = np.percentile(returns, (1 - confidence) * 100)
    return float(max(-loss_quantile, 0.0))


def parametric_var(
    weights: np.ndarray,
    cov_matrix: np.ndarray,
    confidence: float = 0.95,
    mean_returns: np.ndarray | None = None,
) -> float:
    """Variance-covariance (delta-normal) VaR.

    portfolio_std = sqrt(w^T * Sigma * w); VaR = z * portfolio_std - w^T * mean_returns
    Returned as a positive fraction of portfolio value.
    """
    weights = np.asarray(weights, dtype=float)
    cov_matrix = np.atleast_2d(np.asarray(cov_matrix, dtype=float))
    if weights.size == 0 or cov_matrix.size == 0:
        return 0.0

    portfolio_variance = float(weights @ cov_matrix @ weights.T)
    portfolio_std = float(np.sqrt(max(portfolio_variance, 0.0)))
    portfolio_mean = float(weights @ np.asarray(mean_returns, dtype=float)) if mean_returns is not None else 0.0

    z_score = float(norm.ppf(confidence))
    var = z_score * portfolio_std - portfolio_mean
    return float(max(var, 0.0))


def annualized_volatility(returns: np.ndarray, periods_per_year: int = TRADING_DAYS_PER_YEAR) -> float:
    """Sample standard deviation of returns, annualized by sqrt(time)."""
    returns = np.asarray(returns, dtype=float)
    if returns.size < 2:
        return 0.0
    return float(np.std(returns, ddof=1) * np.sqrt(periods_per_year))


def cumulative_returns(returns: np.ndarray) -> np.ndarray:
    returns = np.asarray(returns, dtype=float)
    if returns.size == 0:
        return np.array([], dtype=float)
    return np.cumprod(1.0 + returns)


def max_drawdown(cumulative_values: np.ndarray) -> float:
    """Largest peak-to-trough decline over a cumulative value/return series.

    Returned as a positive fraction (e.g. 0.2 == a 20% drawdown).
    """
    cumulative_values = np.asarray(cumulative_values, dtype=float)
    if cumulative_values.size == 0:
        return 0.0
    running_max = np.maximum.accumulate(cumulative_values)
    drawdowns = (cumulative_values - running_max) / running_max
    return float(-np.min(drawdowns))


@dataclass
class Exposure:
    symbol: str
    quantity: float
    price: float
    market_value: float
    weight: float


def compute_exposures(
    quantities: dict[str, float], latest_prices: dict[str, float]
) -> tuple[list[Exposure], float]:
    """Per-asset market value and weight, plus total portfolio market value."""
    market_values = {
        symbol: quantities[symbol] * latest_prices[symbol]
        for symbol in quantities
        if symbol in latest_prices
    }
    total_value = sum(market_values.values())

    exposures = [
        Exposure(
            symbol=symbol,
            quantity=quantities[symbol],
            price=latest_prices[symbol],
            market_value=value,
            weight=(value / total_value) if total_value else 0.0,
        )
        for symbol, value in market_values.items()
    ]
    return exposures, total_value


@dataclass
class RiskResult:
    portfolio_value: float
    historical_var_pct: float
    historical_var_value: float
    parametric_var_pct: float
    parametric_var_value: float
    annualized_volatility: float
    max_drawdown: float
    exposures: list[Exposure]


def compute_portfolio_risk(
    price_wide: pd.DataFrame,
    quantities: dict[str, float],
    confidence: float = 0.95,
) -> RiskResult:
    """Orchestrate the full risk computation for one portfolio.

    price_wide: DataFrame indexed by date, one column per held symbol, already
    trimmed to the desired lookback window and sorted ascending by date.
    quantities: symbol -> position size (short positions are negative).
    """
    symbols = [s for s in quantities if s in price_wide.columns]
    price_wide = price_wide[symbols].dropna(how="all")

    latest_prices = {
        symbol: float(price_wide[symbol].dropna().iloc[-1])
        for symbol in symbols
        if not price_wide[symbol].dropna().empty
    }
    exposures, portfolio_value = compute_exposures(quantities, latest_prices)

    returns = returns_frame(price_wide)
    weights = np.array([latest_prices.get(s, 0.0) * quantities[s] for s in symbols])
    weights = weights / portfolio_value if portfolio_value else weights

    asset_returns = returns[symbols].to_numpy() if not returns.empty else np.empty((0, len(symbols)))
    portfolio_returns = weighted_portfolio_returns(asset_returns, weights)

    hist_var_pct = historical_var(portfolio_returns, confidence)

    if asset_returns.shape[0] >= 2:
        cov_matrix = np.cov(asset_returns, rowvar=False)
        mean_returns = np.mean(asset_returns, axis=0)
    else:
        cov_matrix = np.zeros((len(symbols), len(symbols)))
        mean_returns = np.zeros(len(symbols))
    param_var_pct = parametric_var(weights, cov_matrix, confidence, mean_returns)

    vol = annualized_volatility(portfolio_returns)
    drawdown = max_drawdown(cumulative_returns(portfolio_returns)) if portfolio_returns.size else 0.0

    return RiskResult(
        portfolio_value=portfolio_value,
        historical_var_pct=hist_var_pct,
        historical_var_value=hist_var_pct * portfolio_value,
        parametric_var_pct=param_var_pct,
        parametric_var_value=param_var_pct * portfolio_value,
        annualized_volatility=vol,
        max_drawdown=drawdown,
        exposures=exposures,
    )

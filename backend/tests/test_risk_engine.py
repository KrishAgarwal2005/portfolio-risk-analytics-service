"""Validate app.services.risk_engine against an independent NumPy reference.

Every reference implementation here is written from the definition of the
metric, deliberately without reusing any helper from app.services.risk_engine,
so a bug shared between "implementation" and "test" can't hide.
"""

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm

from app.services import risk_engine

# ---------------------------------------------------------------------------
# NumPy reference implementations
# ---------------------------------------------------------------------------


def reference_simple_returns(prices: np.ndarray) -> np.ndarray:
    out = []
    for i in range(1, len(prices)):
        out.append(prices[i] / prices[i - 1] - 1.0)
    return np.array(out)


def reference_historical_var(returns: np.ndarray, confidence: float) -> float:
    sorted_returns = np.sort(returns)
    n = len(sorted_returns)
    rank = (1 - confidence) * (n - 1)
    lower = int(np.floor(rank))
    upper = int(np.ceil(rank))
    if lower == upper:
        quantile = sorted_returns[lower]
    else:
        frac = rank - lower
        quantile = sorted_returns[lower] * (1 - frac) + sorted_returns[upper] * frac
    return max(-quantile, 0.0)


def reference_parametric_var(weights: np.ndarray, cov: np.ndarray, confidence: float) -> float:
    variance = 0.0
    n = len(weights)
    for i in range(n):
        for j in range(n):
            variance += weights[i] * weights[j] * cov[i, j]
    std = np.sqrt(variance)
    z = norm.ppf(confidence)
    return max(z * std, 0.0)


def reference_volatility(returns: np.ndarray, periods_per_year: int = 252) -> float:
    mean = np.mean(returns)
    n = len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (n - 1)
    return np.sqrt(variance) * np.sqrt(periods_per_year)


def reference_max_drawdown(cumulative: np.ndarray) -> float:
    peak = cumulative[0]
    worst = 0.0
    for value in cumulative:
        peak = max(peak, value)
        drawdown = (value - peak) / peak
        worst = min(worst, drawdown)
    return -worst


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def rng() -> np.random.Generator:
    return np.random.default_rng(seed=42)


@pytest.fixture
def price_series(rng: np.random.Generator) -> np.ndarray:
    daily_returns = rng.normal(loc=0.0003, scale=0.015, size=500)
    return 100 * np.cumprod(1 + daily_returns)


# ---------------------------------------------------------------------------
# simple_returns
# ---------------------------------------------------------------------------


def test_simple_returns_matches_reference(price_series: np.ndarray) -> None:
    expected = reference_simple_returns(price_series)
    actual = risk_engine.simple_returns(price_series)
    np.testing.assert_allclose(actual, expected, rtol=1e-10)


def test_simple_returns_empty_for_single_price() -> None:
    assert risk_engine.simple_returns(np.array([100.0])).size == 0


def test_simple_returns_empty_for_no_prices() -> None:
    assert risk_engine.simple_returns(np.array([])).size == 0


# ---------------------------------------------------------------------------
# historical_var
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("confidence", [0.90, 0.95, 0.99])
def test_historical_var_matches_reference(price_series: np.ndarray, confidence: float) -> None:
    returns = risk_engine.simple_returns(price_series)
    expected = reference_historical_var(returns, confidence)
    actual = risk_engine.historical_var(returns, confidence)
    assert actual == pytest.approx(expected, rel=1e-9)


def test_historical_var_is_zero_for_all_positive_returns() -> None:
    returns = np.array([0.01, 0.02, 0.03, 0.015])
    assert risk_engine.historical_var(returns, confidence=0.95) == 0.0


def test_historical_var_empty_returns_is_zero() -> None:
    assert risk_engine.historical_var(np.array([]), confidence=0.95) == 0.0


# ---------------------------------------------------------------------------
# parametric_var
# ---------------------------------------------------------------------------


def test_parametric_var_matches_reference_multi_asset(rng: np.random.Generator) -> None:
    n_assets = 4
    weights = rng.dirichlet(np.ones(n_assets))
    a = rng.normal(size=(n_assets, n_assets))
    cov = a @ a.T * 1e-4  # guaranteed positive semi-definite covariance matrix

    expected = reference_parametric_var(weights, cov, confidence=0.99)
    actual = risk_engine.parametric_var(weights, cov, confidence=0.99)
    assert actual == pytest.approx(expected, rel=1e-9)


def test_parametric_var_single_asset_matches_reference() -> None:
    weights = np.array([1.0])
    cov = np.array([[0.0004]])  # 2% daily vol squared
    expected = reference_parametric_var(weights, cov, confidence=0.95)
    actual = risk_engine.parametric_var(weights, cov, confidence=0.95)
    assert actual == pytest.approx(expected, rel=1e-9)


def test_parametric_var_subtracts_positive_mean_drift() -> None:
    weights = np.array([1.0])
    cov = np.array([[0.0001]])
    mean = np.array([0.05])  # large positive drift should reduce/zero out VaR
    var = risk_engine.parametric_var(weights, cov, confidence=0.95, mean_returns=mean)
    assert var == 0.0


def test_parametric_var_empty_weights_is_zero() -> None:
    assert risk_engine.parametric_var(np.array([]), np.array([]), confidence=0.95) == 0.0


# ---------------------------------------------------------------------------
# annualized_volatility
# ---------------------------------------------------------------------------


def test_annualized_volatility_matches_reference(price_series: np.ndarray) -> None:
    returns = risk_engine.simple_returns(price_series)
    expected = reference_volatility(returns)
    actual = risk_engine.annualized_volatility(returns)
    assert actual == pytest.approx(expected, rel=1e-9)


def test_annualized_volatility_needs_at_least_two_points() -> None:
    assert risk_engine.annualized_volatility(np.array([0.01])) == 0.0
    assert risk_engine.annualized_volatility(np.array([])) == 0.0


# ---------------------------------------------------------------------------
# max_drawdown
# ---------------------------------------------------------------------------


def test_max_drawdown_matches_reference(price_series: np.ndarray) -> None:
    returns = risk_engine.simple_returns(price_series)
    cumulative = risk_engine.cumulative_returns(returns)
    expected = reference_max_drawdown(cumulative)
    actual = risk_engine.max_drawdown(cumulative)
    assert actual == pytest.approx(expected, rel=1e-9)


def test_max_drawdown_known_sequence() -> None:
    # 100 -> 120 -> 90 -> 110: peak 120, trough 90 => 25% drawdown
    cumulative = np.array([1.0, 1.2, 0.9, 1.1])
    assert risk_engine.max_drawdown(cumulative) == pytest.approx(0.25, rel=1e-9)


def test_max_drawdown_monotonic_up_is_zero() -> None:
    cumulative = np.array([1.0, 1.05, 1.10, 1.20])
    assert risk_engine.max_drawdown(cumulative) == pytest.approx(0.0, abs=1e-12)


def test_max_drawdown_empty_is_zero() -> None:
    assert risk_engine.max_drawdown(np.array([])) == 0.0


# ---------------------------------------------------------------------------
# compute_exposures
# ---------------------------------------------------------------------------


def test_compute_exposures_weights_sum_to_one() -> None:
    quantities = {"AAPL": 10, "MSFT": 5, "GOOG": 2}
    prices = {"AAPL": 190.0, "MSFT": 420.0, "GOOG": 175.0}
    exposures, total_value = risk_engine.compute_exposures(quantities, prices)

    assert total_value == pytest.approx(10 * 190 + 5 * 420 + 2 * 175)
    assert sum(e.weight for e in exposures) == pytest.approx(1.0)


def test_compute_exposures_single_asset_book() -> None:
    exposures, total_value = risk_engine.compute_exposures({"AAPL": 100}, {"AAPL": 200.0})
    assert total_value == pytest.approx(20000.0)
    assert len(exposures) == 1
    assert exposures[0].weight == pytest.approx(1.0)


def test_compute_exposures_missing_price_is_skipped() -> None:
    exposures, total_value = risk_engine.compute_exposures(
        {"AAPL": 10, "UNKNOWN": 5}, {"AAPL": 100.0}
    )
    assert len(exposures) == 1
    assert exposures[0].symbol == "AAPL"


# ---------------------------------------------------------------------------
# compute_portfolio_risk -- integration of the pieces above, edge cases
# ---------------------------------------------------------------------------


def _price_frame(dates: pd.DatetimeIndex, data: dict[str, list[float]]) -> pd.DataFrame:
    return pd.DataFrame(data, index=dates)


def test_compute_portfolio_risk_single_asset_book(rng: np.random.Generator) -> None:
    dates = pd.date_range("2024-01-01", periods=260, freq="B")
    prices = 100 * np.cumprod(1 + rng.normal(0.0002, 0.01, size=260))
    price_wide = _price_frame(dates, {"AAPL": prices})

    result = risk_engine.compute_portfolio_risk(price_wide, {"AAPL": 50}, confidence=0.95)

    assert result.portfolio_value == pytest.approx(50 * prices[-1])
    assert len(result.exposures) == 1
    assert result.exposures[0].weight == pytest.approx(1.0)
    assert result.historical_var_pct >= 0
    assert result.parametric_var_pct >= 0
    assert result.annualized_volatility >= 0
    assert result.max_drawdown >= 0


def test_compute_portfolio_risk_multi_asset_book(rng: np.random.Generator) -> None:
    dates = pd.date_range("2024-01-01", periods=260, freq="B")
    aapl = 100 * np.cumprod(1 + rng.normal(0.0002, 0.01, size=260))
    msft = 300 * np.cumprod(1 + rng.normal(0.0001, 0.012, size=260))
    price_wide = _price_frame(dates, {"AAPL": aapl, "MSFT": msft})

    result = risk_engine.compute_portfolio_risk(
        price_wide, {"AAPL": 20, "MSFT": 10}, confidence=0.99
    )

    assert result.portfolio_value == pytest.approx(20 * aapl[-1] + 10 * msft[-1])
    assert {e.symbol for e in result.exposures} == {"AAPL", "MSFT"}
    assert sum(e.weight for e in result.exposures) == pytest.approx(1.0)


def test_compute_portfolio_risk_sparse_history_does_not_crash() -> None:
    dates = pd.date_range("2024-01-01", periods=3, freq="B")
    price_wide = _price_frame(dates, {"AAPL": [100.0, 101.0, 99.5]})

    result = risk_engine.compute_portfolio_risk(price_wide, {"AAPL": 10}, confidence=0.95)

    assert result.portfolio_value == pytest.approx(995.0)
    assert result.historical_var_pct >= 0
    assert result.parametric_var_pct >= 0


def test_compute_portfolio_risk_single_price_point() -> None:
    dates = pd.date_range("2024-01-01", periods=1, freq="B")
    price_wide = _price_frame(dates, {"AAPL": [100.0]})

    result = risk_engine.compute_portfolio_risk(price_wide, {"AAPL": 10}, confidence=0.95)

    assert result.portfolio_value == pytest.approx(1000.0)
    assert result.historical_var_pct == 0.0
    assert result.annualized_volatility == 0.0
    assert result.max_drawdown == 0.0


def test_compute_portfolio_risk_empty_price_history() -> None:
    price_wide = pd.DataFrame()
    result = risk_engine.compute_portfolio_risk(price_wide, {"AAPL": 10}, confidence=0.95)

    assert result.portfolio_value == 0.0
    assert result.exposures == []
    assert result.historical_var_pct == 0.0

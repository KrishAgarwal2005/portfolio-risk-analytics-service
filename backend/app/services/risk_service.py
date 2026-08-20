from datetime import date, timedelta

import redis
from sqlalchemy.orm import Session

from app.crud.price_history import get_latest_price_date, get_price_history_wide
from app.models.portfolio import Portfolio
from app.schemas.risk import AssetExposure, RiskMetrics
from app.services.cache import get_cached_risk, risk_cache_key, set_cached_risk
from app.services.risk_engine import compute_portfolio_risk


def get_portfolio_risk(
    db: Session,
    redis_client: redis.Redis,
    portfolio: Portfolio,
    as_of_date: date | None,
    confidence: float,
    lookback_days: int,
) -> RiskMetrics:
    symbols = [position.symbol for position in portfolio.positions]
    quantities = {position.symbol: float(position.quantity) for position in portfolio.positions}

    resolved_date = as_of_date or get_latest_price_date(db, symbols)
    if resolved_date is None:
        return RiskMetrics(
            portfolio_id=portfolio.id,
            as_of_date=as_of_date or date.today(),
            confidence=confidence,
            lookback_days=lookback_days,
            portfolio_value=0.0,
            historical_var_pct=0.0,
            historical_var_value=0.0,
            parametric_var_pct=0.0,
            parametric_var_value=0.0,
            annualized_volatility=0.0,
            max_drawdown=0.0,
            exposures=[],
            cached=False,
        )

    cache_key = risk_cache_key(portfolio.id, resolved_date, confidence, lookback_days)
    cached = get_cached_risk(redis_client, cache_key)
    if cached is not None:
        return RiskMetrics(**cached, cached=True)

    start_date = resolved_date - timedelta(days=int(lookback_days * 1.6) + 10)
    price_wide = get_price_history_wide(db, symbols, start_date, resolved_date)

    result = compute_portfolio_risk(price_wide, quantities, confidence)

    metrics = RiskMetrics(
        portfolio_id=portfolio.id,
        as_of_date=resolved_date,
        confidence=confidence,
        lookback_days=lookback_days,
        portfolio_value=result.portfolio_value,
        historical_var_pct=result.historical_var_pct,
        historical_var_value=result.historical_var_value,
        parametric_var_pct=result.parametric_var_pct,
        parametric_var_value=result.parametric_var_value,
        annualized_volatility=result.annualized_volatility,
        max_drawdown=result.max_drawdown,
        exposures=[
            AssetExposure(
                symbol=e.symbol,
                quantity=e.quantity,
                price=e.price,
                market_value=e.market_value,
                weight=e.weight,
            )
            for e in result.exposures
        ],
        cached=False,
    )

    set_cached_risk(redis_client, cache_key, metrics.model_dump(mode="json", exclude={"cached"}))
    return metrics

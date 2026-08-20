from datetime import date

import redis
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.crud.portfolio import get_portfolio
from app.database import get_db
from app.models.user import User
from app.redis_client import get_redis_client
from app.schemas.risk import RiskMetrics
from app.services.risk_service import get_portfolio_risk

router = APIRouter(prefix="/portfolios/{portfolio_id}/risk", tags=["risk"])


@router.get("", response_model=RiskMetrics)
def compute_risk(
    portfolio_id: int,
    as_of_date: date | None = Query(default=None, description="Defaults to latest priced date"),
    confidence: float = Query(default=0.95, gt=0, lt=1),
    lookback_days: int = Query(default=252, ge=2, le=2000),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
    user: User = Depends(get_current_user),
) -> RiskMetrics:
    """Historical VaR, parametric VaR, annualized volatility, max drawdown and
    per-asset exposure for a portfolio as of a given date.

    Results are cached in Redis keyed by (portfolio, as-of date, confidence,
    lookback) so repeat requests for an already-computed day skip both the
    Postgres price-history scan and the NumPy computation.
    """
    portfolio = get_portfolio(db, portfolio_id, user.id)
    if portfolio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    return get_portfolio_risk(db, redis_client, portfolio, as_of_date, confidence, lookback_days)

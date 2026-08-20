from datetime import date

from pydantic import BaseModel, Field


class AssetExposure(BaseModel):
    symbol: str
    quantity: float
    price: float
    market_value: float
    weight: float = Field(description="Fraction of total portfolio market value")


class RiskQuery(BaseModel):
    as_of_date: date | None = Field(
        default=None, description="Defaults to the latest available price date"
    )
    confidence: float = Field(default=0.95, gt=0, lt=1)
    lookback_days: int = Field(default=252, ge=2, le=2000)


class RiskMetrics(BaseModel):
    portfolio_id: int
    as_of_date: date
    confidence: float
    lookback_days: int
    portfolio_value: float
    historical_var_pct: float = Field(description="Loss as a fraction of portfolio value")
    historical_var_value: float = Field(description="Loss in base currency")
    parametric_var_pct: float
    parametric_var_value: float
    annualized_volatility: float
    max_drawdown: float
    exposures: list[AssetExposure]
    cached: bool = False

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PositionCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    quantity: float
    avg_cost: float = Field(ge=0)


class PositionUpdate(BaseModel):
    quantity: float | None = None
    avg_cost: float | None = Field(default=None, ge=0)


class PositionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    portfolio_id: int
    symbol: str
    quantity: float
    avg_cost: float
    created_at: datetime

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.position import PositionRead


class PortfolioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    base_currency: str = Field(default="USD", min_length=3, max_length=3)


class PortfolioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    name: str
    base_currency: str
    created_at: datetime


class PortfolioDetail(PortfolioRead):
    positions: list[PositionRead] = []

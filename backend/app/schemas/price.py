from datetime import date

from pydantic import BaseModel, Field


class PricePoint(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    price_date: date
    close_price: float = Field(gt=0)


class PriceBulkUpsert(BaseModel):
    prices: list[PricePoint]

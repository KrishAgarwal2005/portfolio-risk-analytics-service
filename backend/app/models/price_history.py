from datetime import date as date_

from sqlalchemy import Date, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PriceHistory(Base):
    """Daily close prices per symbol.

    The composite (symbol, price_date) index backs the time-range queries the
    risk engine issues when it pulls a lookback window of prices for a symbol.
    """

    __tablename__ = "price_history"
    __table_args__ = (
        UniqueConstraint("symbol", "price_date", name="uq_price_symbol_date"),
        Index("ix_price_history_symbol_date", "symbol", "price_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    price_date: Mapped[date_] = mapped_column(Date, nullable=False)
    close_price: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)

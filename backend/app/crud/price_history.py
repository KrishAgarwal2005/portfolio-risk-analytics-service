from datetime import date

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.price_history import PriceHistory


def upsert_price(db: Session, symbol: str, price_date: date, close_price: float) -> PriceHistory:
    existing = (
        db.query(PriceHistory)
        .filter(PriceHistory.symbol == symbol, PriceHistory.price_date == price_date)
        .first()
    )
    if existing:
        existing.close_price = close_price
        db.commit()
        db.refresh(existing)
        return existing

    row = PriceHistory(symbol=symbol, price_date=price_date, close_price=close_price)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_price_history_wide(
    db: Session, symbols: list[str], start_date: date, end_date: date
) -> pd.DataFrame:
    """Fetch close prices for `symbols` within [start_date, end_date] and pivot to wide form.

    Backed by the composite (symbol, price_date) index on price_history, so this
    is a single index range scan per symbol rather than a full table scan.
    """
    if not symbols:
        return pd.DataFrame()

    stmt = (
        select(PriceHistory.symbol, PriceHistory.price_date, PriceHistory.close_price)
        .where(
            PriceHistory.symbol.in_(symbols),
            PriceHistory.price_date >= start_date,
            PriceHistory.price_date <= end_date,
        )
        .order_by(PriceHistory.price_date)
    )
    rows = db.execute(stmt).all()
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=["symbol", "price_date", "close_price"])
    df["close_price"] = df["close_price"].astype(float)
    wide = df.pivot(index="price_date", columns="symbol", values="close_price")
    wide.index = pd.to_datetime(wide.index)
    return wide.sort_index()


def get_latest_price_date(db: Session, symbols: list[str]) -> date | None:
    if not symbols:
        return None
    stmt = select(PriceHistory.price_date).where(PriceHistory.symbol.in_(symbols)).order_by(
        PriceHistory.price_date.desc()
    ).limit(1)
    result = db.execute(stmt).first()
    return result[0] if result else None

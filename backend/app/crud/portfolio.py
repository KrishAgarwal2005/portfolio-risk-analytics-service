from sqlalchemy.orm import Session

from app.models.portfolio import Portfolio
from app.schemas.portfolio import PortfolioCreate


def create_portfolio(db: Session, owner_id: int, portfolio_in: PortfolioCreate) -> Portfolio:
    portfolio = Portfolio(owner_id=owner_id, name=portfolio_in.name, base_currency=portfolio_in.base_currency)
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio


def list_portfolios(db: Session, owner_id: int) -> list[Portfolio]:
    return db.query(Portfolio).filter(Portfolio.owner_id == owner_id).order_by(Portfolio.id).all()


def get_portfolio(db: Session, portfolio_id: int, owner_id: int) -> Portfolio | None:
    return (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.owner_id == owner_id)
        .first()
    )


def delete_portfolio(db: Session, portfolio: Portfolio) -> None:
    db.delete(portfolio)
    db.commit()

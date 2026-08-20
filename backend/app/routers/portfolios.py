from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.crud.portfolio import create_portfolio, delete_portfolio, get_portfolio, list_portfolios
from app.database import get_db
from app.models.user import User
from app.schemas.portfolio import PortfolioCreate, PortfolioDetail, PortfolioRead

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


def _get_owned_portfolio(db: Session, portfolio_id: int, user: User):
    portfolio = get_portfolio(db, portfolio_id, user.id)
    if portfolio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    return portfolio


@router.post("", response_model=PortfolioRead, status_code=status.HTTP_201_CREATED)
def create(
    portfolio_in: PortfolioCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PortfolioRead:
    return create_portfolio(db, user.id, portfolio_in)


@router.get("", response_model=list[PortfolioRead])
def list_all(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[PortfolioRead]:
    return list_portfolios(db, user.id)


@router.get("/{portfolio_id}", response_model=PortfolioDetail)
def get_one(
    portfolio_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> PortfolioDetail:
    return _get_owned_portfolio(db, portfolio_id, user)


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    portfolio_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    portfolio = _get_owned_portfolio(db, portfolio_id, user)
    delete_portfolio(db, portfolio)

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.crud.portfolio import get_portfolio
from app.crud.position import (
    create_position,
    delete_position,
    get_position,
    list_positions,
    update_position,
)
from app.database import get_db
from app.models.user import User
from app.schemas.position import PositionCreate, PositionRead, PositionUpdate

router = APIRouter(prefix="/portfolios/{portfolio_id}/positions", tags=["positions"])


def _get_owned_portfolio(db: Session, portfolio_id: int, user: User):
    portfolio = get_portfolio(db, portfolio_id, user.id)
    if portfolio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    return portfolio


@router.post("", response_model=PositionRead, status_code=status.HTTP_201_CREATED)
def create(
    portfolio_id: int,
    position_in: PositionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PositionRead:
    _get_owned_portfolio(db, portfolio_id, user)
    return create_position(db, portfolio_id, position_in)


@router.get("", response_model=list[PositionRead])
def list_all(
    portfolio_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[PositionRead]:
    _get_owned_portfolio(db, portfolio_id, user)
    return list_positions(db, portfolio_id)


@router.patch("/{position_id}", response_model=PositionRead)
def update(
    portfolio_id: int,
    position_id: int,
    position_in: PositionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PositionRead:
    _get_owned_portfolio(db, portfolio_id, user)
    position = get_position(db, position_id, portfolio_id)
    if position is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
    return update_position(db, position, position_in)


@router.delete("/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    portfolio_id: int,
    position_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    _get_owned_portfolio(db, portfolio_id, user)
    position = get_position(db, position_id, portfolio_id)
    if position is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
    delete_position(db, position)

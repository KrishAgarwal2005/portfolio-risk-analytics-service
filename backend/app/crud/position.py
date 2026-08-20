from sqlalchemy.orm import Session

from app.models.position import Position
from app.schemas.position import PositionCreate, PositionUpdate


def create_position(db: Session, portfolio_id: int, position_in: PositionCreate) -> Position:
    position = Position(
        portfolio_id=portfolio_id,
        symbol=position_in.symbol.upper(),
        quantity=position_in.quantity,
        avg_cost=position_in.avg_cost,
    )
    db.add(position)
    db.commit()
    db.refresh(position)
    return position


def list_positions(db: Session, portfolio_id: int) -> list[Position]:
    return db.query(Position).filter(Position.portfolio_id == portfolio_id).order_by(Position.id).all()


def get_position(db: Session, position_id: int, portfolio_id: int) -> Position | None:
    return (
        db.query(Position)
        .filter(Position.id == position_id, Position.portfolio_id == portfolio_id)
        .first()
    )


def update_position(db: Session, position: Position, position_in: PositionUpdate) -> Position:
    if position_in.quantity is not None:
        position.quantity = position_in.quantity
    if position_in.avg_cost is not None:
        position.avg_cost = position_in.avg_cost
    db.commit()
    db.refresh(position)
    return position


def delete_position(db: Session, position: Position) -> None:
    db.delete(position)
    db.commit()

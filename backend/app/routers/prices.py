from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.crud.price_history import upsert_price
from app.database import get_db
from app.models.user import User
from app.schemas.price import PriceBulkUpsert

router = APIRouter(prefix="/prices", tags=["prices"])


@router.post("", status_code=status.HTTP_204_NO_CONTENT)
def bulk_upsert(
    payload: PriceBulkUpsert,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Load/refresh daily close prices. Any authenticated user may contribute
    market data since price history is shared reference data, not per-user."""
    for point in payload.prices:
        upsert_price(db, point.symbol.upper(), point.price_date, point.close_price)

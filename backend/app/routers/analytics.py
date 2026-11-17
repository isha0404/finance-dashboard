from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Transaction, User
from app.schemas import CategoryTotal, MonthlyPoint, Summary
from app.security import get_current_user
from app.services import analytics

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

MONTH_PATTERN = r"^\d{4}-\d{2}$"


def _user_transactions(db: Session, user: User) -> list[Transaction]:
    return list(db.scalars(select(Transaction).where(Transaction.user_id == user.id)))


def _latest_month(txs: list[Transaction]) -> str:
    """Default to the most recent month that has data, so imported history shows up straight away."""
    return analytics.month_key(max(t.date for t in txs)) if txs else analytics.month_key(date.today())


@router.get("/summary", response_model=Summary)
def summary(
    month: str | None = Query(None, pattern=MONTH_PATTERN),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Summary:
    txs = _user_transactions(db, user)
    data = analytics.summarise(txs, month or _latest_month(txs))
    return Summary(**data.__dict__)


@router.get("/monthly", response_model=list[MonthlyPoint])
def monthly(
    months: int = Query(6, ge=1, le=24),
    end: str | None = Query(None, pattern=MONTH_PATTERN),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    txs = _user_transactions(db, user)
    end_key = end or _latest_month(txs)
    y, m = map(int, end_key.split("-"))
    return analytics.monthly_totals(txs, analytics.previous_months(date(y, m, 1), months))


@router.get("/by-category", response_model=list[CategoryTotal])
def by_category(
    month: str | None = Query(None, pattern=MONTH_PATTERN),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    txs = _user_transactions(db, user)
    return analytics.spending_by_category(txs, month or _latest_month(txs))

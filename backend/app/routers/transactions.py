from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import extract, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Transaction, User
from app.schemas import ImportResult, TransactionCreate, TransactionOut, TransactionUpdate
from app.security import get_current_user
from app.services.categoriser import CATEGORIES, categorise
from app.services.csv_import import CSVFormatError, fingerprint, parse_csv

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def _get_owned(db: Session, user: User, tx_id: int) -> Transaction:
    """Fetch a transaction, but only if it belongs to the current user.

    Returning 404 (not 403) for other users' records avoids revealing that the ID exists.
    """
    tx = db.get(Transaction, tx_id)
    if tx is None or tx.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transaction not found")
    return tx


def _commit_or_conflict(db: Session) -> None:
    """Commit, turning a duplicate-fingerprint violation into a friendly 409."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "An identical transaction already exists") from None


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$", description="YYYY-MM"),
    category: str | None = None,
    q: str | None = Query(None, max_length=100, description="Search in description"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Transaction]:
    stmt = select(Transaction).where(Transaction.user_id == user.id)
    if month:
        year, mon = map(int, month.split("-"))
        stmt = stmt.where(extract("year", Transaction.date) == year, extract("month", Transaction.date) == mon)
    if category:
        stmt = stmt.where(Transaction.category == category)
    if q:
        # Bound parameter, so this is safe from SQL injection.
        stmt = stmt.where(Transaction.description.ilike(f"%{q}%"))
    stmt = stmt.order_by(Transaction.date.desc(), Transaction.id.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt))


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    body: TransactionCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Transaction:
    if body.amount == 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Amount can't be zero")
    tx = Transaction(
        user_id=user.id,
        date=body.date,
        description=body.description.strip(),
        amount=body.amount,
        category=body.category or categorise(body.description, body.amount),
        fingerprint=fingerprint(user.id, body.date, body.description, body.amount),
    )
    db.add(tx)
    _commit_or_conflict(db)
    db.refresh(tx)
    return tx


@router.put("/{tx_id}", response_model=TransactionOut)
def update_transaction(
    tx_id: int, body: TransactionUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Transaction:
    tx = _get_owned(db, user, tx_id)
    tx.date = body.date
    tx.description = body.description.strip()
    tx.amount = body.amount
    tx.category = body.category or categorise(body.description, body.amount)
    tx.fingerprint = fingerprint(user.id, body.date, body.description, body.amount)
    _commit_or_conflict(db)
    db.refresh(tx)
    return tx


@router.delete("/{tx_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(tx_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    db.delete(_get_owned(db, user, tx_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/import", response_model=ImportResult)
async def import_csv(
    file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ImportResult:
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Please upload a .csv file")

    # Read one byte past the limit so we can tell if the file is too big without loading all of it.
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File is larger than 2 MB")

    try:
        parsed = parse_csv(content, max_rows=settings.max_import_rows)
    except CSVFormatError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from None

    existing = set(db.scalars(select(Transaction.fingerprint).where(Transaction.user_id == user.id)))
    imported = skipped = 0
    for row in parsed.rows:
        fp = fingerprint(user.id, row.date, row.description, row.amount)
        if fp in existing:
            skipped += 1
            continue
        existing.add(fp)
        category = row.category if row.category in CATEGORIES else categorise(row.description, row.amount)
        db.add(Transaction(
            user_id=user.id, date=row.date, description=row.description,
            amount=row.amount, category=category, fingerprint=fp,
        ))
        imported += 1
    db.commit()
    return ImportResult(imported=imported, skipped_duplicates=skipped, errors=parsed.errors[:50])


@router.get("/categories", response_model=list[str], tags=["transactions"])
def list_categories() -> list[str]:
    return CATEGORIES


# Defined after the routes above so "/categories" isn't captured by "/{tx_id}".
@router.get("/{tx_id}", response_model=TransactionOut)
def get_transaction(tx_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Transaction:
    return _get_owned(db, user, tx_id)


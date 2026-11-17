"""Request and response shapes (validated by Pydantic)."""
import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.services.categoriser import CATEGORIES


# ---------- auth ----------
class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    name: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- transactions ----------
class TransactionBase(BaseModel):
    date: dt.date
    description: str = Field(min_length=1, max_length=255)
    amount: Decimal = Field(max_digits=12, decimal_places=2)
    category: str | None = None  # auto-detected when left empty

    @field_validator("category")
    @classmethod
    def category_must_be_known(cls, v: str | None) -> str | None:
        if v is not None and v not in CATEGORIES:
            raise ValueError(f"Unknown category. Choose one of: {', '.join(CATEGORIES)}")
        return v


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(TransactionBase):
    pass


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date: dt.date
    description: str
    amount: Decimal
    category: str


class ImportResult(BaseModel):
    imported: int
    skipped_duplicates: int
    errors: list[str]


# ---------- analytics ----------
class Summary(BaseModel):
    month: str
    income: Decimal
    spending: Decimal
    net: Decimal
    savings_rate: float  # percentage of income kept, 0 when there is no income
    top_category: str | None
    transaction_count: int


class MonthlyPoint(BaseModel):
    month: str
    income: Decimal
    spending: Decimal


class CategoryTotal(BaseModel):
    category: str
    total: Decimal

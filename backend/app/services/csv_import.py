"""Parse bank-statement CSVs into clean transaction rows.

Banks export CSVs in different shapes, so the parser is forgiving:
- header names are matched case-insensitively against common aliases
- either one signed "amount" column, or separate "money in" / "money out" columns
- UK (DD/MM/YYYY) and ISO (YYYY-MM-DD) dates, plus a few others
- currency symbols and thousands separators are stripped

Every bad row is reported back with its line number instead of failing the whole file.
"""
import csv
import hashlib
import io
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

DATE_ALIASES = {"date", "transaction date", "posted date", "booking date"}
DESC_ALIASES = {"description", "merchant", "name", "details", "payee", "reference", "narrative"}
AMOUNT_ALIASES = {"amount", "value", "amount (gbp)", "amount(gbp)"}
IN_ALIASES = {"money in", "paid in", "credit", "credit amount", "in"}
OUT_ALIASES = {"money out", "paid out", "debit", "debit amount", "out"}
CATEGORY_ALIASES = {"category"}

DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d %b %Y", "%d %B %Y")


class CSVFormatError(ValueError):
    """The file as a whole can't be read (e.g. missing required columns)."""


@dataclass(frozen=True)
class ParsedRow:
    date: date
    description: str
    amount: Decimal
    category: str | None  # only set if the CSV supplied one


@dataclass
class ParseResult:
    rows: list[ParsedRow]
    errors: list[str]


def parse_date(value: str) -> date:
    value = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date '{value}'")


def parse_amount(value: str) -> Decimal:
    cleaned = value.strip().replace("£", "").replace("$", "").replace("€", "").replace(",", "").replace(" ", "")
    if cleaned.startswith("(") and cleaned.endswith(")"):  # accounting style negatives: (12.50)
        cleaned = "-" + cleaned[1:-1]
    if cleaned == "":
        return Decimal("0")
    try:
        return Decimal(cleaned).quantize(Decimal("0.01"))
    except InvalidOperation:
        raise ValueError(f"invalid amount '{value}'") from None


def _find(headers: dict[str, str], aliases: set[str]) -> str | None:
    for normalised, original in headers.items():
        if normalised in aliases:
            return original
    return None


def parse_csv(content: bytes, max_rows: int = 5000) -> ParseResult:
    try:
        text = content.decode("utf-8-sig")  # strips the BOM Excel likes to add
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise CSVFormatError("The file is empty or has no header row.")

    headers = {h.strip().lower(): h for h in reader.fieldnames if h}
    date_col = _find(headers, DATE_ALIASES)
    desc_col = _find(headers, DESC_ALIASES)
    amount_col = _find(headers, AMOUNT_ALIASES)
    in_col = _find(headers, IN_ALIASES)
    out_col = _find(headers, OUT_ALIASES)
    cat_col = _find(headers, CATEGORY_ALIASES)

    if not date_col or not desc_col:
        raise CSVFormatError("CSV needs a date column and a description column.")
    if not amount_col and not (in_col or out_col):
        raise CSVFormatError("CSV needs an 'amount' column, or 'money in' / 'money out' columns.")

    rows: list[ParsedRow] = []
    errors: list[str] = []

    for line_no, raw in enumerate(reader, start=2):  # line 1 is the header
        if len(rows) >= max_rows:
            errors.append(f"Stopped after {max_rows} rows (limit).")
            break
        if not any((v or "").strip() for v in raw.values()):
            continue  # blank line
        try:
            d = parse_date(raw.get(date_col) or "")
            desc = (raw.get(desc_col) or "").strip()[:255]
            if not desc:
                raise ValueError("missing description")
            if amount_col:
                amount = parse_amount(raw.get(amount_col) or "")
            else:
                money_in = parse_amount(raw.get(in_col) or "") if in_col else Decimal("0")
                money_out = parse_amount(raw.get(out_col) or "") if out_col else Decimal("0")
                amount = abs(money_in) - abs(money_out)
            if amount == 0:
                raise ValueError("amount is zero")
            category = None
            if cat_col:
                category = (raw.get(cat_col) or "").strip() or None
            rows.append(ParsedRow(d, desc, amount, category))
        except ValueError as exc:
            errors.append(f"Line {line_no}: {exc}")

    return ParseResult(rows=rows, errors=errors)


def fingerprint(user_id: int, d: date, description: str, amount: Decimal) -> str:
    """Stable hash used to detect duplicate imports."""
    key = f"{user_id}|{d.isoformat()}|{description.strip().lower()}|{amount:.2f}"
    return hashlib.sha256(key.encode()).hexdigest()

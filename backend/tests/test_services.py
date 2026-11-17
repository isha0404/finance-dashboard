"""Unit tests for the pure business logic (no database or web server needed)."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pytest

from app.services.analytics import monthly_totals, previous_months, spending_by_category, summarise
from app.services.categoriser import categorise
from app.services.csv_import import CSVFormatError, fingerprint, parse_amount, parse_csv, parse_date


# ---------- categoriser ----------
@pytest.mark.parametrize(
    "description,amount,expected",
    [
        ("TESCO STORES 2231", "-23.40", "Groceries"),
        ("TfL Travel Charge", "-8.10", "Transport"),
        ("NETFLIX.COM", "-10.99", "Subscriptions"),
        ("Deliveroo order", "-18.50", "Eating Out"),
        ("Salary ACME LTD", "2100.00", "Income"),
        ("Refund from Amazon", "15.00", "Income"),  # money in is always income
        ("Mystery shop", "-5.00", "Other"),
        ("Transfer to current account", "-100.00", "Transfers"),  # "current" must not match "rent"
        ("Rent - Greenway Lettings", "-850.00", "Rent & Bills"),
        ("EE mobile bill", "-20.00", "Rent & Bills"),
        ("Steel works", "-9.00", "Other"),  # short keyword "ee" must not match inside a word
    ],
)
def test_categorise(description, amount, expected):
    assert categorise(description, Decimal(amount)) == expected


# ---------- parsing helpers ----------
@pytest.mark.parametrize(
    "raw,expected",
    [("2026-03-14", date(2026, 3, 14)), ("14/03/2026", date(2026, 3, 14)), ("14 Mar 2026", date(2026, 3, 14))],
)
def test_parse_date(raw, expected):
    assert parse_date(raw) == expected


def test_parse_date_rejects_garbage():
    with pytest.raises(ValueError):
        parse_date("not a date")


@pytest.mark.parametrize(
    "raw,expected",
    [("£1,234.50", "1234.50"), ("-12.3", "-12.30"), ("(45.00)", "-45.00"), ("", "0")],
)
def test_parse_amount(raw, expected):
    assert parse_amount(raw) == Decimal(expected)


# ---------- CSV parsing ----------
def test_parse_signed_amount_csv():
    csv = b"Date,Description,Amount\n2026-03-01,Salary,2000\n2026-03-02,Tesco,-25.50\n"
    result = parse_csv(csv)
    assert result.errors == []
    assert [r.amount for r in result.rows] == [Decimal("2000.00"), Decimal("-25.50")]


def test_parse_money_in_out_columns_and_bom():
    csv = "﻿Transaction Date,Merchant,Money In,Money Out\n01/03/2026,Salary,2000,\n02/03/2026,Pret,,4.20\n".encode()
    rows = parse_csv(csv).rows
    assert rows[0].amount == Decimal("2000.00")
    assert rows[1].amount == Decimal("-4.20")
    assert rows[1].date == date(2026, 3, 2)


def test_bad_rows_are_reported_not_fatal():
    csv = b"date,description,amount\n2026-03-01,Ok,-1\nbad-date,Oops,-1\n2026-03-03,,-1\n2026-03-04,Zero,0\n"
    result = parse_csv(csv)
    assert len(result.rows) == 1
    assert len(result.errors) == 3
    assert result.errors[0].startswith("Line 3")


def test_missing_columns_raise():
    with pytest.raises(CSVFormatError):
        parse_csv(b"foo,bar\n1,2\n")


def test_row_limit():
    body = "".join(f"2026-03-01,Item {i},-1\n" for i in range(10))
    result = parse_csv(("date,description,amount\n" + body).encode(), max_rows=5)
    assert len(result.rows) == 5
    assert "limit" in result.errors[-1]


def test_fingerprint_ignores_case_and_whitespace():
    a = fingerprint(1, date(2026, 3, 1), " Tesco ", Decimal("-5"))
    b = fingerprint(1, date(2026, 3, 1), "tesco", Decimal("-5.00"))
    assert a == b
    assert a != fingerprint(2, date(2026, 3, 1), "tesco", Decimal("-5"))


# ---------- analytics ----------
@dataclass
class Tx:
    date: date
    amount: Decimal
    category: str


TXS = [
    Tx(date(2026, 3, 1), Decimal("2000"), "Income"),
    Tx(date(2026, 3, 2), Decimal("-800"), "Rent & Bills"),
    Tx(date(2026, 3, 5), Decimal("-200"), "Groceries"),
    Tx(date(2026, 2, 10), Decimal("-50"), "Groceries"),
]


def test_summary():
    s = summarise(TXS, "2026-03")
    assert s.income == Decimal("2000")
    assert s.spending == Decimal("1000")
    assert s.net == Decimal("1000")
    assert s.savings_rate == 50.0
    assert s.top_category == "Rent & Bills"
    assert s.transaction_count == 3


def test_summary_with_no_income_has_zero_rate():
    s = summarise([Tx(date(2026, 1, 1), Decimal("-10"), "Other")], "2026-01")
    assert s.savings_rate == 0.0


def test_previous_months_crosses_year_boundary():
    assert previous_months(date(2026, 2, 1), 3) == ["2025-12", "2026-01", "2026-02"]


def test_monthly_totals():
    points = monthly_totals(TXS, ["2026-02", "2026-03"])
    assert points[0]["spending"] == Decimal("50")
    assert points[1]["income"] == Decimal("2000")


def test_spending_by_category_sorted_desc():
    cats = spending_by_category(TXS, "2026-03")
    assert [c["category"] for c in cats] == ["Rent & Bills", "Groceries"]

"""End-to-end API tests using FastAPI's TestClient and a throwaway SQLite database."""
import os
import tempfile

# Point the app at a temporary database *before* it is imported.
_db_file = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file}"
os.environ["SECRET_KEY"] = "test-secret"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # the context manager runs startup (creates tables)
        yield c


def register_and_login(client: TestClient, email: str) -> dict[str, str]:
    client.post("/api/auth/register", json={"email": email, "name": "Test", "password": "supersecret1"})
    r = client.post("/api/auth/login", data={"username": email, "password": "supersecret1"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_register_rejects_short_password(client):
    r = client.post("/api/auth/register", json={"email": "a@b.com", "name": "A", "password": "short"})
    assert r.status_code == 422


def test_duplicate_email_conflicts(client):
    body = {"email": "dup@example.com", "name": "D", "password": "supersecret1"}
    assert client.post("/api/auth/register", json=body).status_code == 201
    assert client.post("/api/auth/register", json=body).status_code == 409


def test_wrong_password_is_401(client):
    register_and_login(client, "wrong@example.com")
    r = client.post("/api/auth/login", data={"username": "wrong@example.com", "password": "nope-nope"})
    assert r.status_code == 401


def test_endpoints_require_auth(client):
    assert client.get("/api/transactions").status_code == 401
    assert client.get("/api/analytics/summary").status_code == 401


def test_create_list_and_auto_categorise(client):
    h = register_and_login(client, "crud@example.com")
    r = client.post("/api/transactions", headers=h,
                    json={"date": "2026-03-02", "description": "TESCO STORES", "amount": "-12.50"})
    assert r.status_code == 201
    assert r.json()["category"] == "Groceries"

    rows = client.get("/api/transactions?month=2026-03", headers=h).json()
    assert len(rows) == 1


def test_users_cannot_see_each_others_data(client):
    alice = register_and_login(client, "alice@example.com")
    bob = register_and_login(client, "bob@example.com")
    tx = client.post("/api/transactions", headers=alice,
                     json={"date": "2026-03-01", "description": "Rent", "amount": "-900"}).json()

    assert client.get(f"/api/transactions/{tx['id']}", headers=bob).status_code == 404
    assert client.delete(f"/api/transactions/{tx['id']}", headers=bob).status_code == 404
    assert client.get("/api/transactions", headers=bob).json() == []


def test_csv_import_dedupes_and_feeds_analytics(client):
    h = register_and_login(client, "import@example.com")
    csv = (
        "Date,Description,Amount\n"
        "2026-03-01,Salary ACME,2000\n"
        "2026-03-02,Rent,-800\n"
        "2026-03-03,Tesco,-200\n"
        "oops,Broken row,-1\n"
    ).encode()
    files = {"file": ("statement.csv", csv, "text/csv")}

    first = client.post("/api/transactions/import", headers=h, files=files).json()
    assert first["imported"] == 3
    assert len(first["errors"]) == 1

    second = client.post("/api/transactions/import", headers=h, files=files).json()
    assert second["imported"] == 0
    assert second["skipped_duplicates"] == 3

    summary = client.get("/api/analytics/summary?month=2026-03", headers=h).json()
    assert float(summary["income"]) == 2000
    assert float(summary["spending"]) == 1000
    assert summary["savings_rate"] == 50.0

    cats = client.get("/api/analytics/by-category?month=2026-03", headers=h).json()
    assert cats[0]["category"] == "Rent & Bills"


def test_import_rejects_non_csv(client):
    h = register_and_login(client, "noncsv@example.com")
    r = client.post("/api/transactions/import", headers=h, files={"file": ("x.txt", b"hello", "text/plain")})
    assert r.status_code == 400

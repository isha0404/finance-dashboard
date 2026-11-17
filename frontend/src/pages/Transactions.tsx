import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api } from "../api";
import { money, monthLabel, recentMonths } from "../format";
import type { Transaction, TransactionInput } from "../types";

const today = () => new Date().toISOString().slice(0, 10);
const blank: TransactionInput = { date: today(), description: "", amount: "", category: "" };

export default function Transactions() {
  const [rows, setRows] = useState<Transaction[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [month, setMonth] = useState("");
  const [category, setCategory] = useState("");
  const [q, setQ] = useState("");
  const [form, setForm] = useState<TransactionInput>(blank);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api.transactions({ month, category, q }).then(setRows).catch((e) => setError(e.message));
  }, [month, category, q]);

  useEffect(() => {
    api.categories().then(setCategories).catch(() => {});
  }, []);

  // Small debounce so we don't hit the API on every keystroke in the search box.
  useEffect(() => {
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
  }, [load]);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    const body = { ...form, category: form.category || null };
    try {
      if (editingId) await api.updateTransaction(editingId, body);
      else await api.createTransaction(body);
      setForm({ ...blank, date: today() });
      setEditingId(null);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save");
    }
  };

  const edit = (t: Transaction) => {
    setEditingId(t.id);
    setForm({ date: t.date, description: t.description, amount: t.amount, category: t.category });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const remove = async (t: Transaction) => {
    if (!window.confirm(`Delete "${t.description}"?`)) return;
    try {
      await api.deleteTransaction(t.id);
      setRows((r) => r.filter((x) => x.id !== t.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete");
    }
  };

  const total = rows.reduce((sum, t) => sum + Number(t.amount), 0);

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Transactions</h1>
          <p className="muted">Add, edit and search everything you've spent and earned.</p>
        </div>
      </header>

      <form className="card form-row" onSubmit={save}>
        <input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} required />
        <input
          placeholder="Description (e.g. Tesco)"
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          required
          maxLength={255}
        />
        <input
          type="number"
          step="0.01"
          placeholder="Amount (−12.50 = spend)"
          value={form.amount}
          onChange={(e) => setForm({ ...form, amount: e.target.value })}
          required
        />
        <select value={form.category ?? ""} onChange={(e) => setForm({ ...form, category: e.target.value })}>
          <option value="">Auto-detect category</option>
          {categories.map((c) => <option key={c}>{c}</option>)}
        </select>
        <button className="btn primary">{editingId ? "Save changes" : "Add"}</button>
        {editingId && (
          <button type="button" className="btn ghost" onClick={() => { setEditingId(null); setForm(blank); }}>
            Cancel
          </button>
        )}
      </form>

      {error && <div className="alert error">{error}</div>}

      <div className="filters">
        <input placeholder="Search…" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={month} onChange={(e) => setMonth(e.target.value)}>
          <option value="">All months</option>
          {recentMonths(24).map((m) => <option key={m} value={m}>{monthLabel(m)}</option>)}
        </select>
        <select value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All categories</option>
          {categories.map((c) => <option key={c}>{c}</option>)}
        </select>
        <span className="muted small">{rows.length} shown · net {money(total)}</span>
      </div>

      <div className="card">
        {rows.length === 0 ? (
          <div className="center muted" style={{ padding: 40 }}>No transactions match.</div>
        ) : (
          <table className="table">
            <thead>
              <tr><th>Date</th><th>Description</th><th>Category</th><th className="num">Amount</th><th /></tr>
            </thead>
            <tbody>
              {rows.map((t) => (
                <tr key={t.id}>
                  <td className="muted">{t.date}</td>
                  <td>{t.description}</td>
                  <td><span className="tag">{t.category}</span></td>
                  <td className={`num ${Number(t.amount) > 0 ? "good" : ""}`}>{money(t.amount)}</td>
                  <td className="actions">
                    <button className="link" onClick={() => edit(t)}>Edit</button>
                    <button className="link danger" onClick={() => remove(t)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api";
import { CATEGORY_COLOURS, money, monthLabel, recentMonths } from "../format";
import type { CategoryTotal, MonthlyPoint, Summary, Transaction } from "../types";

export default function Dashboard() {
  // undefined = let the server choose the latest month that has data
  const [month, setMonth] = useState<string | undefined>(undefined);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [monthly, setMonthly] = useState<MonthlyPoint[]>([]);
  const [cats, setCats] = useState<CategoryTotal[]>([]);
  const [recent, setRecent] = useState<Transaction[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false; // ignore late responses if the month changes quickly
    setError(null);
    api
      .summary(month)
      .then(async (s) => {
        const [m, c, r] = await Promise.all([
          api.monthly(6, s.month),
          api.byCategory(s.month),
          api.transactions({ month: s.month }),
        ]);
        if (cancelled) return;
        setSummary(s);
        setMonthly(m);
        setCats(c);
        setRecent(r.slice(0, 6));
      })
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [month]);

  const months = Array.from(new Set([...(summary ? [summary.month] : []), ...recentMonths(18)])).sort().reverse();
  const chartData = monthly.map((p) => ({
    month: monthLabel(p.month, true),
    Income: Number(p.income),
    Spending: Number(p.spending),
  }));

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Dashboard</h1>
          <p className="muted">Your money at a glance.</p>
        </div>
        <select value={summary?.month ?? ""} onChange={(e) => setMonth(e.target.value)} aria-label="Month">
          {months.map((m) => (
            <option key={m} value={m}>{monthLabel(m)}</option>
          ))}
        </select>
      </header>

      {error && <div className="alert error">{error}</div>}

      {summary && summary.transaction_count === 0 && (
        <div className="card empty">
          <h3>No transactions for {monthLabel(summary.month)} yet</h3>
          <p className="muted">Import a bank statement to see your dashboard come to life.</p>
          <Link to="/import" className="btn primary">Import a CSV</Link>
        </div>
      )}

      {summary && (
        <section className="stats">
          <Stat label="Income" value={money(summary.income)} tone="good" />
          <Stat label="Spending" value={money(summary.spending)} tone="bad" />
          <Stat label="Net" value={money(summary.net)} tone={Number(summary.net) >= 0 ? "good" : "bad"} />
          <Stat
            label="Savings rate"
            value={`${summary.savings_rate}%`}
            hint={summary.top_category ? `Biggest spend: ${summary.top_category}` : undefined}
          />
        </section>
      )}

      <section className="grid-2">
        <div className="card">
          <h3>Income vs spending</h3>
          <p className="muted small">Last 6 months</p>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartData} barGap={4}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,.06)" vertical={false} />
              <XAxis dataKey="month" stroke="#8b8b98" tickLine={false} axisLine={false} />
              <YAxis stroke="#8b8b98" tickLine={false} axisLine={false} tickFormatter={(v) => `£${v}`} width={60} />
              <Tooltip formatter={(v) => money(Number(v))} contentStyle={tooltipStyle} cursor={{ fill: "rgba(255,255,255,.04)" }} />
              <Legend />
              <Bar dataKey="Income" fill="#3ddc84" radius={[6, 6, 0, 0]} />
              <Bar dataKey="Spending" fill="#4c8dff" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h3>Where it went</h3>
          <p className="muted small">Spending by category</p>
          {cats.length === 0 ? (
            <div className="center muted" style={{ height: 280 }}>No spending this month</div>
          ) : (
            <div className="donut">
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={cats.map((c) => ({ ...c, total: Number(c.total) }))} dataKey="total" nameKey="category" innerRadius={60} outerRadius={95} paddingAngle={2}>
                    {cats.map((c) => (
                      <Cell key={c.category} fill={CATEGORY_COLOURS[c.category] ?? "#576574"} stroke="none" />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v) => money(Number(v))} contentStyle={tooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
              <ul className="legend">
                {cats.slice(0, 6).map((c) => (
                  <li key={c.category}>
                    <i style={{ background: CATEGORY_COLOURS[c.category] }} />
                    {c.category}
                    <b>{money(c.total)}</b>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </section>

      <section className="card">
        <div className="row-between">
          <h3>Recent transactions</h3>
          <Link to="/transactions" className="link">View all →</Link>
        </div>
        <table className="table">
          <tbody>
            {recent.map((t) => (
              <tr key={t.id}>
                <td className="muted">{t.date}</td>
                <td>{t.description}</td>
                <td><span className="tag">{t.category}</span></td>
                <td className={`num ${Number(t.amount) > 0 ? "good" : ""}`}>{money(t.amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}

const tooltipStyle = { background: "#16161d", border: "1px solid rgba(255,255,255,.1)", borderRadius: 10 };

function Stat({ label, value, tone, hint }: { label: string; value: string; tone?: "good" | "bad"; hint?: string }) {
  return (
    <div className="card stat">
      <div className="muted small">{label}</div>
      <div className={`stat-value ${tone ?? ""}`}>{value}</div>
      {hint && <div className="muted small">{hint}</div>}
    </div>
  );
}

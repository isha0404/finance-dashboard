import { useRef, useState, type DragEvent } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { ImportResult } from "../types";

const MAX_BYTES = 2 * 1024 * 1024;

export default function ImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string[][]>([]);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  const choose = async (f: File | undefined) => {
    setResult(null);
    setError(null);
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".csv")) return setError("Please choose a .csv file.");
    if (f.size > MAX_BYTES) return setError("That file is over 2 MB.");
    setFile(f);
    // Show the first few lines so the user can check it's the right file before uploading.
    const text = await f.slice(0, 4000).text();
    setPreview(text.split(/\r?\n/).filter(Boolean).slice(0, 6).map((line) => line.split(",")));
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    choose(e.dataTransfer.files[0]);
  };

  const upload = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await api.importCsv(file));
      setFile(null);
      setPreview([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Import a bank statement</h1>
          <p className="muted">
            Upload a CSV export from your bank. Transactions are categorised automatically and duplicates are skipped,
            so it's safe to upload overlapping statements.
          </p>
        </div>
      </header>

      <div
        className={`card dropzone ${dragging ? "over" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => input.current?.click()}
        role="button"
        tabIndex={0}
      >
        <input ref={input} type="file" accept=".csv,text/csv" hidden onChange={(e) => choose(e.target.files?.[0])} />
        <div className="drop-icon">⇪</div>
        <strong>{file ? file.name : "Drop a CSV here, or click to choose"}</strong>
        <span className="muted small">
          Needs a date and description column, plus either an amount column or money in / money out columns. Max 2 MB.
        </span>
      </div>

      {preview.length > 0 && (
        <div className="card">
          <h3>Preview</h3>
          <table className="table compact">
            <tbody>
              {preview.map((cells, i) => (
                <tr key={i} className={i === 0 ? "head" : ""}>
                  {cells.map((c, j) => <td key={j}>{c}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
          <button className="btn primary" onClick={upload} disabled={busy}>
            {busy ? "Importing…" : "Import transactions"}
          </button>
        </div>
      )}

      {error && <div className="alert error">{error}</div>}

      {result && (
        <div className="card">
          <h3>Import complete</h3>
          <div className="stats">
            <div><div className="stat-value good">{result.imported}</div><div className="muted small">imported</div></div>
            <div><div className="stat-value">{result.skipped_duplicates}</div><div className="muted small">duplicates skipped</div></div>
            <div><div className="stat-value bad">{result.errors.length}</div><div className="muted small">rows with problems</div></div>
          </div>
          {result.errors.length > 0 && (
            <ul className="errors">{result.errors.map((e) => <li key={e}>{e}</li>)}</ul>
          )}
          <Link to="/" className="btn primary">See your dashboard →</Link>
        </div>
      )}

      <p className="muted small">
        No statement handy? Try <code>sample-data/transactions.csv</code> from the repo.
      </p>
    </>
  );
}

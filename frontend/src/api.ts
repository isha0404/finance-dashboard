import type {
  CategoryTotal,
  ImportResult,
  MonthlyPoint,
  Summary,
  Transaction,
  TransactionInput,
  User,
} from "./types";

const TOKEN_KEY = "fd_token";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

/** Called when the server says our token is no longer valid (set by AuthProvider). */
let onUnauthorised: () => void = () => {};
export const setUnauthorisedHandler = (fn: () => void) => (onUnauthorised = fn);

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = tokenStore.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData) && !(init.body instanceof URLSearchParams)) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(path, { ...init, headers });

  if (res.status === 401 && token) onUnauthorised();
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      // FastAPI returns either {"detail": "text"} or {"detail": [{msg: ...}, ...]} for validation errors.
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((d: { msg: string }) => d.msg).join(", ");
    } catch {
      /* response had no JSON body */
    }
    throw new ApiError(res.status, message);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

const qs = (params: Record<string, string | number | undefined>) => {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => v !== undefined && v !== "" && p.set(k, String(v)));
  const s = p.toString();
  return s ? `?${s}` : "";
};

export const api = {
  // auth
  register: (email: string, name: string, password: string) =>
    request<User>("/api/auth/register", { method: "POST", body: JSON.stringify({ email, name, password }) }),
  login: (email: string, password: string) =>
    request<{ access_token: string }>("/api/auth/login", {
      method: "POST",
      body: new URLSearchParams({ username: email, password }),
    }),
  me: () => request<User>("/api/auth/me"),

  // transactions
  categories: () => request<string[]>("/api/transactions/categories"),
  transactions: (f: { month?: string; category?: string; q?: string } = {}) =>
    request<Transaction[]>(`/api/transactions${qs(f)}`),
  createTransaction: (t: TransactionInput) =>
    request<Transaction>("/api/transactions", { method: "POST", body: JSON.stringify(t) }),
  updateTransaction: (id: number, t: TransactionInput) =>
    request<Transaction>(`/api/transactions/${id}`, { method: "PUT", body: JSON.stringify(t) }),
  deleteTransaction: (id: number) => request<void>(`/api/transactions/${id}`, { method: "DELETE" }),
  importCsv: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<ImportResult>("/api/transactions/import", { method: "POST", body: form });
  },

  // analytics
  summary: (month?: string) => request<Summary>(`/api/analytics/summary${qs({ month })}`),
  monthly: (months = 6, end?: string) => request<MonthlyPoint[]>(`/api/analytics/monthly${qs({ months, end })}`),
  byCategory: (month?: string) => request<CategoryTotal[]>(`/api/analytics/by-category${qs({ month })}`),
};

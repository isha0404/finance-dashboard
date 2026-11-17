// Shapes returned by the API. Money comes back as strings (Python Decimal) to avoid float rounding.

export interface User {
  id: number;
  email: string;
  name: string;
}

export interface Transaction {
  id: number;
  date: string; // YYYY-MM-DD
  description: string;
  amount: string;
  category: string;
}

export interface TransactionInput {
  date: string;
  description: string;
  amount: string;
  category?: string | null;
}

export interface ImportResult {
  imported: number;
  skipped_duplicates: number;
  errors: string[];
}

export interface Summary {
  month: string;
  income: string;
  spending: string;
  net: string;
  savings_rate: number;
  top_category: string | null;
  transaction_count: number;
}

export interface MonthlyPoint {
  month: string;
  income: string;
  spending: string;
}

export interface CategoryTotal {
  category: string;
  total: string;
}

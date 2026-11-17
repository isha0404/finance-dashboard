const gbp = new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP" });

export const money = (value: string | number) => gbp.format(Number(value));

/** "2026-03" -> "Mar 2026" */
export const monthLabel = (key: string, short = false) => {
  const [y, m] = key.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString("en-GB", short ? { month: "short" } : { month: "short", year: "numeric" });
};

/** Month keys for the last `count` months, newest first, e.g. for a <select>. */
export const recentMonths = (count = 12): string[] => {
  const now = new Date();
  return Array.from({ length: count }, (_, i) => {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  });
};

export const CATEGORY_COLOURS: Record<string, string> = {
  Income: "#3ddc84",
  Groceries: "#4c8dff",
  "Eating Out": "#ff9f43",
  Transport: "#9b7bff",
  "Rent & Bills": "#ff6b6b",
  Shopping: "#f368e0",
  Subscriptions: "#00d2d3",
  Health: "#1dd1a1",
  Entertainment: "#feca57",
  Transfers: "#8395a7",
  Other: "#576574",
};

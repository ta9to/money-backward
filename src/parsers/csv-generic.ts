import { Transaction } from "../schema.js";

/**
 * Very small MVP parser.
 * Assumes the CSV already has recognizable columns.
 */
export function parseGenericCsv(
  rows: Record<string, string>[],
  opts: { file?: string; account?: string; currency?: string }
): Transaction[] {
  const currency = opts.currency ?? "JPY";

  // Common column candidates (JP exports vary a lot).
  const col = {
    date: pickKey(rows, ["date", "Date", "日付", "利用日", "取引日"]),
    amount: pickKey(rows, ["amount", "Amount", "金額", "利用金額", "支払金額", "入金", "出金"]),
    desc: pickKey(rows, ["description", "Description", "摘要", "内容", "利用店名", "加盟店名", "取引内容"]),
    merchant: pickKey(rows, ["merchant", "Merchant", "店名", "加盟店"]),
    category: pickKey(rows, ["category", "Category", "カテゴリ", "費目"])
  };

  return rows
    .map((r, i) => {
      const dateRaw = col.date ? r[col.date] : undefined;
      const amountRaw = col.amount ? r[col.amount] : undefined;
      const descRaw = col.desc ? r[col.desc] : undefined;

      if (!dateRaw || !amountRaw || !descRaw) return null;

      const date = normalizeDate(dateRaw);
      const amount = normalizeAmount(amountRaw);

      const tx: Transaction = {
        date,
        amount,
        currency,
        description: descRaw,
        merchant: col.merchant ? r[col.merchant] || undefined : undefined,
        category: col.category ? r[col.category] || undefined : undefined,
        account: opts.account,
        source: { file: opts.file, row: i + 2, raw: r }
      };
      return tx;
    })
    .filter((x): x is Transaction => x !== null);
}

function pickKey(rows: Record<string, string>[], candidates: string[]): string | null {
  const keys = new Set<string>();
  for (const r of rows) for (const k of Object.keys(r)) keys.add(k);
  for (const c of candidates) if (keys.has(c)) return c;
  return null;
}

function normalizeDate(s: string): string {
  // Supports YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD
  const m = s.trim().match(/^(\d{4})[\/.\-](\d{1,2})[\/.\-](\d{1,2})/);
  if (m) {
    const yyyy = m[1];
    const mm = m[2].padStart(2, "0");
    const dd = m[3].padStart(2, "0");
    return `${yyyy}-${mm}-${dd}`;
  }
  // Fallback: let caller/LLM fix later.
  throw new Error(`Unsupported date format: ${s}`);
}

function normalizeAmount(s: string): number {
  // Remove commas, yen symbols, whitespace, and parentheses.
  const cleaned = s
    .trim()
    .replace(/[￥¥,\s]/g, "")
    .replace(/\(([^)]+)\)/g, "-$1");

  // Handle columns like "出金"/"入金" by leaving sign as-is.
  const n = Number(cleaned);
  if (!Number.isFinite(n)) throw new Error(`Unsupported amount: ${s}`);
  return n;
}

import { Transaction } from "../schema.js";

/**
 * SMBC (Olive) credit statement CSV (no header).
 * Observed format:
 *  - First row: "<name>様,<masked card>,<product>"
 *  - Following rows: date, description, amount, paymentType, count, paymentAmount, note?
 */
export function parseSmbcOliveCsv(
  records: string[][],
  opts: { file?: string; account?: string; currency?: string }
): Transaction[] {
  const currency = opts.currency ?? "JPY";

  const out: Transaction[] = [];

  for (let i = 0; i < records.length; i++) {
    const r = records[i];

    // Skip the first meta line if it looks like it.
    if (i === 0 && looksLikeMetaRow(r)) continue;

    if (r.length < 3) continue;

    const dateRaw = r[0];
    const descRaw = r[1];

    // Prefer "支払金額" column when present, otherwise use "利用金額".
    const amountCandidate = firstNonEmpty([r[5], r[2]]);
    if (!dateRaw || !descRaw || !amountCandidate) continue;

    const date = normalizeDate(dateRaw);
    const amt = normalizeAmount(amountCandidate);

    const tx: Transaction = {
      date,
      amount: normalizeAsExpense(amt),
      currency,
      description: descRaw,
      merchant: descRaw,
      account: opts.account ?? "SMBC Olive",
      source: { file: opts.file, row: i + 1, raw: toRawObject(r) }
    };
    out.push(tx);
  }

  return out;
}

function looksLikeMetaRow(r: string[]): boolean {
  if (r.length < 3) return false;
  return /様\s*$/.test(r[0]) || /Ｏｌｉｖｅ|Olive/i.test(r[2]);
}

function normalizeDate(s: string): string {
  const m = s.trim().match(/^(\d{4})[\/.\-](\d{1,2})[\/.\-](\d{1,2})/);
  if (m) {
    const yyyy = m[1];
    const mm = m[2].padStart(2, "0");
    const dd = m[3].padStart(2, "0");
    return `${yyyy}-${mm}-${dd}`;
  }
  throw new Error(`Unsupported date format: ${s}`);
}

function normalizeAmount(s: string): number {
  const cleaned = s
    .trim()
    .replace(/[￥¥,\s]/g, "")
    .replace(/\(([^)]+)\)/g, "-$1");
  const n = Number(cleaned);
  if (!Number.isFinite(n)) throw new Error(`Unsupported amount: ${s}`);
  return n;
}

function normalizeAsExpense(n: number): number {
  // SMBC credit statement lines are expenses; if refunds appear, they may come as negative.
  return n <= 0 ? n : -n;
}

function firstNonEmpty(xs: Array<string | undefined>): string | undefined {
  for (const x of xs) {
    if (x && x.trim() !== "") return x;
  }
  return undefined;
}

function toRawObject(r: string[]): Record<string, string> {
  // Keep stable keys even without header.
  const keys = ["date", "description", "amount", "paymentType", "count", "paymentAmount", "note"];
  const o: Record<string, string> = {};
  for (let i = 0; i < Math.min(keys.length, r.length); i++) o[keys[i]] = r[i];
  return o;
}

import { Transaction } from "../schema.js";

/**
 * SMBC bank account statement CSV.
 * Observed headers (CP932):
 *  - 年月日
 *  - お引出し
 *  - お預入れ
 *  - お取り扱い内容
 *  - 残高
 */
export function parseSmbcBankCsv(
  rows: Record<string, string>[],
  opts: { file?: string; account?: string; currency?: string }
): Transaction[] {
  const currency = opts.currency ?? "JPY";

  const keyDate = pickKey(rows, ["年月日", "日付", "Date"]);
  const keyWithdraw = pickKey(rows, ["お引出し", "出金", "引出", "withdrawal"]);
  const keyDeposit = pickKey(rows, ["お預入れ", "入金", "deposit"]);
  const keyDesc = pickKey(rows, ["お取り扱い内容", "摘要", "内容", "description"]);

  if (!keyDate || (!keyWithdraw && !keyDeposit) || !keyDesc) {
    throw new Error(
      `SMBC bank CSV: required columns not found. date=${keyDate} withdraw=${keyWithdraw} deposit=${keyDeposit} desc=${keyDesc}`
    );
  }

  const out: Transaction[] = [];

  for (let i = 0; i < rows.length; i++) {
    const r = rows[i];
    const dateRaw = r[keyDate];
    const descRaw = r[keyDesc];

    if (!dateRaw || !descRaw) continue;

    const w = keyWithdraw ? parseYen(r[keyWithdraw]) : 0;
    const d = keyDeposit ? parseYen(r[keyDeposit]) : 0;

    if (!w && !d) continue;

    const amount = d > 0 ? d : -w;

    out.push({
      date: normalizeDate(dateRaw),
      amount,
      currency,
      description: descRaw,
      merchant: descRaw,
      account: opts.account ?? "SMBC Bank",
      source: { file: opts.file, row: i + 2, raw: r }
    });
  }

  return out;
}

function pickKey(rows: Record<string, string>[], candidates: string[]): string | null {
  const keys = new Set<string>();
  for (const r of rows) for (const k of Object.keys(r)) keys.add(k);
  for (const c of candidates) if (keys.has(c)) return c;
  return null;
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

function parseYen(s: string | undefined): number {
  if (!s) return 0;
  const cleaned = s.trim().replace(/[￥¥,\s]/g, "");
  if (cleaned === "") return 0;
  const n = Number(cleaned);
  if (!Number.isFinite(n)) return 0;
  return n;
}

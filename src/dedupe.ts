import crypto from "node:crypto";
import { Transaction } from "./schema.js";

export type DedupeResult = {
  transactions: Transaction[];
  removed: number;
};

/**
 * Deterministic best-effort dedupe.
 *
 * Hash key is based on stable normalized fields.
 * (date, amount, description, account) are usually enough.
 */
export function dedupeTransactions(transactions: Transaction[]): DedupeResult {
  const seen = new Set<string>();
  const out: Transaction[] = [];
  let removed = 0;

  for (const tx of transactions) {
    const key = hashKey(tx);
    if (seen.has(key)) {
      removed++;
      continue;
    }
    seen.add(key);
    out.push(tx);
  }

  // Stable sort (oldest first) for downstream tools.
  out.sort((a, b) => (a.date === b.date ? (a.amount ?? 0) - (b.amount ?? 0) : a.date.localeCompare(b.date)));

  return { transactions: out, removed };
}

function hashKey(tx: Transaction): string {
  const payload = {
    date: tx.date,
    amount: tx.amount,
    description: tx.description,
    account: tx.account ?? "",
    currency: tx.currency
  };
  return crypto.createHash("sha256").update(JSON.stringify(payload)).digest("hex");
}

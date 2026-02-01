import fs from "node:fs/promises";
import { Transaction } from "./schema.js";
import { ensureDirForFile } from "./io.js";

const CSV_HEADER = [
  "date",
  "amount",
  "currency",
  "description",
  "merchant",
  "category",
  "account",
  "source_file",
  "source_row"
];

export async function writeTransactionsCsv(filePath: string, txs: Transaction[]): Promise<void> {
  await ensureDirForFile(filePath);

  const lines: string[] = [];
  lines.push(CSV_HEADER.join(","));

  for (const t of txs) {
    const row = [
      t.date,
      String(t.amount),
      t.currency,
      t.description,
      t.merchant ?? "",
      t.category ?? "",
      t.account ?? "",
      t.source?.file ?? "",
      t.source?.row != null ? String(t.source.row) : ""
    ].map(csvEscape);

    lines.push(row.join(","));
  }

  await fs.writeFile(filePath, lines.join("\n") + "\n", "utf8");
}

function csvEscape(v: string): string {
  if (v == null) return "";
  const needsQuote = /[\n\r,\"]/g.test(v);
  const s = v.replace(/\"/g, '""');
  return needsQuote ? `"${s}"` : s;
}

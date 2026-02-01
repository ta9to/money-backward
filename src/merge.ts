import fs from "node:fs/promises";
import path from "node:path";
import { TransactionsFileSchema, Transaction } from "./schema.js";

export async function readTransactionsFile(filePath: string): Promise<Transaction[]> {
  const raw = await fs.readFile(filePath, "utf8");
  const json = JSON.parse(raw);
  const parsed = TransactionsFileSchema.parse(json);
  return parsed.transactions;
}

export async function listJsonFiles(inputs: string[]): Promise<string[]> {
  const out: string[] = [];

  for (const p of inputs) {
    // crude glob support for "dir/*.json"
    if (p.includes("*")) {
      const dir = path.dirname(p);
      const base = path.basename(p);
      const re = globToRegExp(base);
      const entries = await fs.readdir(dir);
      for (const e of entries) {
        if (re.test(e)) out.push(path.join(dir, e));
      }
    } else {
      out.push(p);
    }
  }

  // de-dupe file paths + stable order
  return Array.from(new Set(out)).sort();
}

function globToRegExp(glob: string): RegExp {
  const escaped = glob.replace(/[.+^${}()|[\]\\]/g, "\\$&");
  const re = "^" + escaped.replace(/\*/g, ".*") + "$";
  return new RegExp(re);
}

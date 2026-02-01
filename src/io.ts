import fs from "node:fs/promises";
import path from "node:path";
import pdf from "pdf-parse";
import { parse as parseCsv } from "csv-parse/sync";

export async function readTextFromPdf(filePath: string): Promise<string> {
  const buf = await fs.readFile(filePath);
  const data = await pdf(buf);
  return data.text ?? "";
}

export async function readRowsFromCsv(filePath: string): Promise<Record<string, string>[]> {
  const raw = await fs.readFile(filePath, "utf8");
  const rows = parseCsv(raw, {
    columns: true,
    skip_empty_lines: true,
    bom: true,
    relax_column_count: true,
    trim: true
  }) as Record<string, string>[];
  return rows;
}

export async function ensureDirForFile(filePath: string) {
  const dir = path.dirname(filePath);
  await fs.mkdir(dir, { recursive: true });
}

export async function writeJson(filePath: string, data: unknown) {
  await ensureDirForFile(filePath);
  await fs.writeFile(filePath, JSON.stringify(data, null, 2) + "\n", "utf8");
}

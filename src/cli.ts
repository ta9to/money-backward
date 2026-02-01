#!/usr/bin/env node
import { Command } from "commander";
import chalk from "chalk";
import path from "node:path";

import {
  readRecordsFromCsv,
  readRowsFromCsv,
  readRowsFromCsvWithEncoding,
  readTextFromPdf,
  writeJson
} from "./io.js";
import { TransactionsFileSchema } from "./schema.js";
import { parseGenericCsv } from "./parsers/csv-generic.js";
import { parseSmbcOliveCsv } from "./parsers/smbc-olive.js";
import { parseSmbcBankCsv } from "./parsers/smbc-bank.js";
import { createLlmClient } from "./llm/index.js";
import { parsePdfWithLlm } from "./parsers/pdf-llm.js";
import { listJsonFiles, readTransactionsFile } from "./merge.js";
import { dedupeTransactions } from "./dedupe.js";
import { writeTransactionsCsv } from "./export.js";

const program = new Command();

program
  .name("money-backward")
  .description("Convert raw financial data (PDF/CSV) into structured JSON.")
  .version("0.1.0");

program
  .command("ingest")
  .description("Ingest a statement file and output normalized JSON.")
  .argument("<input>", "Input file path (.csv or .pdf)")
  .option("-o, --out <path>", "Output JSON path", "./out/transactions.json")
  .option("--type <type>", "Force type: csv|pdf")
  .option("--parser <parser>", "CSV parser: generic|smbc-olive|smbc-bank", "generic")
  .option("--account <name>", "Account label")
  .option("--currency <code>", "Currency (JPY/USD/EUR...)", "JPY")
  .action(async (input, opts) => {
    const ext = path.extname(input).toLowerCase();
    const type = (opts.type ?? (ext === ".pdf" ? "pdf" : "csv")) as "csv" | "pdf";

    let transactions = [];

    if (type === "csv") {
      const parser = String(opts.parser ?? "generic");

      if (parser === "smbc-olive") {
        const records = await readRecordsFromCsv({ filePath: input, encoding: "cp932" });
        transactions = parseSmbcOliveCsv(records, { file: input, account: opts.account, currency: opts.currency });
      } else if (parser === "smbc-bank") {
        const rows = await readRowsFromCsvWithEncoding({ filePath: input, encoding: "cp932" });
        transactions = parseSmbcBankCsv(rows, { file: input, account: opts.account, currency: opts.currency });
      } else {
        const rows = await readRowsFromCsv(input);
        transactions = parseGenericCsv(rows, { file: input, account: opts.account, currency: opts.currency });
      }
    } else if (type === "pdf") {
      const text = await readTextFromPdf(input);
      const llm = createLlmClient();
      transactions = await parsePdfWithLlm({ text, file: input, account: opts.account, currency: opts.currency, llm });
    } else {
      throw new Error(`Unknown type: ${type}`);
    }

    const out = {
      version: 1 as const,
      generatedAt: new Date().toISOString(),
      tool: "money-backward@0.1.0",
      transactions
    };

    // Validate before writing.
    const parsed = TransactionsFileSchema.parse(out);
    await writeJson(opts.out, parsed);

    console.log(chalk.green(`OK: wrote ${transactions.length} transactions -> ${opts.out}`));

    if (type === "pdf") {
      console.log(
        chalk.yellow(
          "Note: PDF mode requires an LLM adapter. Currently only provider=none is implemented; set up OpenAI/Anthropic next."
        )
      );
    }
  });

program
  .command("merge")
  .description("Merge multiple normalized JSON files into one (optionally dedupe).")
  .argument("<inputs...>", "Input JSON files (supports simple globs like out/*.json)")
  .option("-o, --out <path>", "Output JSON path", "./out/merged.json")
  .option("--dedupe", "Dedupe transactions (recommended)", true)
  .action(async (inputs: string[], opts) => {
    const files = await listJsonFiles(inputs);
    if (files.length === 0) throw new Error("No input files matched");

    let all = [] as any[];
    for (const f of files) {
      const txs = await readTransactionsFile(f);
      all.push(...txs);
    }

    let removed = 0;
    if (opts.dedupe) {
      const r = dedupeTransactions(all);
      all = r.transactions;
      removed = r.removed;
    }

    const out = {
      version: 1 as const,
      generatedAt: new Date().toISOString(),
      tool: "money-backward@0.1.0",
      transactions: all
    };

    const parsed = TransactionsFileSchema.parse(out);
    await writeJson(opts.out, parsed);

    console.log(
      chalk.green(
        `OK: merged ${files.length} file(s), ${parsed.transactions.length} txs` +
          (opts.dedupe ? ` (deduped: -${removed})` : "") +
          ` -> ${opts.out}`
      )
    );
  });

program
  .command("export-csv")
  .description("Export a normalized JSON file to CSV (streamlit/pandas friendly).")
  .argument("<input>", "Input normalized JSON")
  .option("-o, --out <path>", "Output CSV path", "./out/transactions.csv")
  .action(async (input, opts) => {
    const txs = await readTransactionsFile(input);
    await writeTransactionsCsv(opts.out, txs);
    console.log(chalk.green(`OK: wrote ${txs.length} rows -> ${opts.out}`));
  });

program
  .command("schema")
  .description("Print the JSON schema (rough) for the normalized output.")
  .action(() => {
    console.log(
      [
        "Normalized output is a JSON object:",
        "{ version: 1, generatedAt: ISOString, tool: string, transactions: Transaction[] }",
        "Transaction fields:",
        "- date: YYYY-MM-DD",
        "- amount: number (income +, expense -)",
        "- currency: 3-letter code (default JPY)",
        "- description: string",
        "- merchant?: string",
        "- category?: string",
        "- account?: string",
        "- source?: { file?: string, row?: number, raw?: object|string }"
      ].join("\n")
    );
  });

program.parseAsync(process.argv).catch((err) => {
  console.error(chalk.red(err?.stack ?? String(err)));
  process.exitCode = 1;
});

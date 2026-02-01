#!/usr/bin/env node
import { Command } from "commander";
import chalk from "chalk";
import path from "node:path";

import { readRowsFromCsv, readTextFromPdf, writeJson } from "./io.js";
import { TransactionsFileSchema } from "./schema.js";
import { parseGenericCsv } from "./parsers/csv-generic.js";
import { createLlmClient } from "./llm/index.js";
import { parsePdfWithLlm } from "./parsers/pdf-llm.js";

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
  .option("--account <name>", "Account label")
  .option("--currency <code>", "Currency (JPY/USD/EUR...)", "JPY")
  .action(async (input, opts) => {
    const ext = path.extname(input).toLowerCase();
    const type = (opts.type ?? (ext === ".pdf" ? "pdf" : "csv")) as "csv" | "pdf";

    let transactions = [];

    if (type === "csv") {
      const rows = await readRowsFromCsv(input);
      transactions = parseGenericCsv(rows, { file: input, account: opts.account, currency: opts.currency });
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
  .command("schema")
  .description("Print the JSON schema (rough) for the normalized output.")
  .action(() => {
    // Keep it simple: point to source for now.
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
        "- source?: { file?: string, row?: number, raw?: object }"
      ].join("\n")
    );
  });

program.parseAsync(process.argv).catch((err) => {
  console.error(chalk.red(err?.stack ?? String(err)));
  process.exitCode = 1;
});

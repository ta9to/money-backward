import { Transaction, TransactionSchema } from "../schema.js";
import { LlmClient } from "../llm/types.js";

const SYSTEM = `You are a careful financial data normalization tool.
Return ONLY valid JSON (no markdown), matching the requested schema exactly.
Dates must be ISO YYYY-MM-DD.
Amounts: positive income, negative expense.
Currency: 3-letter code (default JPY).
Do not hallucinate transactions that are not present.`;

export async function parsePdfWithLlm(args: {
  text: string;
  file?: string;
  account?: string;
  currency?: string;
  llm: LlmClient;
}): Promise<Transaction[]> {
  const currency = args.currency ?? "JPY";

  const prompt = `Extract transactions from the following bank/card statement text.

Return a JSON array of Transaction objects with fields:
- date (YYYY-MM-DD)
- amount (number; expense negative)
- currency (string; use ${currency})
- description (string)
- merchant (optional string)
- category (optional string)
- account (optional string; use ${args.account ?? ""})

Also include source.raw if you can (best-effort), but keep it small.

STATEMENT_TEXT_START
${args.text.slice(0, 120_000)}
STATEMENT_TEXT_END
`;

  const json = await args.llm.generateJson({ system: SYSTEM, prompt });
  const data = JSON.parse(json);

  if (!Array.isArray(data)) throw new Error("LLM must return an array");

  const out: Transaction[] = [];
  for (const item of data) {
    // Attach minimal traceability.
    const withSource = {
      ...item,
      currency: item.currency ?? currency,
      account: item.account ?? args.account,
      source: {
        ...(item.source ?? {}),
        file: args.file
      }
    };
    out.push(TransactionSchema.parse(withSource));
  }
  return out;
}

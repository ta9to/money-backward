import { z } from "zod";

/**
 * Core schema for a normalized transaction record.
 * Keep it bank-agnostic; bank-specific parsers should map into this.
 */
export const TransactionSchema = z.object({
  /** ISO date (YYYY-MM-DD). */
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  /** Positive = income, negative = expense (normalized). */
  amount: z.number().finite(),
  currency: z.string().min(3).max(3).default("JPY"),

  description: z.string().min(1),
  merchant: z.string().optional(),

  /** Optional normalized category label. */
  category: z.string().optional(),

  /** Source account label (e.g., "Rakuten Card", "SBI Bank"). */
  account: z.string().optional(),

  /** Bank/provider raw row reference for traceability. */
  source: z
    .object({
      file: z.string().optional(),
      row: z.number().int().positive().optional(),
      raw: z.record(z.any()).optional()
    })
    .optional()
});

export const TransactionsFileSchema = z.object({
  version: z.literal(1),
  generatedAt: z.string(),
  tool: z.string(),
  transactions: z.array(TransactionSchema)
});

export type Transaction = z.infer<typeof TransactionSchema>;
export type TransactionsFile = z.infer<typeof TransactionsFileSchema>;

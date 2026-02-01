# money-backward — Design (MVP)

## Goal
Convert raw financial exports (CSV/PDF) into a **normalized transaction JSON** for a private dashboard / analysis pipeline.

## Principles
- **Bank-agnostic core schema**: one output format regardless of provider.
- **Traceability**: keep `source.file` and (for CSV) `source.row` + `source.raw` so you can debug mappings.
- **Pluggable ingestion**:
  - CSV: deterministic parser(s)
  - PDF: text extraction + LLM-based structuring (adapter per provider)

## CLI surface
- `money-backward ingest <input> [--type csv|pdf] --out <path> [--account <name>] [--currency JPY]`
- `money-backward schema`

## Normalized Schema
See `src/schema.ts`.

### Key conventions
- `amount`: **income positive**, **expense negative** (normalized)
- `date`: ISO `YYYY-MM-DD`

## Modules
- `src/io.ts`: file IO + PDF text extraction + CSV row parsing
- `src/parsers/csv-generic.ts`: generic CSV mapper (header-based)
- `src/parsers/pdf-llm.ts`: LLM prompt + strict Zod validation
- `src/llm/*`: LLM adapter layer (currently only `none`)

## Next steps
1. Add at least one real bank-specific CSV parser (Rakuten Card / SBI / SMBC etc.).
2. Implement an LLM adapter:
   - OpenAI or Anthropic (env-driven)
   - JSON-mode / tool calling where possible
3. Add `validate` command + `merge` command (combine multiple ingests into one file, dedupe by hash).
4. Add tests with fixture CSVs.

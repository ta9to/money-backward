# 💸 money-backward

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Status](https://img.shields.io/badge/MoneyForward-Canceled-red)
![Bank](https://img.shields.io/badge/Bank_Sync-Manual_CSV-green)

> **"I canceled my subscription to build this."**

`money-backward` is a CLI tool to convert raw financial exports (CSV/PDF) into **normalized transaction JSON**, as input for a private, customizable dashboard.

## Status
MVP scaffolding is in place:
- CSV ingest (generic header-based)
- PDF ingest pipeline (text extraction + LLM hook) — **Claude Code CLI adapter available** (`claude` OAuth)

## Install (dev)
```bash
npm i
npm run build
```

## Usage
```bash
# Print schema
node dist/cli.js schema

# Ingest CSV
node dist/cli.js ingest ./statement.csv --out ./out/transactions.json --account "My Account" --currency JPY

# Ingest PDF (Claude Code CLI)
MONEY_BACKWARD_LLM_PROVIDER=claude-cli node dist/cli.js ingest ./statement.pdf --type pdf --out ./out/transactions.json
```

## Design notes
See `DESIGN.md`.

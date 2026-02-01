import { createNoneClient } from "./none.js";
import { createClaudeCliClient } from "./claude-cli.js";
import { LlmClient, LlmProvider } from "./types.js";

export function createLlmClient(): LlmClient {
  const provider = (process.env.MONEY_BACKWARD_LLM_PROVIDER ?? "none") as LlmProvider;

  if (provider === "none") return createNoneClient();

  if (provider === "claude-cli") {
    return createClaudeCliClient({
      bin: process.env.MONEY_BACKWARD_CLAUDE_BIN,
      model: process.env.MONEY_BACKWARD_CLAUDE_MODEL
    });
  }

  throw new Error(
    `LLM provider '${provider}' not implemented yet. Try MONEY_BACKWARD_LLM_PROVIDER=claude-cli.`
  );
}

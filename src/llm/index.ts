import { createNoneClient } from "./none.js";
import { LlmClient, LlmProvider } from "./types.js";

export function createLlmClient(): LlmClient {
  const provider = (process.env.MONEY_BACKWARD_LLM_PROVIDER ?? "none") as LlmProvider;

  // For MVP we only implement 'none'.
  // We'll add OpenAI/Anthropic adapters once we decide which key + model we want.
  if (provider === "none") return createNoneClient();

  throw new Error(
    `LLM provider '${provider}' not implemented yet. Set MONEY_BACKWARD_LLM_PROVIDER=none for now.`
  );
}

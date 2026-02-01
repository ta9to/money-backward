import { LlmClient } from "./types.js";

export function createNoneClient(): LlmClient {
  return {
    provider: "none",
    async generateJson() {
      throw new Error(
        "LLM provider is disabled (provider=none). Use CSV mode or set MONEY_BACKWARD_LLM_PROVIDER."
      );
    }
  };
}

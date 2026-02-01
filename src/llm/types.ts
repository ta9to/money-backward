export type LlmProvider = "none" | "openai" | "anthropic";

export type LlmClient = {
  provider: LlmProvider;
  /** Returns a JSON string (not parsed), to allow strict post-parse validation. */
  generateJson(args: { system: string; prompt: string }): Promise<string>;
};

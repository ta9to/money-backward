import { spawn } from "node:child_process";
import { LlmClient } from "./types.js";

/**
 * Claude Code CLI adapter.
 * Assumes `claude` is installed and authenticated via subscription OAuth.
 */
export function createClaudeCliClient(args?: {
  /** Override claude executable name/path. Default: `claude` */
  bin?: string;
  /** Optional model name (depends on your Claude Code setup). */
  model?: string;
}): LlmClient {
  const bin = args?.bin ?? "claude";

  return {
    provider: "anthropic",
    async generateJson({ system, prompt }) {
      // We want strictly JSON.
      // Claude Code CLI flags can vary across versions, so we use a conservative approach:
      // - pass full instruction in the prompt
      // - read stdout and assume it's JSON
      const full = `${system}\n\nReturn ONLY JSON.\n\n${prompt}`;

      const argv = ["-p", full];
      if (args?.model) argv.unshift("--model", args.model);

      const { code, stdout, stderr } = await run(bin, argv);
      if (code !== 0) {
        throw new Error(`claude CLI failed (code=${code})\n${stderr || stdout}`);
      }

      const out = stdout.trim();
      // Best-effort: strip accidental code fences.
      const cleaned = out.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/i, "");
      return cleaned;
    }
  };
}

function run(cmd: string, argv: string[]): Promise<{ code: number; stdout: string; stderr: string }> {
  return new Promise((resolve) => {
    const p = spawn(cmd, argv, { stdio: ["ignore", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    p.stdout.on("data", (d) => (stdout += String(d)));
    p.stderr.on("data", (d) => (stderr += String(d)));
    p.on("close", (code) => resolve({ code: code ?? 0, stdout, stderr }));
  });
}

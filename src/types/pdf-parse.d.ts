declare module "pdf-parse" {
  type PdfParseResult = { text?: string } & Record<string, unknown>;
  export default function pdf(data: Buffer | Uint8Array): Promise<PdfParseResult>;
}

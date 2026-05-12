export type FormatMatchesErrorCode = "INVALID_INPUT" | "INVALID_FIXTURE_SHAPE";

export class FormatMatchesError extends Error {
  readonly code: FormatMatchesErrorCode;

  constructor(
    code: FormatMatchesErrorCode,
    message: string,
    options?: { cause?: unknown }
  ) {
    super(message, options?.cause !== undefined ? { cause: options.cause } : undefined);
    this.name = "FormatMatchesError";
    this.code = code;
  }
}

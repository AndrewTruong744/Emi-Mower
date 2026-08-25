export type ErrorPresentation = 'toast' | 'modal' | 'silent';
export type ErrorPriority = 'low' | 'normal' | 'high' | 'critical';

export type ErrorCode =
  | 'auth.sign_in_failed'
  | 'auth.session_failed'
  | 'auth.sign_out_failed'
  | 'zenoh.request_failed'
  | 'zenoh.command_failed'
  | 'zenoh.subscription_failed'
  | 'control.command_failed'
  | 'livestream.connection_failed'
  | 'telemetry.delayed'
  | 'telemetry.invalid_payload';

export interface AppError {
  id: string;
  code: ErrorCode;
  title: string;
  message: string;
  presentation: ErrorPresentation;
  priority: ErrorPriority;
  retryable: boolean;
  dedupeKey: string;
  count: number;
  occurredAt: number;
}

export interface ErrorDefinition {
  title: string;
  presentation: ErrorPresentation;
  priority: ErrorPriority;
  retryable: boolean;
}

export interface ReportErrorOptions {
  message?: string;
  dedupeKey?: string;
}

/** Expected input failures stay next to the relevant control rather than entering the global queue. */
export class InputValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'InputValidationError';
  }
}

export function isInputValidationError(error: unknown): boolean {
  return error instanceof InputValidationError;
}

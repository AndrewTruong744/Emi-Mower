import { useBoundStore } from '@/store/useBoundStore';
import { isOperationCancelled } from './operationCancelled';
import { ERROR_CATALOG } from './catalog';
import type { AppError, ErrorCode, ReportErrorOptions } from './types';

let nextErrorId = 0;

function getMessage(error: unknown): string {
  if (error instanceof Error && error.message) return error.message;
  if (typeof error === 'string' && error) return error;
  return 'Something went wrong. Please try again.';
}

/** Report a product-level operational error. Validation belongs with its input. */
export function reportAppError(
  code: ErrorCode,
  error: unknown,
  options: ReportErrorOptions = {}
): void {
  if (isOperationCancelled(error)) return;

  const definition = ERROR_CATALOG[code];
  const appError: AppError = {
    id: `${Date.now()}-${nextErrorId++}`,
    code,
    title: definition.title,
    message: options.message ?? getMessage(error),
    presentation: definition.presentation,
    priority: definition.priority,
    retryable: definition.retryable,
    dedupeKey: options.dedupeKey ?? code,
    count: 1,
    occurredAt: Date.now(),
  };

  useBoundStore.getState().reportError(appError);
}

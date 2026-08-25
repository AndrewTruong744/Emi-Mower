import { beforeEach, describe, expect, it } from '@jest/globals';
import { useBoundStore } from '@/store/useBoundStore';
import type { AppError } from '@/errors/types';

function makeError(overrides: Partial<AppError> = {}): AppError {
  return {
    id: 'error-1',
    code: 'zenoh.request_failed',
    title: 'Request failed',
    message: 'Zenoh is unavailable',
    presentation: 'toast',
    priority: 'normal',
    retryable: true,
    dedupeKey: 'zenoh.request_failed',
    count: 1,
    occurredAt: 1_000,
    ...overrides,
  };
}

describe('error store slice', () => {
  beforeEach(() => useBoundStore.getState().clearErrors());

  it('queues errors and dismisses the active error', () => {
    useBoundStore.getState().reportError(makeError());

    expect(useBoundStore.getState().errorQueue).toHaveLength(1);
    expect(useBoundStore.getState().errorQueue[0]).toMatchObject({
      title: 'Request failed',
      message: 'Zenoh is unavailable',
    });

    useBoundStore.getState().dismissError('error-1');
    expect(useBoundStore.getState().errorQueue).toEqual([]);
  });

  it('coalesces repeated errors and ignores silent errors', () => {
    useBoundStore.getState().reportError(makeError());
    useBoundStore.getState().reportError(makeError({ id: 'error-2', occurredAt: 2_000 }));
    useBoundStore.getState().reportError(
      makeError({
        id: 'error-3',
        code: 'telemetry.invalid_payload',
        presentation: 'silent',
        dedupeKey: 'telemetry.invalid_payload',
      })
    );

    expect(useBoundStore.getState().errorQueue).toEqual([
      expect.objectContaining({ id: 'error-1', count: 2, occurredAt: 2_000 }),
    ]);
  });

  it('caps distinct queued errors to prevent notification spam', () => {
    for (let index = 0; index < 6; index += 1) {
      useBoundStore.getState().reportError(
        makeError({
          id: `error-${index}`,
          dedupeKey: `request-${index}`,
          occurredAt: 1_000 + index,
        })
      );
    }

    expect(useBoundStore.getState().errorQueue).toHaveLength(5);
    expect(useBoundStore.getState().errorQueue.map((error) => error.id)).toEqual([
      'error-0',
      'error-1',
      'error-2',
      'error-3',
      'error-4',
    ]);
  });
});

import { beforeEach, describe, expect, it } from '@jest/globals';
import { useBoundStore } from '@/store/useBoundStore';

describe('bound store reset', () => {
  beforeEach(() => useBoundStore.getState().resetStore());

  it('clears user-scoped data and restores defaults', () => {
    useBoundStore.getState().setUser({
      user_id: 'user-1',
      email: 'user@example.com',
      displayName: 'User',
    });
    useBoundStore.getState().setMowers(['mower-1']);
    useBoundStore.getState().setThemePreference('dark');
    useBoundStore.getState().reportError({
      id: 'stale-error',
      code: 'zenoh.request_failed',
      title: 'Request failed',
      message: 'stale error',
      presentation: 'toast',
      priority: 'normal',
      retryable: true,
      dedupeKey: 'zenoh.request_failed',
      count: 1,
      occurredAt: Date.now(),
    });

    useBoundStore.getState().resetStore();

    expect(useBoundStore.getState()).toMatchObject({
      zenohEnabled: false,
      user_id: null,
      email: null,
      displayName: null,
      mowers: [],
      themePreference: 'system',
      errorQueue: [],
    });
  });
});

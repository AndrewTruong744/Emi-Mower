import { beforeEach, describe, expect, it } from '@jest/globals';
import { useBoundStore } from '@/store/useBoundStore';

describe('bound store reset', () => {
  beforeEach(() => useBoundStore.getState().resetStore());

  it('clears user-scoped data and restores defaults', () => {
    useBoundStore.getState().setAuthToken('firebase-token');
    useBoundStore.getState().setUser({
      user_id: 'user-1',
      email: 'user@example.com',
      displayName: 'User',
    });
    useBoundStore.getState().setMowers(['mower-1']);
    useBoundStore.getState().setThemePreference('dark');
    useBoundStore.getState().reportError(new Error('stale error'));

    useBoundStore.getState().resetStore();

    expect(useBoundStore.getState()).toMatchObject({
      idToken: null,
      user_id: null,
      email: null,
      displayName: null,
      mowers: [],
      themePreference: 'system',
      error: null,
    });
  });
});

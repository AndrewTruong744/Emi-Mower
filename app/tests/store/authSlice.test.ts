import { beforeEach, describe, expect, it } from '@jest/globals';
import { useBoundStore } from '@/store/useBoundStore';

describe('auth store slice', () => {
  beforeEach(() => useBoundStore.getState().resetStore());

  it('stores only the Firebase ID token and clears it', () => {
    useBoundStore.getState().setAuthToken('firebase');
    expect(useBoundStore.getState()).toMatchObject({
      idToken: 'firebase',
    });

    useBoundStore.getState().clearAuth();
    expect(useBoundStore.getState().idToken).toBeNull();
  });

  it('enables and disables Zenoh with a new generation for each lifecycle change', () => {
    const initialGeneration = useBoundStore.getState().authGeneration;

    useBoundStore.getState().enableZenoh();
    expect(useBoundStore.getState()).toMatchObject({
      zenohEnabled: true,
      authGeneration: initialGeneration + 1,
    });

    useBoundStore.getState().enableZenoh();
    expect(useBoundStore.getState().authGeneration).toBe(initialGeneration + 1);

    useBoundStore.getState().disableZenoh();
    expect(useBoundStore.getState()).toMatchObject({
      zenohEnabled: false,
      authGeneration: initialGeneration + 2,
    });
  });
});

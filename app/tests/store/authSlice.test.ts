import { beforeEach, describe, expect, it } from '@jest/globals';
import { useBoundStore } from '@/store/useBoundStore';

describe('auth store slice', () => {
  beforeEach(() => useBoundStore.getState().clearAuth());

  it('stores only the Firebase ID token and clears it', () => {
    useBoundStore.getState().setAuthToken('firebase');
    expect(useBoundStore.getState()).toMatchObject({
      idToken: 'firebase',
    });

    useBoundStore.getState().clearAuth();
    expect(useBoundStore.getState().idToken).toBeNull();
  });
});

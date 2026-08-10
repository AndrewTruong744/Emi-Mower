import { beforeEach, describe, expect, it } from '@jest/globals';
import { useBoundStore } from '@/store/useBoundStore';

describe('user store slice', () => {
  beforeEach(() => useBoundStore.getState().clearUser());

  it('stores and clears user data', () => {
    useBoundStore.getState().setUser({
      user_id: 'user-1',
      email: 'user@example.com',
      displayName: 'User',
    });
    expect(useBoundStore.getState()).toMatchObject({ user_id: 'user-1', displayName: 'User' });
    useBoundStore.getState().clearUser();
    expect(useBoundStore.getState().user_id).toBeNull();
  });
});

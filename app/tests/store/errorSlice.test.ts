import { beforeEach, describe, expect, it } from '@jest/globals';
import { useBoundStore } from '@/store/useBoundStore';

describe('error store slice', () => {
  beforeEach(() => useBoundStore.getState().clearError());

  it('stores normalized errors and clears them', () => {
    useBoundStore.getState().reportError(new Error('Zenoh is unavailable'), {
      source: 'zenoh',
      title: 'Connection failed',
    });

    expect(useBoundStore.getState().error).toMatchObject({
      title: 'Connection failed',
      message: 'Zenoh is unavailable',
      source: 'zenoh',
    });

    useBoundStore.getState().clearError();
    expect(useBoundStore.getState().error).toBeNull();
  });

  it('uses a safe fallback for unknown error values', () => {
    useBoundStore.getState().reportError(null);
    expect(useBoundStore.getState().error?.message).toBe(
      'Something went wrong. Please try again.'
    );
  });
});

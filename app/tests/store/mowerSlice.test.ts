import { beforeEach, describe, expect, it } from '@jest/globals';
import { useBoundStore } from '@/store/useBoundStore';

describe('mower store slice', () => {
  beforeEach(() => useBoundStore.getState().clearMowers());

  it('stores and clears the authenticated user mower IDs', () => {
    useBoundStore.getState().setMowers(['mower-1', 'mower-2']);
    expect(useBoundStore.getState().mowers).toEqual(['mower-1', 'mower-2']);

    useBoundStore.getState().clearMowers();
    expect(useBoundStore.getState().mowers).toEqual([]);
  });
});

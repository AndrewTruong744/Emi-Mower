import { beforeEach, describe, expect, it } from '@jest/globals';
import { useBoundStore } from '@/store/useBoundStore';

const boundary = [
  { x: -74.006, y: 40.7128 },
  { x: -74.0058, y: 40.7128 },
  { x: -74.0058, y: 40.713 },
];

describe('map store slice', () => {
  beforeEach(() => useBoundStore.getState().resetStore());

  it('tracks a cutting session, its local area image, pause state, and cancellation', () => {
    useBoundStore.getState().startMowingSession(boundary, 'file:///local/cutting-area-preview.png');

    expect(useBoundStore.getState()).toMatchObject({
      isSessionActive: true,
      isSessionPaused: false,
      cuttingBoundary: boundary,
      areaImageUri: 'file:///local/cutting-area-preview.png',
    });

    useBoundStore.getState().setSessionPaused(true);
    expect(useBoundStore.getState().isSessionPaused).toBe(true);

    useBoundStore.getState().cancelMowingSession();
    expect(useBoundStore.getState()).toMatchObject({
      isSessionActive: false,
      isSessionPaused: false,
      cuttingBoundary: [],
      areaImageUri: null,
    });
  });
});

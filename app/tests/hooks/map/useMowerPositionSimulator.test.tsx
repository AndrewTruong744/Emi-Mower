import { afterEach, beforeEach, describe, expect, it, jest } from '@jest/globals';
import { act, renderHook } from '@testing-library/react-native';
import { useMowerPositionSimulator } from '@/hooks/map/useMowerPositionSimulator';
import { useBoundStore } from '@/store/useBoundStore';

describe('useMowerPositionSimulator', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    useBoundStore.getState().resetStore();
    useBoundStore.getState().seedFakeMowers();
    return undefined;
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('updates mower coordinates only while an unpaused session is active', () => {
    useBoundStore.getState().startMowingSession(
      [
        { x: -74.006, y: 40.7128 },
        { x: -74.005, y: 40.7128 },
        { x: -74.005, y: 40.7138 },
      ],
      'file:///area.png'
    );
    const mowerId = useBoundStore.getState().mowers[0];
    const before = useBoundStore.getState().mowerPositions[mowerId];
    renderHook(() => useMowerPositionSimulator());

    act(() => jest.advanceTimersByTime(500));
    expect(useBoundStore.getState().mowerPositions[mowerId]).not.toEqual(before);

    act(() => useBoundStore.getState().setSessionPaused(true));
    const pausedPosition = useBoundStore.getState().mowerPositions[mowerId];
    act(() => jest.advanceTimersByTime(1_000));
    expect(useBoundStore.getState().mowerPositions[mowerId]).toEqual(pausedPosition);
  });
});

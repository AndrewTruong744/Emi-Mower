import { beforeEach, describe, expect, it } from '@jest/globals';
import { MOWER_TELEMETRY_MAX_SAMPLES } from '@/store/slices/mowerSlice';
import { useBoundStore } from '@/store/useBoundStore';

const sample = (timestamp: number, batteryPercentage = 80) => ({
  timestamp,
  latitude: 40.7128,
  longitude: -74.006,
  batteryPercentage,
  leftMotorSpeed: 0.6,
  leftMotorDirection: 1 as const,
  rightMotorSpeed: 0.5,
  rightMotorDirection: 1 as const,
  cuttingMotorSpeed: 2800,
  slippageDetected: false,
  imuData: null,
});

describe('mower store slice', () => {
  beforeEach(() => useBoundStore.getState().clearMowers());

  it('stores and clears the authenticated user mower IDs', () => {
    useBoundStore.getState().setMowers(['mower-1', 'mower-2']);
    expect(useBoundStore.getState().mowers).toEqual(['mower-1', 'mower-2']);

    useBoundStore.getState().clearMowers();
    expect(useBoundStore.getState().mowers).toEqual([]);
  });

  it('creates empty mower records and retains ordered live telemetry', () => {
    useBoundStore.getState().addMower('mower-1', 'Backyard Mower');

    const mower = useBoundStore.getState().mowerDetails['mower-1'];
    expect(mower).toEqual({
      uuid: 'mower-1',
      name: 'Backyard Mower',
      battery: null,
      state: 'unknown',
      health: 'unknown',
      telemetry: [],
    });
    useBoundStore.getState().appendTelemetryBatch({
      'mower-1': [sample(3), sample(1), sample(2), sample(2, 10)],
    });
    expect(useBoundStore.getState().mowerDetails['mower-1'].telemetry.map((item) => item.timestamp)).toEqual([1, 2, 3]);
    expect(useBoundStore.getState().mowerDetails['mower-1'].battery).toBe(80);
    expect(useBoundStore.getState().mowerPositions['mower-1']).toEqual({ x: -74.006, y: 40.7128 });
  });

  it('updates a live telemetry batch in one notification and ignores unknown mowers', () => {
    useBoundStore.getState().setMowers(['mower-1', 'mower-2', 'mower-3']);
    const listener = jest.fn();
    const unsubscribe = useBoundStore.subscribe(listener);

    useBoundStore.getState().appendTelemetryBatch({
      'mower-1': [sample(1)],
      'mower-2': [sample(1)],
      'mower-3': [sample(1)],
      unknown: [sample(1)],
    });
    unsubscribe();

    expect(listener).toHaveBeenCalledTimes(1);
    for (const uuid of useBoundStore.getState().mowers) {
      const telemetry = useBoundStore.getState().mowerDetails[uuid].telemetry;
      expect(telemetry).toHaveLength(1);
    }
    expect(useBoundStore.getState().mowerDetails.unknown).toBeUndefined();
  });
});

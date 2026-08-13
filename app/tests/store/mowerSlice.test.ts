import { beforeEach, describe, expect, it } from '@jest/globals';
import { MOWER_TELEMETRY_MAX_SAMPLES } from '@/store/slices/mowerSlice';
import { useBoundStore } from '@/store/useBoundStore';

describe('mower store slice', () => {
  beforeEach(() => useBoundStore.getState().clearMowers());

  it('stores and clears the authenticated user mower IDs', () => {
    useBoundStore.getState().setMowers(['mower-1', 'mower-2']);
    expect(useBoundStore.getState().mowers).toEqual(['mower-1', 'mower-2']);

    useBoundStore.getState().clearMowers();
    expect(useBoundStore.getState().mowers).toEqual([]);
  });

  it('creates detailed mower records and keeps telemetry in a 30-second queue', () => {
    useBoundStore.getState().addMower('mower-1', 'Backyard Mower');

    const mower = useBoundStore.getState().mowerDetails['mower-1'];
    expect(mower).toMatchObject({
      uuid: 'mower-1',
      name: 'Backyard Mower',
      state: expect.any(String),
      health: expect.any(String),
    });
    expect(mower.telemetry.at(-1)).toMatchObject({
      batteryPercentage: expect.any(Number),
      leftMotorSpeed: expect.any(Number),
      leftMotorDirection: expect.any(Number),
      rightMotorSpeed: expect.any(Number),
      rightMotorDirection: expect.any(Number),
      cuttingMotorSpeed: expect.any(Number),
      slippageDetected: expect.any(Boolean),
      imuData: {
        accelX: expect.any(Number),
        gyroY: expect.any(Number),
        magZ: expect.any(Number),
      },
    });
    expect(mower.telemetry).toHaveLength(MOWER_TELEMETRY_MAX_SAMPLES);

    for (let index = 0; index < MOWER_TELEMETRY_MAX_SAMPLES + 4; index += 1) {
      useBoundStore.getState().appendFakeTelemetry('mower-1');
    }

    expect(useBoundStore.getState().mowerDetails['mower-1'].telemetry).toHaveLength(
      MOWER_TELEMETRY_MAX_SAMPLES
    );
  });
});

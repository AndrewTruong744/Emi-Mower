import { afterEach, beforeEach, describe, expect, it, jest } from '@jest/globals';
import { initializeMowerTelemetrySubscription } from '@/zenoh/mowerTelemetrySubscription';
import { MowerTelemetryMessage, subscribeToMowerTelemetry } from '@/zenoh/mowerTelemetry';
import { useBoundStore } from '@/store/useBoundStore';

jest.mock('@/zenoh/mowerTelemetry', () => ({ subscribeToMowerTelemetry: jest.fn() }));
const mockSubscribeToMowerTelemetry = subscribeToMowerTelemetry as jest.Mock<
  (...args: any[]) => any
>;

const message = (mowerId: string, timestamp: number): MowerTelemetryMessage => ({
  mowerId,
  sample: {
    timestamp,
    latitude: 40.7128,
    longitude: -74.006,
    batteryPercentage: 80,
    leftMotorSpeed: 0.6,
    leftMotorDirection: 1,
    rightMotorSpeed: 0.6,
    rightMotorDirection: 1,
    cuttingMotorSpeed: 2800,
    slippageDetected: false,
    imuData: null,
  },
});

describe('mower telemetry subscription bootstrap', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    useBoundStore.getState().resetStore();
    useBoundStore.getState().startZenohSession();
    useBoundStore.getState().setMowers(['mower-1', 'mower-2']);
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('must finish declaring before authentication can continue and flushes only owned mower data', async () => {
    let resolveSubscription: ((cleanup: () => Promise<void>) => void) | undefined;
    let deliver: ((messages: MowerTelemetryMessage[]) => void) | undefined;
    mockSubscribeToMowerTelemetry.mockImplementation(
      (onTelemetry: (messages: MowerTelemetryMessage[]) => void) =>
        new Promise((resolve) => {
          deliver = onTelemetry;
          resolveSubscription = resolve;
        })
    );

    const ready = initializeMowerTelemetrySubscription(useBoundStore.getState().authGeneration);
    await Promise.resolve();
    expect(mockSubscribeToMowerTelemetry).toHaveBeenCalledTimes(1);

    let settled = false;
    void ready.then(() => {
      settled = true;
    });
    await Promise.resolve();
    expect(settled).toBe(false);

    resolveSubscription?.(jest.fn<() => Promise<void>>().mockResolvedValue(undefined));
    await ready;

    deliver?.([message('mower-1', 1), message('unknown', 1)]);
    jest.advanceTimersByTime(200);
    expect(useBoundStore.getState().mowerDetails['mower-1'].telemetry).toHaveLength(1);
    expect(useBoundStore.getState().mowerDetails.unknown).toBeUndefined();
  });
});

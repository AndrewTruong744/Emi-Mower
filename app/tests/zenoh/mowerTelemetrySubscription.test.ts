import { afterEach, beforeEach, describe, expect, it, jest } from '@jest/globals';
import { initializeMowerTelemetrySubscription } from '@/zenoh/mowerTelemetry';
import { isZenohOperationActive, zenohSubscribe } from '@/config/zenohClient';
import { reportAppError } from '@/errors/reporter';
import { useBoundStore } from '@/store/useBoundStore';

jest.mock('@/config/zenohClient', () => ({
  isZenohOperationActive: jest.fn(),
  zenohSubscribe: jest.fn(),
}));
jest.mock('@/errors/reporter', () => ({ reportAppError: jest.fn() }));
const mockZenohSubscribe = zenohSubscribe as jest.Mock<(...args: any[]) => any>;
const mockIsZenohOperationActive = isZenohOperationActive as jest.Mock<(...args: any[]) => any>;
const mockReportAppError = reportAppError as jest.Mock<(...args: any[]) => any>;

const message = (mowerId: string, timestamp: number) => ({
  mower_id: mowerId,
  timestamp: new Date(timestamp).toISOString(),
    latitude: 40.7128,
    longitude: -74.006,
    battery_percentage: 80,
    left_motor_speed: 0.6,
    left_motor_direction: 1,
    right_motor_speed: 0.6,
    right_motor_direction: 1,
    cutting_motor_speed: 2800,
    slippage_detected: false,
    imu_data: null,
});

describe('mower telemetry subscription bootstrap', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    useBoundStore.getState().resetStore();
    useBoundStore.getState().startZenohSession();
    useBoundStore.getState().setMowers(['mower-1', 'mower-2']);
    mockZenohSubscribe.mockReset();
    mockIsZenohOperationActive.mockReturnValue(true);
    mockReportAppError.mockReset();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('must finish declaring before authentication can continue and flushes only owned mower data', async () => {
    let resolveSubscription: ((cleanup: () => Promise<void>) => void) | undefined;
    let deliver: ((payload: string) => void) | undefined;
    mockZenohSubscribe.mockImplementation(
      (_key: string, onPayload: (payload: string) => void) =>
        new Promise((resolve) => {
          deliver = onPayload;
          resolveSubscription = resolve;
        })
    );

    const ready = initializeMowerTelemetrySubscription(useBoundStore.getState().authGeneration);
    await Promise.resolve();
    expect(mockZenohSubscribe).toHaveBeenCalledTimes(1);

    let settled = false;
    void ready.then(() => {
      settled = true;
    });
    await Promise.resolve();
    expect(settled).toBe(false);

    resolveSubscription?.(jest.fn<() => Promise<void>>().mockResolvedValue(undefined));
    await ready;

    deliver?.(JSON.stringify([message('mower-1', 1), message('unknown', 1)]));
    deliver?.('invalid');
    jest.advanceTimersByTime(200);
    expect(useBoundStore.getState().mowerDetails['mower-1'].telemetry).toHaveLength(1);
    expect(useBoundStore.getState().mowerDetails.unknown).toBeUndefined();
    expect(mockReportAppError).toHaveBeenCalledWith(
      'telemetry.invalid_payload',
      expect.objectContaining({ message: expect.stringContaining('not valid JSON') })
    );
  });
});

import { afterEach, beforeEach, describe, expect, it, jest } from '@jest/globals';
import { act, renderHook, waitFor } from '@testing-library/react-native';
import { useMowerTelemetrySubscription } from '@/hooks/api/mower/useMowerTelemetrySubscription';
import { MowerTelemetryMessage, subscribeToMowerTelemetry } from '@/zenoh/mowerTelemetry';
import { useBoundStore } from '@/store/useBoundStore';

jest.mock('@/zenoh/mowerTelemetry', () => ({ subscribeToMowerTelemetry: jest.fn() }));
const mockSubscribeToMowerTelemetry = subscribeToMowerTelemetry as jest.Mock<(...args: any[]) => any>;

const message = (mowerId: string, timestamp: number): MowerTelemetryMessage => ({
  mowerId,
  sample: {
    timestamp, latitude: 40.7128, longitude: -74.006, batteryPercentage: 80,
    leftMotorSpeed: 0.6, leftMotorDirection: 1, rightMotorSpeed: 0.6, rightMotorDirection: 1,
    cuttingMotorSpeed: 2800, slippageDetected: false, imuData: null,
  },
});

describe('useMowerTelemetrySubscription', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    useBoundStore.getState().resetStore();
    useBoundStore.getState().setAuthToken('token');
    useBoundStore.getState().setMowers(['mower-1', 'mower-2']);
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('subscribes once, flushes the active mower quickly, and excludes unknown mower messages', async () => {
    let deliver: ((messages: MowerTelemetryMessage[]) => void) | undefined;
    const unsubscribe = jest.fn<() => Promise<void>>().mockResolvedValue(undefined);
    mockSubscribeToMowerTelemetry.mockImplementation(async (onTelemetry: (messages: MowerTelemetryMessage[]) => void) => {
      deliver = onTelemetry;
      return unsubscribe;
    });
    const { unmount } = renderHook(() => useMowerTelemetrySubscription());
    await waitFor(() => expect(deliver).toBeDefined());

    act(() => deliver!([message('mower-1', 1), message('unknown', 1)]));
    act(() => jest.advanceTimersByTime(200));
    expect(useBoundStore.getState().mowerDetails['mower-1'].telemetry).toHaveLength(1);
    expect(useBoundStore.getState().mowerDetails.unknown).toBeUndefined();

    unmount();
    await waitFor(() => expect(unsubscribe).toHaveBeenCalledTimes(1));
  });
});

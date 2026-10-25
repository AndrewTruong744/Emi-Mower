import { beforeEach, describe, expect, it, jest } from '@jest/globals';
import {
  initializeMowerLivelinessSubscription,
  mowerIdFromLivelinessKey,
} from '@/zenoh/mowerLiveliness';
import { isZenohOperationActive, zenohSubscribeLiveliness } from '@/config/zenohClient';
import { useBoundStore } from '@/store/useBoundStore';

jest.mock('@/config/zenohClient', () => ({
  isZenohOperationActive: jest.fn(),
  zenohSubscribeLiveliness: jest.fn(),
}));

const mockIsActive = isZenohOperationActive as jest.Mock<(...args: any[]) => any>;
const mockSubscribe = zenohSubscribeLiveliness as jest.Mock<(...args: any[]) => any>;

describe('mower liveliness subscription', () => {
  beforeEach(() => {
    for (const call of mockSubscribe.mock.calls) call[2]?.();
    jest.clearAllMocks();
    useBoundStore.getState().clearMowers();
    useBoundStore.getState().setMowers(['mower-1']);
    mockIsActive.mockReturnValue(true);
    mockSubscribe.mockResolvedValue(undefined);
  });

  it('uses an exact owned route and updates only owned mowers', async () => {
    await initializeMowerLivelinessSubscription(4);

    expect(mockSubscribe).toHaveBeenCalledWith(
      'mower/mower-1/liveliness',
      expect.any(Function),
      expect.any(Function)
    );
    const handler = mockSubscribe.mock.calls[0][1];
    handler('mower/mower-1/liveliness', true);
    handler('mower/unowned/liveliness', true);
    handler('mower/mower-1/not-liveliness', true);
    expect(useBoundStore.getState().mowerDetails['mower-1'].connection).toBe('connected');

    handler('mower/mower-1/liveliness', false);
    expect(useBoundStore.getState().mowerDetails['mower-1'].connection).toBe('disconnected');
  });

  it('does not update state from a stale Zenoh session', async () => {
    await initializeMowerLivelinessSubscription(4);
    mockIsActive.mockReturnValue(false);
    mockSubscribe.mock.calls[0][1]('mower/mower-1/liveliness', true);

    expect(useBoundStore.getState().mowerDetails['mower-1'].connection).toBe('disconnected');
  });

  it('validates liveliness key shape', () => {
    expect(mowerIdFromLivelinessKey('mower/mower-1/liveliness')).toBe('mower-1');
    expect(mowerIdFromLivelinessKey('mower/a/b/liveliness')).toBeNull();
    expect(mowerIdFromLivelinessKey('mower/mower-1/telemetry')).toBeNull();
  });

  it('reuses a live declaration during fleet updates and replaces it after close', async () => {
    await initializeMowerLivelinessSubscription(7);
    await initializeMowerLivelinessSubscription(7);
    expect(mockSubscribe).toHaveBeenCalledTimes(1);
    mockSubscribe.mock.calls[0][2]();
    await initializeMowerLivelinessSubscription(7);
    expect(mockSubscribe).toHaveBeenCalledTimes(2);
  });

  it('subscribes to each newly owned mower without duplicating existing subscriptions', async () => {
    await initializeMowerLivelinessSubscription(8);
    useBoundStore.getState().addMower('mower-2');
    await initializeMowerLivelinessSubscription(8);
    expect(mockSubscribe).toHaveBeenCalledTimes(2);
    expect(mockSubscribe).toHaveBeenLastCalledWith(
      'mower/mower-2/liveliness', expect.any(Function), expect.any(Function)
    );
  });
});

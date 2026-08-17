import { beforeEach, describe, expect, it } from '@jest/globals';
import { act, renderHook } from '@testing-library/react-native';
import { createWrapper, mockedZenohQuery, resetHookState } from './testUtils';
import { useLiveKitConsume } from '@/hooks/api/mower/useLiveKitConsume';

describe('useLiveKitConsume', () => {
  beforeEach(resetHookState);

  it('requests viewer credentials through the mower LiveKit consume endpoint', async () => {
    mockedZenohQuery.mockResolvedValue({
      token: 'viewer-token',
      url: 'wss://livekit.test',
      expires_in: 3600,
    });
    const { result } = renderHook(() => useLiveKitConsume(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.mutateAsync(' mower-1 ');
    });

    expect(mockedZenohQuery).toHaveBeenCalledWith('mower/mower-1/livekit/consume', {});
  });

  it('rejects a missing mower without making a transport request', async () => {
    const { result } = renderHook(() => useLiveKitConsume(), { wrapper: createWrapper() });

    await expect(result.current.mutateAsync('  ')).rejects.toThrow('mower must be selected');
    expect(mockedZenohQuery).not.toHaveBeenCalled();
  });
});

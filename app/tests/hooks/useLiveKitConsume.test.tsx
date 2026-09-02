import { beforeEach, describe, expect, it } from '@jest/globals';
import { act, renderHook, waitFor } from '@testing-library/react-native';
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
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockedZenohQuery).toHaveBeenCalledWith('mower/mower-1/livekit/consume', {});
  });

  it('rejects a missing mower without making a transport request', async () => {
    const { result } = renderHook(() => useLiveKitConsume(), { wrapper: createWrapper() });

    await act(async () => {
      await expect(result.current.mutateAsync('  ')).rejects.toThrow('mower must be selected');
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(mockedZenohQuery).not.toHaveBeenCalled();
  });

  it('reports transport failures through the mutation error state', async () => {
    mockedZenohQuery.mockRejectedValueOnce(new Error('LiveKit unavailable'));
    const { result } = renderHook(() => useLiveKitConsume(), { wrapper: createWrapper() });

    await act(async () => {
      await expect(result.current.mutateAsync('mower-1')).rejects.toThrow('LiveKit unavailable');
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

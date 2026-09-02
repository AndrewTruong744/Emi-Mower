import { beforeEach, describe, expect, it } from '@jest/globals';
import { act, renderHook, waitFor } from '@testing-library/react-native';
import { createWrapper, mockedZenohQuery, resetHookState } from './testUtils';
import { useMowerCommand } from '@/hooks/api/mower/useMowerCommand';

describe('useMowerCommand', () => {
  beforeEach(resetHookState);

  it('queries the unified command route and preserves the command type', async () => {
    mockedZenohQuery.mockImplementation(async (_path, payload) => ({
      command_id: payload.command_id,
      status: 'accepted',
    }));
    const { result } = renderHook(() => useMowerCommand(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.mutateAsync({
        mowerId: ' mower-1 ',
        command: { type: 'set_mode', mode: 'auto' },
        commandId: 'command-1',
      });
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockedZenohQuery).toHaveBeenCalledWith('mower/mower-1/command', {
      command_id: 'command-1',
      type: 'set_mode',
      mode: 'auto',
    });
  });

  it('rejects a missing mower before attempting a query', async () => {
    const { result } = renderHook(() => useMowerCommand(), { wrapper: createWrapper() });

    await act(async () => {
      await expect(
        result.current.mutateAsync({ mowerId: ' ', command: { type: 'emergency_stop' } })
      ).rejects.toThrow('mower must be selected');
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(mockedZenohQuery).not.toHaveBeenCalled();
  });

  it('generates an id and surfaces a mower rejection', async () => {
    mockedZenohQuery.mockResolvedValueOnce({ status: 'rejected', reason: 'blade blocked' });
    const { result } = renderHook(() => useMowerCommand(), { wrapper: createWrapper() });

    await act(async () => {
      await expect(
        result.current.mutateAsync({ mowerId: 'mower-1', command: { type: 'emergency_stop' } })
      ).rejects.toThrow('blade blocked');
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(mockedZenohQuery).toHaveBeenCalledWith(
      'mower/mower-1/command',
      expect.objectContaining({ command_id: expect.any(String), type: 'emergency_stop' })
    );
  });
});

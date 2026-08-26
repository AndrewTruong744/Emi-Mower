import { beforeEach, describe, expect, it } from '@jest/globals';
import { act, renderHook } from '@testing-library/react-native';
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

    expect(mockedZenohQuery).toHaveBeenCalledWith('mower/mower-1/command', {
      command_id: 'command-1',
      type: 'set_mode',
      mode: 'auto',
    });
  });

  it('rejects a missing mower before attempting a query', async () => {
    const { result } = renderHook(() => useMowerCommand(), { wrapper: createWrapper() });

    await expect(
      result.current.mutateAsync({ mowerId: ' ', command: { type: 'emergency_stop' } })
    ).rejects.toThrow('mower must be selected');
    expect(mockedZenohQuery).not.toHaveBeenCalled();
  });
});

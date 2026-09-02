import { beforeEach, describe, expect, it } from '@jest/globals';
import { act, renderHook, waitFor } from '@testing-library/react-native';
import { createWrapper, mockedZenohPut, resetHookState } from './testUtils';
import { useJoystickCommand } from '@/hooks/api/mower/useJoystickCommand';

describe('useJoystickCommand', () => {
  beforeEach(resetHookState);

  it('publishes normalized joystick coordinates to the mower route', async () => {
    mockedZenohPut.mockResolvedValue(undefined);
    const { result } = renderHook(() => useJoystickCommand(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.mutateAsync({ mowerId: ' mower-1 ', x: 0.5, y: -0.25 });
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockedZenohPut).toHaveBeenCalledWith('mower/mower-1/joystick', { x: 0.5, y: -0.25 });
  });

  it('rejects a missing mower or an out-of-range command', async () => {
    const { result } = renderHook(() => useJoystickCommand(), { wrapper: createWrapper() });

    await act(async () => {
      await expect(result.current.mutateAsync({ mowerId: ' ', x: 0, y: 0 })).rejects.toThrow(
        'mower must be selected'
      );
    });
    await act(async () => {
      await expect(result.current.mutateAsync({ mowerId: 'mower-1', x: 1.1, y: 0 })).rejects.toThrow(
        'normalized between -1 and 1'
      );
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

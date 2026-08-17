import { beforeEach, describe, expect, it } from '@jest/globals';
import { act, renderHook, waitFor } from '@testing-library/react-native';
import { useMowers } from '@/hooks/mowers/useMowers';
import { useBoundStore } from '@/store/useBoundStore';

describe('useMowers', () => {
  beforeEach(() => {
    useBoundStore.getState().resetStore();
    useBoundStore.getState().setMowers(['mower-1', 'mower-2']);
  });

  it('uses the authenticated fleet, switches the displayed mower, and manages mower names', async () => {
    const { result } = renderHook(() => useMowers());

    await waitFor(() => expect(result.current.activeMower).not.toBeNull());
    expect(result.current.mowerOptions).toHaveLength(2);

    const secondMower = result.current.mowerOptions[1];
    act(() => result.current.selectMower(secondMower.uuid));
    expect(result.current.activeMower?.uuid).toBe(secondMower.uuid);

    act(() => expect(result.current.renameActiveMower('Garden Robot')).toEqual({ success: true }));
    expect(result.current.activeMower?.name).toBe('Garden Robot');

    act(() => expect(result.current.addMower('new-mower-uuid')).toEqual({ success: true }));
    expect(result.current.activeMower).toMatchObject({
      uuid: 'new-mower-uuid',
      name: 'Mower new-mowe',
    });
  });

  it('validates empty and duplicate mower UUIDs', async () => {
    const { result } = renderHook(() => useMowers());
    await waitFor(() => expect(result.current.activeMower).not.toBeNull());

    expect(result.current.addMower('   ')).toEqual({
      success: false,
      error: 'A mower UUID is required.',
    });
    expect(result.current.addMower(result.current.activeMower!.uuid)).toEqual({
      success: false,
      error: 'That mower is already in your fleet.',
    });
  });
});

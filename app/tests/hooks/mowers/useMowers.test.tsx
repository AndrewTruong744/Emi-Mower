import { mockedZenohQuery, resetHookState } from '../testUtils';
import { beforeEach, describe, expect, it, jest } from '@jest/globals';
import { act, renderHook, waitFor } from '@testing-library/react-native';
import { useMowers } from '@/hooks/mowers/useMowers';
import { useBoundStore } from '@/store/useBoundStore';
import { mockFirebaseUser } from '../../mocks/firebase';

jest.mock('@/zenoh/mowerTelemetry', () => ({
  initializeMowerTelemetrySubscription: jest
    .fn<(...args: any[]) => Promise<void>>()
    .mockResolvedValue(undefined),
}));
jest.mock('@/zenoh/mowerLiveliness', () => ({
  initializeMowerLivelinessSubscription: jest
    .fn<(...args: any[]) => Promise<void>>()
    .mockResolvedValue(undefined),
}));

describe('useMowers', () => {
  beforeEach(() => {
    resetHookState();
    useBoundStore
      .getState()
      .setUser({ user_id: mockFirebaseUser.uid, email: 'user@example.com', displayName: 'User' });
    mockedZenohQuery.mockImplementation(async (_path: string, payload: any) => ({
      user_id: mockFirebaseUser.uid,
      mower_id: payload.mower_id,
      new_owner_id: payload.new_owner_id,
    }));
    useBoundStore
      .getState()
      .setMowers(['a0f6f58e-ef97-4fa9-aede-002467ca11ed', '7c3d863b-5778-4ae6-9177-151d2f9f846d']);
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

    await act(async () =>
      expect(await result.current.addMower('c7ea8f21-7c9c-4d01-8a3b-a3efeaf0f9b0')).toMatchObject({
        success: true,
      })
    );
    expect(result.current.activeMower).toMatchObject({
      uuid: 'c7ea8f21-7c9c-4d01-8a3b-a3efeaf0f9b0',
      name: 'Mower c7ea8f21',
    });
  });

  it('validates empty and duplicate mower UUIDs', async () => {
    const { result } = renderHook(() => useMowers());
    await waitFor(() => expect(result.current.activeMower).not.toBeNull());

    expect(await result.current.addMower('   ')).toEqual({
      success: false,
      error: 'Enter a valid mower UUID.',
    });
    expect(await result.current.addMower(result.current.activeMower!.uuid)).toEqual({
      success: false,
      error: 'That mower is already in your fleet.',
    });
  });
});

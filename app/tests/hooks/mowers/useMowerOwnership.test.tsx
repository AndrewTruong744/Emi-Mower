import { mockedZenohQuery, resetHookState } from '../testUtils';
import { beforeEach, describe, expect, it, jest } from '@jest/globals';
import { act, renderHook } from '@testing-library/react-native';
import { useMowerOwnership } from '@/hooks/mowers/useMowerOwnership';
import { useBoundStore } from '@/store/useBoundStore';
import { initializeMowerTelemetrySubscription } from '@/zenoh/mowerTelemetry';
import { initializeMowerLivelinessSubscription } from '@/zenoh/mowerLiveliness';
import { loginUser } from '@/zenoh/UserLogin';
import { mockFirebaseUser } from '../../mocks/firebase';

jest.mock('@/zenoh/mowerTelemetry', () => ({
  initializeMowerTelemetrySubscription: jest.fn<() => Promise<void>>().mockResolvedValue(undefined),
}));
jest.mock('@/zenoh/mowerLiveliness', () => ({
  initializeMowerLivelinessSubscription: jest
    .fn<() => Promise<void>>()
    .mockResolvedValue(undefined),
}));
jest.mock('@/zenoh/UserLogin', () => ({ loginUser: jest.fn() }));
const mockLogin = loginUser as jest.MockedFunction<typeof loginUser>;
const mowerId = 'c7ea8f21-7c9c-4d01-8a3b-a3efeaf0f9b0';

describe('backend-confirmed mower ownership', () => {
  beforeEach(() => {
    resetHookState();
    useBoundStore
      .getState()
      .setUser({ user_id: mockFirebaseUser.uid, email: 'user@example.com', displayName: 'User' });
  });

  it('rejects invalid UUIDs locally and nonexistent/already-owned mowers through the backend', async () => {
    const { result } = renderHook(useMowerOwnership);
    expect(await result.current.addMower('garbage')).toMatchObject({
      success: false,
      error: 'Enter a valid mower UUID.',
    });
    expect(mockedZenohQuery).not.toHaveBeenCalled();
    for (const detail of [
      'No registered mower exists with this UUID',
      'This mower already belongs to an account',
    ]) {
      mockedZenohQuery.mockRejectedValueOnce(new Error(JSON.stringify({ status: 404, detail })));
      await act(async () => {
        expect(await result.current.addMower(mowerId)).toEqual({ success: false, error: detail });
      });
      expect(useBoundStore.getState().mowers).toEqual([]);
    }
  });

  it('waits for confirmation before adding a mower and starts first-mower subscriptions', async () => {
    let confirm!: (value: unknown) => void;
    mockedZenohQuery.mockReturnValueOnce(
      new Promise((resolve) => {
        confirm = resolve;
      })
    );
    const { result } = renderHook(useMowerOwnership);
    let saving!: ReturnType<typeof result.current.addMower>;
    await act(async () => {
      saving = result.current.addMower(` ${mowerId.toUpperCase()} `);
    });
    expect(result.current.isPending).toBe(true);
    expect(useBoundStore.getState().mowers).toEqual([]);
    expect(await result.current.addMower(mowerId)).toMatchObject({ success: false });
    expect(mockedZenohQuery).toHaveBeenCalledTimes(1);
    expect(mockedZenohQuery).toHaveBeenCalledWith('user/add_mower', {
      id_token: 'firebase-token',
      mower_id: mowerId,
    });
    await act(async () => {
      confirm({ user_id: mockFirebaseUser.uid, mower_id: mowerId });
      expect(await saving).toMatchObject({ success: true });
    });
    expect(useBoundStore.getState().mowers).toEqual([mowerId]);
    expect(initializeMowerTelemetrySubscription).toHaveBeenCalled();
    expect(initializeMowerLivelinessSubscription).toHaveBeenCalled();
  });

  it('keeps mowers on backend failure and removes only the confirmed mower after transfer', async () => {
    useBoundStore.getState().setMowers([mowerId, 'another-mower']);
    const { result } = renderHook(useMowerOwnership);
    mockedZenohQuery.mockRejectedValueOnce(new Error('Recipient was not found'));
    await act(async () => {
      expect(await result.current.transferMower(mowerId, 'missing')).toMatchObject({
        success: false,
      });
    });
    expect(useBoundStore.getState().mowers).toContain(mowerId);
    mockedZenohQuery.mockResolvedValueOnce({
      user_id: mockFirebaseUser.uid,
      mower_id: mowerId,
      new_owner_id: 'recipient',
    });
    await act(async () => {
      expect(await result.current.transferMower(mowerId, 'recipient')).toMatchObject({
        success: true,
      });
    });
    expect(mockedZenohQuery).toHaveBeenLastCalledWith('user/transfer_mower', {
      id_token: 'firebase-token',
      mower_id: mowerId,
      new_owner_id: 'recipient',
    });
    expect(useBoundStore.getState().mowers).toEqual(['another-mower']);
    expect(useBoundStore.getState().mowerDetails[mowerId]).toBeUndefined();
  });

  it('removes a confirmed mower from local details, selection and map positions', async () => {
    useBoundStore.getState().setMowers([mowerId]);
    mockedZenohQuery.mockResolvedValueOnce({ user_id: mockFirebaseUser.uid, mower_id: mowerId });
    const { result } = renderHook(useMowerOwnership);
    await act(async () => {
      expect(await result.current.removeMower(mowerId)).toMatchObject({ success: true });
    });
    expect(mockedZenohQuery).toHaveBeenCalledWith('user/remove_mower', {
      id_token: 'firebase-token',
      mower_id: mowerId,
    });
    expect(useBoundStore.getState().mowers).toEqual([]);
    expect(useBoundStore.getState().selectedMowerUuid).toBeNull();
    expect(useBoundStore.getState().mowerDetails).toEqual({});
    expect(useBoundStore.getState().mowerPositions).toEqual({});
  });

  it('does not apply a response to a replacement login or accept a mismatched mower', async () => {
    mockedZenohQuery.mockResolvedValueOnce({ user_id: mockFirebaseUser.uid, mower_id: 'wrong' });
    const { result } = renderHook(useMowerOwnership);
    await act(async () => {
      expect(await result.current.addMower(mowerId)).toMatchObject({ success: false });
    });
    mockedZenohQuery.mockImplementationOnce(async () => {
      useBoundStore.getState().resetStore();
      return { user_id: mockFirebaseUser.uid, mower_id: mowerId };
    });
    await act(async () => {
      expect(await result.current.addMower(mowerId)).toMatchObject({ success: false });
    });
    expect(useBoundStore.getState().mowers).toEqual([]);
  });

  it('refreshes from the authoritative fleet, dropping old UI-only entries', async () => {
    useBoundStore.getState().setMowers(['made-up']);
    mockLogin.mockResolvedValueOnce({
      id: mockFirebaseUser.uid,
      email: 'user@example.com',
      name: 'User',
      mowers: [mowerId],
    });
    const { result } = renderHook(useMowerOwnership);
    await act(async () => {
      expect(await result.current.refreshFleet()).toMatchObject({ success: true });
    });
    expect(useBoundStore.getState().mowers).toEqual([mowerId]);
  });
});

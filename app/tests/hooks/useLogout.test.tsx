import { beforeEach, describe, expect, it } from '@jest/globals';
import { act, renderHook } from '@testing-library/react-native';
import { mockGoogleSignin } from '../mocks/google-signin';
import { mockFirebaseAuth } from '../mocks/firebase';
import { useBoundStore } from '@/store/useBoundStore';
import { mockedCloseZenoh, resetHookState } from './testUtils';
import { useLogout } from '@/hooks/useLogout';
import { queryClient } from '@/config/queryClient';

describe('useLogout', () => {
  beforeEach(resetHookState);

  it('keeps the current screen while Firebase sign-out is pending, then clears local state', async () => {
    let resolveFirebaseSignOut: (() => void) | undefined;
    mockFirebaseAuth.signOut.mockImplementationOnce(
      () =>
        new Promise<void>((resolve) => {
          resolveFirebaseSignOut = resolve;
        })
    );
    useBoundStore.getState().setAuthStatus('authenticated');
    useBoundStore.getState().setUser({
      user_id: 'user-1',
      email: 'user@example.com',
      displayName: 'User',
    });
    queryClient.setQueryData(['telemetry-history', 'old-account'], { points: [1] });

    const { result } = renderHook(() => useLogout());
    let logoutPromise: Promise<void> | undefined;
    act(() => {
      logoutPromise = result.current.logout();
    });

    expect(useBoundStore.getState()).toMatchObject({
      authStatus: 'signingOut',
      zenohEnabled: false,
    });
    expect(queryClient.getQueryData(['telemetry-history', 'old-account'])).toBeUndefined();

    await act(async () => {
      resolveFirebaseSignOut?.();
      await logoutPromise;
    });

    expect(mockGoogleSignin.signOut).toHaveBeenCalled();
    expect(mockFirebaseAuth.signOut).toHaveBeenCalled();
    expect(result.current.isLoading).toBe(false);
    expect(useBoundStore.getState()).toMatchObject({
      authStatus: 'signedOut',
      user_id: null,
    });
  });

  it('restores the authenticated lifecycle when Firebase sign-out fails', async () => {
    mockFirebaseAuth.signOut.mockRejectedValueOnce(new Error('sign-out failed'));
    useBoundStore.getState().setAuthStatus('authenticated');

    const { result } = renderHook(() => useLogout());
    await act(async () => result.current.logout());

    expect(result.current.error).toBe('sign-out failed');
    expect(useBoundStore.getState()).toMatchObject({
      authStatus: 'authenticated',
      zenohEnabled: true,
    });
  });

  it('waits for Zenoh teardown before clearing state for the next login', async () => {
    let finishTeardown: (() => void) | undefined;
    mockedCloseZenoh.mockImplementationOnce(
      () =>
        new Promise<void>((resolve) => {
          finishTeardown = resolve;
        })
    );
    useBoundStore.getState().setAuthStatus('authenticated');

    const { result } = renderHook(() => useLogout());
    let logoutPromise: Promise<void> | undefined;
    act(() => {
      logoutPromise = result.current.logout();
    });
    await act(async () => {
      await Promise.resolve();
    });

    expect(mockedCloseZenoh).toHaveBeenCalledTimes(1);
    expect(useBoundStore.getState()).toMatchObject({
      authStatus: 'signingOut',
    });

    await act(async () => {
      finishTeardown?.();
      await logoutPromise;
    });
    expect(useBoundStore.getState().authStatus).toBe('signedOut');
  });
});

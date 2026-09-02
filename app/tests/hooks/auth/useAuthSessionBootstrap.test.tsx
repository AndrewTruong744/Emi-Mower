import { act, renderHook } from '@testing-library/react-native';
import { beforeEach, describe, expect, it, jest } from '@jest/globals';
import { mockFirebaseAuth, mockFirebaseUser } from '../../mocks/firebase';
import { useBoundStore } from '@/store/useBoundStore';
import { useAuthSessionBootstrap } from '@/hooks/auth/useAuthSessionBootstrap';
import { closeZenoh, isZenohOperationActive } from '@/config/zenohClient';
import { onAuthStateChanged } from '@react-native-firebase/auth';
import { loginUser } from '@/zenoh/UserLogin';
import { initializeMowerTelemetrySubscription } from '@/zenoh/mowerTelemetry';
import { reportAppError } from '@/errors/reporter';

jest.mock('@react-native-firebase/auth', () => ({
  onAuthStateChanged: jest.fn(),
}));
jest.mock('@/config/zenohClient', () => ({
  closeZenoh: jest.fn<(...args: any[]) => any>().mockResolvedValue(undefined),
  isZenohOperationActive: jest.fn(),
}));
jest.mock('@/zenoh/UserLogin', () => ({ loginUser: jest.fn() }));
jest.mock('@/zenoh/mowerTelemetry', () => ({
  initializeMowerTelemetrySubscription: jest.fn(),
}));
jest.mock('@/errors/reporter', () => ({ reportAppError: jest.fn() }));

const mockAuthStateChanged = onAuthStateChanged as jest.Mock<(...args: any[]) => any>;
const mockCloseZenoh = closeZenoh as jest.Mock<(...args: any[]) => any>;
const mockIsActive = isZenohOperationActive as jest.Mock<(...args: any[]) => any>;
const mockLoginUser = loginUser as jest.Mock<(...args: any[]) => any>;
const mockInitializeTelemetry = initializeMowerTelemetrySubscription as jest.Mock<
  (...args: any[]) => any
>;
const mockReportAppError = reportAppError as jest.Mock<(...args: any[]) => any>;

let authListener: ((user: typeof mockFirebaseUser | null) => Promise<void>) | undefined;

describe('useAuthSessionBootstrap', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useBoundStore.getState().resetStore();
    mockAuthStateChanged.mockImplementation((_auth, listener) => {
      authListener = listener;
      return jest.fn();
    });
    mockIsActive.mockReturnValue(true);
    mockLoginUser.mockResolvedValue({
      id: 'user-1',
      email: 'user@example.com',
      name: 'User One',
      mowers: ['mower-1'],
    });
    mockInitializeTelemetry.mockResolvedValue(undefined);
  });

  it('clears the authenticated session when Firebase reports signed out', async () => {
    useBoundStore.getState().setUser({
      user_id: 'old-user',
      email: 'old@example.com',
      displayName: 'Old User',
    });
    const { unmount } = renderHook(() => useAuthSessionBootstrap());

    await act(async () => {
      await authListener?.(null);
    });

    expect(mockCloseZenoh).toHaveBeenCalledTimes(1);
    expect(useBoundStore.getState()).toMatchObject({
      authStatus: 'signedOut',
      user_id: null,
    });
    unmount();
  });

  it('does not tear down twice when explicit logout already owns the barrier', async () => {
    renderHook(() => useAuthSessionBootstrap());
    useBoundStore.getState().setAuthStatus('signingOut');

    await act(async () => {
      await authListener?.(null);
    });

    expect(mockCloseZenoh).not.toHaveBeenCalled();
  });

  it('logs in, publishes the user state, and waits for telemetry setup', async () => {
    renderHook(() => useAuthSessionBootstrap());

    await act(async () => {
      await authListener?.(mockFirebaseUser);
    });

    expect(mockLoginUser).toHaveBeenCalledTimes(1);
    expect(mockInitializeTelemetry).toHaveBeenCalledTimes(1);
    expect(useBoundStore.getState()).toMatchObject({
      authStatus: 'authenticated',
      user_id: 'user-1',
      email: 'user@example.com',
      displayName: 'User One',
      mowers: ['mower-1'],
    });
  });

  it('resets state and reports an active-session login failure', async () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => undefined);
    mockLoginUser.mockRejectedValueOnce(new Error('login unavailable'));
    renderHook(() => useAuthSessionBootstrap());

    await act(async () => {
      await authListener?.(mockFirebaseUser);
    });

    expect(mockCloseZenoh).toHaveBeenCalled();
    expect(mockReportAppError).toHaveBeenCalledWith('auth.sign_in_failed', expect.any(Error));
    expect(consoleError).toHaveBeenCalledWith(
      'Error establishing authenticated Zenoh session:',
      expect.any(Error)
    );
    expect(useBoundStore.getState().authStatus).toBe('signedOut');
    consoleError.mockRestore();
  });

  it('ignores a stale-session failure without reporting or resetting the new session', async () => {
    mockLoginUser.mockRejectedValueOnce(new Error('stale login failure'));
    mockIsActive.mockReturnValue(false);
    renderHook(() => useAuthSessionBootstrap());

    await act(async () => {
      await authListener?.(mockFirebaseUser);
    });

    expect(mockCloseZenoh).not.toHaveBeenCalled();
    expect(mockReportAppError).not.toHaveBeenCalled();
  });

  it('handles Firebase listener setup failures', () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => undefined);
    mockAuthStateChanged.mockImplementationOnce(() => {
      throw new Error('Firebase unavailable');
    });

    renderHook(() => useAuthSessionBootstrap());

    expect(mockReportAppError).toHaveBeenCalledWith('auth.session_failed', expect.any(Error));
    expect(useBoundStore.getState().authStatus).toBe('signedOut');
    consoleError.mockRestore();
  });
});

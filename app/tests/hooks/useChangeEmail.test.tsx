import { beforeEach, describe, expect, it } from '@jest/globals';
import { act, renderHook } from '@testing-library/react-native';
import { mockGoogleSignin } from '../mocks/google-signin';
import { resetHookState, silenceExpectedConsoleError } from './testUtils';
import { useChangeEmail } from '@/hooks/useChangeEmail';

describe('useChangeEmail', () => {
  beforeEach(resetHookState);

  it('gets replacement Google/Firebase credentials', async () => {
    const { result } = renderHook(() => useChangeEmail());
    let tokens;
    await act(async () => {
      tokens = await result.current.triggerChangeEmail();
    });
    expect(tokens).toEqual({
      idToken: 'firebase-token',
      email: 'user@example.com',
    });
    expect(mockGoogleSignin.hasPlayServices).toHaveBeenCalled();
  });

  it('falls back to Firebase handling without a server auth code', async () => {
    mockGoogleSignin.signIn.mockResolvedValueOnce({ type: 'success', data: {} });
    const { result } = renderHook(() => useChangeEmail());
    await act(async () => {
      await expect(result.current.triggerChangeEmail()).resolves.toMatchObject({
        idToken: 'firebase-token',
      });
    });
  });

  it('handles cancellation and missing Google tokens', async () => {
    const consoleError = silenceExpectedConsoleError();
    mockGoogleSignin.signIn.mockResolvedValueOnce({ type: 'cancelled' });
    const cancelled = renderHook(() => useChangeEmail());
    await act(async () => {
      await expect(cancelled.result.current.triggerChangeEmail()).rejects.toThrow(
        'Google Sign-In was cancelled or failed.'
      );
    });
    expect(cancelled.result.current.error).toBe('Google Sign-In was cancelled or failed.');

    mockGoogleSignin.getTokens.mockResolvedValueOnce({ idToken: null, accessToken: 'access-token' });
    const missingIdToken = renderHook(() => useChangeEmail());
    await act(async () => {
      await expect(missingIdToken.result.current.triggerChangeEmail()).rejects.toThrow(
        'Could not retrieve tokens from Google.'
      );
    });

    mockGoogleSignin.getTokens.mockResolvedValueOnce({ idToken: 'id-token', accessToken: null });
    const missingAccessToken = renderHook(() => useChangeEmail());
    await act(async () => {
      await expect(missingAccessToken.result.current.triggerChangeEmail()).rejects.toThrow(
        'Could not retrieve tokens from Google.'
      );
    });
    expect(consoleError).toHaveBeenCalledTimes(3);
    consoleError.mockRestore();
  });
});

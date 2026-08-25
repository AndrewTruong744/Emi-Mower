import { beforeEach, describe, expect, it } from '@jest/globals';
import { act, renderHook, waitFor } from '@testing-library/react-native';
import { useBoundStore } from '@/store/useBoundStore';
import { mockGoogleSignin } from '../mocks/google-signin';
import { resetHookState } from './testUtils';
import { useGoogleAuth } from '@/hooks/useGoogleAuth';

describe('useGoogleAuth', () => {
  beforeEach(resetHookState);

  it('defers app authentication until the Firebase listener completes Zenoh login', async () => {
    const { result } = renderHook(() => useGoogleAuth());
    await act(async () => result.current.signInWithGoogle());
    expect(useBoundStore.getState()).toMatchObject({
      idToken: null,
      user_id: null,
      authStatus: 'signedOut',
    });
  });

  it('handles cancelled sign-in', async () => {
    const { result } = renderHook(() => useGoogleAuth());
    mockGoogleSignin.signIn.mockRejectedValueOnce(new Error('Cancelled'));
    await act(async () => {
      await expect(result.current.signInWithGoogle()).rejects.toThrow('Cancelled');
    });
    await waitFor(() => expect(result.current.error).toBe('Cancelled'));
  });

  it('handles missing tokens', async () => {
    mockGoogleSignin.getTokens.mockResolvedValueOnce({ idToken: null, accessToken: 'access-token' });
    const { result } = renderHook(() => useGoogleAuth());
    await act(async () => {
      await expect(result.current.signInWithGoogle()).rejects.toThrow(
        'No ID Token received from Google Sign-In.'
      );
    });
    mockGoogleSignin.getTokens.mockResolvedValueOnce({ idToken: 'id-token', accessToken: null });
    await act(async () => {
      await expect(result.current.signInWithGoogle()).rejects.toThrow(
        'No Access Token received from Google Sign-In.'
      );
    });
  });
});

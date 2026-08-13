import { beforeEach, describe, expect, it } from '@jest/globals';
import { act, renderHook, waitFor } from '@testing-library/react-native';
import { useBoundStore } from '@/store/useBoundStore';
import { mockFirebaseAuth, mockFirebaseUser } from '../mocks/firebase';
import { mockGoogleSignin } from '../mocks/google-signin';
import { resetHookState } from './testUtils';
import { useGoogleAuth } from '@/hooks/useGoogleAuth';

describe('useGoogleAuth', () => {
  beforeEach(resetHookState);

  it('stores the authenticated Firebase user', async () => {
    const { result } = renderHook(() => useGoogleAuth());
    await act(async () => result.current.signInWithGoogle());
    expect(useBoundStore.getState()).toMatchObject({
      idToken: 'firebase-token',
      user_id: 'firebase-user',
    });
  });

  it('handles cancelled sign-in and invalid Firebase claims', async () => {
    const { result } = renderHook(() => useGoogleAuth());
    mockGoogleSignin.signIn.mockRejectedValueOnce(new Error('Cancelled'));
    await act(async () => {
      await expect(result.current.signInWithGoogle()).rejects.toThrow('Cancelled');
    });
    await waitFor(() => expect(result.current.error).toBe('Cancelled'));

    mockFirebaseUser.getIdToken.mockResolvedValueOnce('header.invalid-json.signature');
    await act(async () => result.current.signInWithGoogle());
    expect(useBoundStore.getState().user_id).toBe('firebase-user');
  });

  it('decodes Firebase claims with the native base64 fallback', async () => {
    const payload = btoa(
      JSON.stringify({ sub: 'decoded-user', email: 'decoded@example.com', name: 'Decoded' })
    );
    const token = `header.${payload}.signature`;
    mockFirebaseUser.getIdToken.mockResolvedValueOnce(token);
    const { result } = renderHook(() => useGoogleAuth());
    await act(async () => result.current.signInWithGoogle());
    expect(useBoundStore.getState()).toMatchObject({
      user_id: 'decoded-user',
      email: 'decoded@example.com',
      displayName: 'Decoded',
    });

    const originalAtob = globalThis.atob;
    Object.defineProperty(globalThis, 'atob', { configurable: true, value: undefined });
    try {
      mockFirebaseUser.getIdToken.mockResolvedValueOnce(token);
      await act(async () => result.current.signInWithGoogle());
      expect(useBoundStore.getState().user_id).toBe('decoded-user');
    } finally {
      Object.defineProperty(globalThis, 'atob', { configurable: true, value: originalAtob });
    }
  });

  it('handles missing tokens and sign-out failures', async () => {
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
    useBoundStore.getState().setAuthToken('stale-token');
    useBoundStore.getState().setUser({
      user_id: 'stale-user',
      email: 'stale@example.com',
      displayName: 'Stale User',
    });
    useBoundStore.getState().setMowers(['stale-mower']);
    mockFirebaseAuth.signOut.mockRejectedValueOnce(new Error('sign-out failed'));
    await act(async () => result.current.signOut());
    await waitFor(() => expect(result.current.error).toBe('sign-out failed'));
    expect(useBoundStore.getState()).toMatchObject({
      idToken: null,
      user_id: null,
      email: null,
      displayName: null,
      mowers: [],
    });
  });
});

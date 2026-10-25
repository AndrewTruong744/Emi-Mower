import { beforeEach, describe, expect, it } from '@jest/globals';
import { act, renderHook } from '@testing-library/react-native';
import { deleteApp, initializeApp } from '@react-native-firebase/app';
import {
  mockFirebaseAuth,
  mockFirebaseUser,
  mockSecondaryAuth,
  mockSecondaryUser,
  firebaseApp,
} from '../mocks/firebase';
import { mockGoogleSignin } from '../mocks/google-signin';
import { resetHookState } from './testUtils';
import { useChangeEmail } from '@/hooks/useChangeEmail';

describe('useChangeEmail', () => {
  beforeEach(resetHookState);

  it('verifies the replacement separately and keeps the active identity until completion', async () => {
    const { result } = renderHook(() => useChangeEmail());
    let proof!: Awaited<ReturnType<typeof result.current.triggerChangeEmail>>;
    await act(async () => {
      proof = await result.current.triggerChangeEmail();
    });
    expect(proof).toMatchObject({
      originalIdToken: 'firebase-token',
      idToken: 'replacement-token',
      email: 'replacement@example.com',
      userId: 'replacement-user',
    });
    expect(mockSecondaryAuth.signInWithCredential).toHaveBeenCalledTimes(1);
    expect(initializeApp).toHaveBeenCalledWith(
      {
        ...firebaseApp.options,
        databaseURL: '',
        storageBucket: '',
        messagingSenderId: '',
      },
      expect.objectContaining({ automaticDataCollectionEnabled: false })
    );
    expect(mockGoogleSignin.signOut).toHaveBeenCalledTimes(1);
    expect(mockGoogleSignin.signOut.mock.invocationCallOrder[0]).toBeLessThan(
      mockGoogleSignin.signIn.mock.invocationCallOrder[0]
    );
    expect(mockFirebaseAuth.signOut).not.toHaveBeenCalled();
    expect(mockFirebaseAuth.signInWithCredential).not.toHaveBeenCalled();
    expect(mockFirebaseAuth.currentUser).toBe(mockFirebaseUser);
    await act(async () => {
      await proof.complete();
      await proof.cleanup();
    });
    expect(mockFirebaseAuth.signInWithCredential).toHaveBeenCalledTimes(1);
    expect(mockSecondaryAuth.signOut).toHaveBeenCalled();
    expect(deleteApp).toHaveBeenCalled();
  });

  it('preserves configured optional Firebase services in the temporary app', async () => {
    Object.assign(firebaseApp.options, {
      databaseURL: 'https://test-project-default-rtdb.firebaseio.com',
      storageBucket: 'test-project.firebasestorage.app',
      messagingSenderId: '1234',
    });
    const { result } = renderHook(() => useChangeEmail());
    await act(async () => {
      const proof = await result.current.triggerChangeEmail();
      await proof.cleanup();
    });
    expect(initializeApp).toHaveBeenCalledWith(firebaseApp.options, expect.any(Object));
  });

  it('handles null native service options without requiring a database', async () => {
    Object.assign(firebaseApp.options, {
      databaseURL: null,
      storageBucket: null,
      messagingSenderId: null,
    });
    const { result } = renderHook(() => useChangeEmail());
    await act(async () => {
      const proof = await result.current.triggerChangeEmail();
      await proof.cleanup();
    });
    expect(initializeApp).toHaveBeenCalledWith(
      expect.objectContaining({ databaseURL: '', storageBucket: '', messagingSenderId: '' }),
      expect.any(Object)
    );
  });

  it('rejects choosing the current account and cleans up the secondary session', async () => {
    mockSecondaryUser.uid = mockFirebaseUser.uid;
    const { result } = renderHook(() => useChangeEmail());
    await act(async () => {
      await expect(result.current.triggerChangeEmail()).rejects.toThrow(
        'Choose a different Google account'
      );
    });
    expect(mockFirebaseAuth.signInWithCredential).not.toHaveBeenCalled();
    expect(mockSecondaryAuth.signOut).toHaveBeenCalled();
    expect(deleteApp).toHaveBeenCalled();
  });

  it('handles cancellation and missing Google tokens without changing the active identity', async () => {
    mockGoogleSignin.signIn.mockResolvedValueOnce({ type: 'cancelled' });
    const { result } = renderHook(() => useChangeEmail());
    await act(async () => {
      await expect(result.current.triggerChangeEmail()).rejects.toThrow('cancelled');
    });
    mockGoogleSignin.getTokens.mockResolvedValueOnce({ idToken: null, accessToken: 'access' });
    await act(async () => {
      await expect(result.current.triggerChangeEmail()).rejects.toThrow('retrieve tokens');
    });
    expect(mockFirebaseAuth.signInWithCredential).not.toHaveBeenCalled();
    expect(mockFirebaseAuth.signOut).not.toHaveBeenCalled();
    expect(mockSecondaryAuth.signOut).toHaveBeenCalled();
  });

  it('refuses to overwrite a primary identity that changed during the chooser', async () => {
    const { result } = renderHook(() => useChangeEmail());
    let proof!: Awaited<ReturnType<typeof result.current.triggerChangeEmail>>;
    await act(async () => {
      proof = await result.current.triggerChangeEmail();
    });
    mockFirebaseAuth.currentUser = null;
    await expect(proof.complete()).rejects.toThrow('signed-in account changed');
    await proof.cleanup();
    expect(mockFirebaseAuth.signInWithCredential).not.toHaveBeenCalled();
  });
});

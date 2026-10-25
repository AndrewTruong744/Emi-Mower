import { Alert } from 'react-native';
import { beforeEach, describe, expect, it, jest } from '@jest/globals';
import { act, renderHook, waitFor } from '@testing-library/react-native';
import { useBoundStore } from '@/store/useBoundStore';
import { mockFirebaseUser, mockFirebaseAuth, mockSecondaryAuth } from '../mocks/firebase';
import { createWrapper, mockedZenohQuery, resetHookState } from './testUtils';
import { useSettings } from '@/hooks/settings/useSettings';

describe('useSettings', () => {
  beforeEach(resetHookState);

  it('updates the username and store state', async () => {
    useBoundStore.getState().setUser({
      user_id: 'user-1',
      email: 'user@example.com',
      displayName: 'OldName',
    });
    mockedZenohQuery.mockResolvedValue({ new_user_name: 'NewName' });
    const alertSpy = jest.spyOn(Alert, 'alert').mockImplementation(() => undefined);
    const { result } = renderHook(() => useSettings(), { wrapper: createWrapper() });
    await act(async () => result.current.updateUsername('NewName'));
    await waitFor(() => expect(useBoundStore.getState().displayName).toBe('NewName'));
    await waitFor(() => expect(result.current.isUpdatingUsername).toBe(false));
    expect(result.current.nameUpdateFeedback).toEqual({
      type: 'success',
      message: 'Name updated successfully.',
    });
    alertSpy.mockRestore();
  });

  it('reports missing users and username failures globally', async () => {
    const alertSpy = jest.spyOn(Alert, 'alert').mockImplementation(() => undefined);
    const missingUser = renderHook(() => useSettings(), { wrapper: createWrapper() });
    await act(async () => missingUser.result.current.updateUsername('NewName'));
    expect(useBoundStore.getState().errorQueue[0]).toMatchObject({
      title: 'Authentication failed',
      message: 'No authenticated user found',
    });

    act(() => {
      useBoundStore
        .getState()
        .setUser({ user_id: 'user-1', email: 'user@example.com', displayName: 'Old' });
    });
    const { result } = renderHook(() => useSettings(), { wrapper: createWrapper() });
    mockedZenohQuery.mockRejectedValueOnce(new Error('username failed'));
    await act(async () => result.current.updateUsername('NewName'));
    await waitFor(() => expect(result.current.isUpdatingUsername).toBe(false));
    expect(useBoundStore.getState().errorQueue).toContainEqual(
      expect.objectContaining({ title: 'Request failed', message: 'username failed' })
    );
    expect(result.current.nameUpdateFeedback).toEqual({
      type: 'error',
      message: 'Name could not be updated. Please try again.',
    });
    alertSpy.mockRestore();
  });

  it('shows saving state until the server confirms the name, then clears a previous failure', async () => {
    useBoundStore.getState().setUser({
      user_id: 'user-1',
      email: 'user@example.com',
      displayName: 'Old',
    });
    const { result } = renderHook(() => useSettings(), { wrapper: createWrapper() });
    mockedZenohQuery.mockResolvedValueOnce({});
    await act(async () => result.current.updateUsername('New'));
    expect(result.current.nameUpdateFeedback?.type).toBe('error');
    expect(useBoundStore.getState().displayName).toBe('Old');

    let confirm!: (value: unknown) => void;
    mockedZenohQuery.mockReturnValueOnce(
      new Promise((resolve) => {
        confirm = resolve;
      })
    );
    let saving!: Promise<void>;
    await act(async () => {
      saving = result.current.updateUsername('New');
    });
    await waitFor(() => expect(result.current.isUpdatingUsername).toBe(true));
    expect(result.current.nameUpdateFeedback).toBeNull();
    expect(useBoundStore.getState().displayName).toBe('Old');
    await act(async () => {
      confirm({ new_user_name: 'New' });
      await saving;
    });
    await waitFor(() => expect(result.current.isUpdatingUsername).toBe(false));
    expect(result.current.nameUpdateFeedback?.type).toBe('success');
    expect(useBoundStore.getState().displayName).toBe('New');
  });

  it('does not overwrite a different account when an old name request finishes', async () => {
    useBoundStore.getState().setUser({
      user_id: 'user-1',
      email: 'user@example.com',
      displayName: 'Old',
    });
    let confirm!: (value: unknown) => void;
    mockedZenohQuery.mockReturnValueOnce(
      new Promise((resolve) => {
        confirm = resolve;
      })
    );
    const { result } = renderHook(() => useSettings(), { wrapper: createWrapper() });
    let saving!: Promise<void>;
    await act(async () => {
      saving = result.current.updateUsername('New');
    });
    await act(async () => {
      useBoundStore.getState().setUser({
        user_id: 'replacement-user',
        email: 'replacement@example.com',
        displayName: 'Replacement',
      });
      confirm({ new_user_name: 'New' });
      await saving;
    });
    expect(useBoundStore.getState().displayName).toBe('Replacement');
    expect(result.current.nameUpdateFeedback).toBeNull();
  });

  it('changes email through Firebase and Zenoh', async () => {
    const alertSpy = jest.spyOn(Alert, 'alert').mockImplementation(() => undefined);
    const missingUser = renderHook(() => useSettings(), { wrapper: createWrapper() });
    await act(async () => missingUser.result.current.changeEmail());
    expect(useBoundStore.getState().errorQueue[0]).toMatchObject({
      title: 'Authentication failed',
      message: 'No authenticated user found',
    });

    act(() => {
      useBoundStore
        .getState()
        .setUser({ user_id: 'user-1', email: 'old@example.com', displayName: 'User' });
    });
    const { result } = renderHook(() => useSettings(), { wrapper: createWrapper() });
    mockedZenohQuery.mockImplementationOnce(async () => {
      expect(mockFirebaseAuth.signInWithCredential).not.toHaveBeenCalled();
      return { user_id: 'replacement-user', new_email: 'replacement@example.com' };
    });
    await act(async () => result.current.changeEmail());
    await waitFor(() => expect(result.current.isUpdatingEmail).toBe(false));
    expect(mockFirebaseUser.updateEmail).not.toHaveBeenCalled();
    expect(mockFirebaseAuth.signInWithCredential).toHaveBeenCalledTimes(1);
    expect(mockSecondaryAuth.signOut).toHaveBeenCalled();
    // The auth-state listener, not the old settings closure, publishes the new identity.
    expect(useBoundStore.getState().email).toBe('old@example.com');
    expect(alertSpy).toHaveBeenCalledWith(
      'Success',
      'Google account switched. Your mowers are available with the new login.'
    );
    alertSpy.mockRestore();
  });

  it('reports an email response without a new address', async () => {
    act(() => {
      useBoundStore
        .getState()
        .setUser({ user_id: 'user-1', email: 'old@example.com', displayName: 'User' });
    });
    mockedZenohQuery.mockResolvedValueOnce({});
    const alertSpy = jest.spyOn(Alert, 'alert').mockImplementation(() => undefined);
    const { result } = renderHook(() => useSettings(), { wrapper: createWrapper() });
    await act(async () => result.current.changeEmail());
    await waitFor(() => expect(result.current.isUpdatingEmail).toBe(false));
    expect(useBoundStore.getState().errorQueue[0]).toEqual(
      expect.objectContaining({
        title: 'Request failed',
        message: 'Account switch returned an unexpected identity.',
      })
    );
    alertSpy.mockRestore();
  });
  it('keeps the old identity and data when the backend rejects a transfer', async () => {
    useBoundStore
      .getState()
      .setUser({ user_id: 'user-1', email: 'old@example.com', displayName: 'Owner' });
    mockedZenohQuery.mockRejectedValueOnce(new Error('transfer failed'));
    const { result } = renderHook(() => useSettings(), { wrapper: createWrapper() });
    await act(async () => result.current.changeEmail());
    expect(mockFirebaseAuth.signInWithCredential).not.toHaveBeenCalled();
    expect(mockSecondaryAuth.signOut).toHaveBeenCalled();
    expect(useBoundStore.getState().user_id).toBe('user-1');
  });

  it('keeps the replacement identity published by the auth listener after handoff', async () => {
    useBoundStore
      .getState()
      .setUser({ user_id: 'user-1', email: 'old@example.com', displayName: 'Owner' });
    mockedZenohQuery.mockResolvedValueOnce({
      user_id: 'replacement-user',
      new_email: 'replacement@example.com',
    });
    mockFirebaseAuth.signInWithCredential.mockImplementationOnce(async () => {
      useBoundStore.getState().setUser({
        user_id: 'replacement-user',
        email: 'replacement@example.com',
        displayName: 'Replacement',
      });
      return { user: mockFirebaseUser };
    });
    const alert = jest.spyOn(Alert, 'alert').mockImplementation(() => undefined);
    const { result } = renderHook(() => useSettings(), { wrapper: createWrapper() });
    await act(async () => result.current.changeEmail());
    expect(useBoundStore.getState().user_id).toBe('replacement-user');
    expect(useBoundStore.getState().email).toBe('replacement@example.com');
    alert.mockRestore();
  });
});

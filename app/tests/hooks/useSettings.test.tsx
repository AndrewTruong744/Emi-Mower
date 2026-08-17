import { Alert } from 'react-native';
import { beforeEach, describe, expect, it, jest } from '@jest/globals';
import { act, renderHook, waitFor } from '@testing-library/react-native';
import { useBoundStore } from '@/store/useBoundStore';
import { mockFirebaseUser } from '../mocks/firebase';
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
    expect(alertSpy).toHaveBeenCalledWith('Success', 'Username updated successfully');
    alertSpy.mockRestore();
  });

  it('handles missing users and username failures', async () => {
    const alertSpy = jest.spyOn(Alert, 'alert').mockImplementation(() => undefined);
    const missingUser = renderHook(() => useSettings(), { wrapper: createWrapper() });
    await act(async () => missingUser.result.current.updateUsername('NewName'));
    expect(alertSpy).toHaveBeenCalledWith('Error', 'No authenticated user found');

    useBoundStore
      .getState()
      .setUser({ user_id: 'user-1', email: 'user@example.com', displayName: 'Old' });
    const { result } = renderHook(() => useSettings(), { wrapper: createWrapper() });
    mockedZenohQuery.mockRejectedValueOnce(new Error('username failed'));
    await act(async () => {
      await expect(result.current.updateUsername('NewName')).rejects.toThrow('username failed');
    });
    expect(alertSpy).toHaveBeenCalledWith('Update Failed', 'username failed');
    alertSpy.mockRestore();
  });

  it('changes email through Firebase and Zenoh', async () => {
    const alertSpy = jest.spyOn(Alert, 'alert').mockImplementation(() => undefined);
    const missingUser = renderHook(() => useSettings(), { wrapper: createWrapper() });
    await act(async () => missingUser.result.current.changeEmail());
    expect(alertSpy).toHaveBeenCalledWith('Error', 'No authenticated user found');

    useBoundStore
      .getState()
      .setUser({ user_id: 'user-1', email: 'old@example.com', displayName: 'User' });
    const { result } = renderHook(() => useSettings(), { wrapper: createWrapper() });
    mockedZenohQuery.mockResolvedValueOnce({ new_email: 'new@example.com' });
    await act(async () => result.current.changeEmail());
    expect(mockFirebaseUser.updateEmail).toHaveBeenCalledWith('user@example.com');
    expect(useBoundStore.getState().email).toBe('new@example.com');
    expect(alertSpy).toHaveBeenCalledWith('Success', 'Email updated successfully');
    alertSpy.mockRestore();
  });

  it('reports an email response without a new address', async () => {
    useBoundStore
      .getState()
      .setUser({ user_id: 'user-1', email: 'old@example.com', displayName: 'User' });
    mockedZenohQuery.mockResolvedValueOnce({});
    const alertSpy = jest.spyOn(Alert, 'alert').mockImplementation(() => undefined);
    const { result } = renderHook(() => useSettings(), { wrapper: createWrapper() });
    await act(async () => result.current.changeEmail());
    expect(alertSpy).toHaveBeenCalledWith(
      'Email Update Failed',
      'Email update did not return the new email address.'
    );
    alertSpy.mockRestore();
  });
});

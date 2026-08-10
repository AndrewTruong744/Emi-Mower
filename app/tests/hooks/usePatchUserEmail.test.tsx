import { act, renderHook } from '@testing-library/react-native';
import { mockFirebaseAuth, mockFirebaseUser } from '../mocks/firebase';
import { createWrapper, mockedZenohQuery, resetHookState } from './testUtils';
import { usePatchUserEmail } from '@/hooks/api/user/usePatchUserEmail';

describe('usePatchUserEmail', () => {
  beforeEach(resetHookState);

  it('updates Firebase first and then calls the email Zenoh route', async () => {
    mockedZenohQuery.mockResolvedValue({
      message: 'updated',
      user_id: 'user-1',
      new_email: 'new@example.com',
    });
    const { result } = renderHook(() => usePatchUserEmail(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.mutateAsync({
        newIdToken: 'new-firebase-token',
        newEmail: 'new@example.com',
      });
    });

    expect(mockFirebaseUser.updateEmail).toHaveBeenCalledWith('new@example.com');
    expect(mockedZenohQuery).toHaveBeenCalledWith('user/update_email', {
      id_token: 'firebase-token',
      new_id_token: 'new-firebase-token',
    });
  });

  it('rejects missing Firebase users and email addresses', async () => {
    const { result } = renderHook(() => usePatchUserEmail(), { wrapper: createWrapper() });
    mockFirebaseAuth.currentUser = null;
    await expect(result.current.mutateAsync({ newIdToken: 'token', newEmail: 'new@example.com' })).rejects.toThrow(
      'No authenticated Firebase user found'
    );
    mockFirebaseAuth.currentUser = mockFirebaseUser;
    await expect(result.current.mutateAsync({ newIdToken: 'token', newEmail: '' })).rejects.toThrow(
      'A new email address is required'
    );
  });
});

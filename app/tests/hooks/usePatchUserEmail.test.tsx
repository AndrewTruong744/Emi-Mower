import { beforeEach, describe, expect, it } from '@jest/globals';
import { act, renderHook } from '@testing-library/react-native';
import { mockFirebaseAuth, mockFirebaseUser } from '../mocks/firebase';
import { createWrapper, mockedZenohQuery, resetHookState } from './testUtils';
import { usePatchUserEmail } from '@/hooks/api/user/usePatchUserEmail';

describe('usePatchUserEmail', () => {
  beforeEach(resetHookState);
  it('submits both captured identities without changing Firebase email or login', async () => {
    mockedZenohQuery.mockResolvedValue({
      user_id: 'replacement-user',
      new_email: 'new@example.com',
    });
    const { result } = renderHook(() => usePatchUserEmail(), { wrapper: createWrapper() });
    await act(async () => {
      await result.current.mutateAsync({ originalIdToken: 'original', newIdToken: 'replacement' });
    });
    expect(mockedZenohQuery).toHaveBeenCalledWith('user/update_email', {
      id_token: 'original',
      new_id_token: 'replacement',
    });
    expect(mockFirebaseUser.updateEmail).not.toHaveBeenCalled();
    expect(mockFirebaseAuth.signInWithCredential).not.toHaveBeenCalled();
  });
  it('requires proof of both accounts', async () => {
    const { result } = renderHook(() => usePatchUserEmail(), { wrapper: createWrapper() });
    await act(async () => {
      await expect(
        result.current.mutateAsync({ originalIdToken: '', newIdToken: 'new' })
      ).rejects.toThrow('Both Google accounts');
    });
    expect(mockedZenohQuery).not.toHaveBeenCalled();
  });
});

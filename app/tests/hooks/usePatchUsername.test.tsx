import { beforeEach, describe, expect, it } from '@jest/globals';
import { act, renderHook } from '@testing-library/react-native';
import { createWrapper, mockedZenohQuery, resetHookState } from './testUtils';
import { usePatchUsername } from '@/hooks/api/user/usePatchUsername';

describe('usePatchUsername', () => {
  beforeEach(resetHookState);

  it('updates a username through the Zenoh route', async () => {
    mockedZenohQuery.mockResolvedValue({
      message: 'updated',
      user_id: 'user-1',
      new_user_name: 'NewName',
    });
    const { result } = renderHook(() => usePatchUsername(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.mutateAsync({ userId: 'user-1', newUserName: 'NewName' });
    });

    expect(mockedZenohQuery).toHaveBeenCalledWith('user/update_name', {
      id_token: 'firebase-token',
      new_user_name: 'NewName',
    });
  });
});

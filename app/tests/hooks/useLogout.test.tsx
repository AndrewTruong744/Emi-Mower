import { beforeEach, describe, expect, it } from '@jest/globals';
import { act, renderHook } from '@testing-library/react-native';
import { mockGoogleSignin } from '../mocks/google-signin';
import { resetHookState } from './testUtils';
import { useLogout } from '@/hooks/useLogout';

describe('useLogout', () => {
  beforeEach(resetHookState);

  it('signs out of Google and Firebase', async () => {
    const { result } = renderHook(() => useLogout());
    await act(async () => result.current.logout());
    expect(mockGoogleSignin.signOut).toHaveBeenCalled();
    expect(result.current.isLoading).toBe(false);
  });
});

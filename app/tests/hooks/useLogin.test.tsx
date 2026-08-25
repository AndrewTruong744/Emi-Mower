import { act, renderHook } from '@testing-library/react-native';
import { beforeEach, describe, expect, it, jest } from '@jest/globals';
import { useBoundStore } from '@/store/useBoundStore';
import { useLogin } from '@/hooks/useLogin';
import { mockedZenohQuery, resetHookState } from './testUtils';
import { mockGoogleSignin } from '../mocks/google-signin';
import { queryClient } from '@/config/queryClient';

const mockLoginReplace = jest.fn();
jest.mock('@/config/zenohClient', () => ({
  zenohQuery: jest.fn(),
  connectZenoh: jest.fn<(...args: any[]) => any>().mockResolvedValue({}),
}));
jest.mock('expo-router', () => ({
  useRouter: () => ({ replace: mockLoginReplace }),
}));

describe('useLogin', () => {
  beforeEach(resetHookState);

  it('starts Firebase sign-in without bypassing the Zenoh-gated auth listener', async () => {
    queryClient.setQueryData(['telemetry-history', 'old-account'], { points: [1] });
    const { result } = renderHook(() => useLogin());
    await act(async () => result.current.handleGoogleLogin());

    expect(mockedZenohQuery).not.toHaveBeenCalled();
    expect(mockLoginReplace).not.toHaveBeenCalled();
    expect(useBoundStore.getState()).toMatchObject({
      idToken: null,
      authStatus: 'signedOut',
    });
    expect(queryClient.getQueryData(['telemetry-history', 'old-account'])).toBeUndefined();
  });

  it('reports login errors globally', async () => {
    mockGoogleSignin.signIn.mockRejectedValueOnce(new Error('Google offline'));
    const { result } = renderHook(() => useLogin());
    await act(async () => result.current.handleGoogleLogin());
    expect(useBoundStore.getState().errorQueue[0]).toMatchObject({
      title: 'Sign-in failed',
      message: 'Google offline',
      presentation: 'modal',
    });

    act(() => useBoundStore.getState().clearErrors());
    expect(useBoundStore.getState().errorQueue).toEqual([]);
  });
});

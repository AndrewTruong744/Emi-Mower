import { act, renderHook } from '@testing-library/react-native';
import { jest } from '@jest/globals';
import { useBoundStore } from '@/store/useBoundStore';
import { useLogin } from '@/hooks/useLogin';
import { mockedZenohQuery, resetHookState } from './testUtils';

const mockLoginReplace = jest.fn();
jest.mock('@/zenoh/client', () => ({
  zenohQuery: jest.fn(),
  connectZenoh: jest.fn<(...args: any[]) => any>().mockResolvedValue({}),
  isZenohOperationCancelled: jest.fn(() => false),
}));
jest.mock('expo-router', () => ({
  useRouter: () => ({ replace: mockLoginReplace }),
}));

describe('useLogin', () => {
  beforeEach(resetHookState);

  it('logs in with Google, calls UserLogin, and navigates', async () => {
    mockedZenohQuery.mockResolvedValue({
      user_id: 'user-1',
      token: 'zenoh-token',
      expires_in: 300,
      user_data: {
        id: 'user-1',
        email: 'user@example.com',
        name: 'Test User',
        mowers: ['mower-1'],
      },
    });
    const { result } = renderHook(() => useLogin());
    await act(async () => result.current.handleGoogleLogin());

    expect(mockedZenohQuery).toHaveBeenCalledWith(
      'user/login',
      expect.objectContaining({ id_token: 'firebase-token' })
    );
    expect(mockLoginReplace).toHaveBeenCalledWith('/(tabs)');
    expect(useBoundStore.getState()).toMatchObject({
      user_id: 'user-1',
      mowers: ['mower-1'],
    });
  });

  it('reports login errors globally', async () => {
    mockedZenohQuery.mockRejectedValue(new Error('Zenoh offline'));
    const { result } = renderHook(() => useLogin());
    await act(async () => result.current.handleGoogleLogin());
    expect(useBoundStore.getState().error).toMatchObject({
      title: 'Sign-in failed',
      message: 'Zenoh offline',
      source: 'auth',
    });

    act(() => useBoundStore.getState().clearError());
    expect(useBoundStore.getState().error).toBeNull();
  });
});

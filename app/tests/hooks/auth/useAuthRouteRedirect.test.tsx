import { beforeEach, describe, expect, it, jest } from '@jest/globals';
import { renderHook } from '@testing-library/react-native';
import { useAuthRouteRedirect } from '@/hooks/auth/useAuthRouteRedirect';

const mockReplace = jest.fn();
const mockSegments = jest.fn();

jest.mock('expo-router', () => ({
  useRouter: () => ({ replace: mockReplace }),
  useSegments: () => mockSegments(),
}));

describe('useAuthRouteRedirect', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSegments.mockReturnValue(['(tabs)']);
  });

  it('does not redirect while auth is still transitioning', () => {
    for (const status of ['initializing', 'authenticating', 'signingOut'] as const) {
      renderHook(() => useAuthRouteRedirect(status));
    }

    expect(mockReplace).not.toHaveBeenCalled();
  });

  it('sends signed-out users to login unless they are already there', () => {
    renderHook(() => useAuthRouteRedirect('signedOut'));
    expect(mockReplace).toHaveBeenCalledWith('/(auth)/login');

    mockReplace.mockClear();
    mockSegments.mockReturnValue(['(auth)']);
    renderHook(() => useAuthRouteRedirect('signedOut'));
    expect(mockReplace).not.toHaveBeenCalled();
  });

  it('sends authenticated users out of the auth group', () => {
    mockSegments.mockReturnValue(['(auth)']);
    renderHook(() => useAuthRouteRedirect('authenticated'));

    expect(mockReplace).toHaveBeenCalledWith('/(tabs)/home');
  });

  it('leaves authenticated users in the app group', () => {
    renderHook(() => useAuthRouteRedirect('authenticated'));

    expect(mockReplace).not.toHaveBeenCalled();
  });
});

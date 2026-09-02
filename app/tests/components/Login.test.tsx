import React from 'react';
import { fireEvent, render } from '@testing-library/react-native';
import { beforeEach, describe, expect, it, jest } from '@jest/globals';
import { ActivityIndicator, PaperProvider } from 'react-native-paper';
import Login from '@/components/Login';
import { useLogin } from '@/hooks/useLogin';

jest.mock('@/hooks/useLogin', () => ({ useLogin: jest.fn() }));

const mockUseLogin = useLogin as jest.MockedFunction<typeof useLogin>;

describe('Login', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the sign-in action and delegates presses', () => {
    const handleGoogleLogin = jest.fn<() => Promise<void>>().mockResolvedValue(undefined);
    mockUseLogin.mockReturnValue({ handleGoogleLogin, isLoading: false });

    const screen = render(
      <PaperProvider>
        <Login />
      </PaperProvider>
    );

    expect(screen.getByText('Emi Mower')).toBeTruthy();
    fireEvent.press(screen.getByText('Sign in with Google'));
    expect(handleGoogleLogin).toHaveBeenCalledTimes(1);
  });

  it('shows a loader and hides the sign-in action while loading', () => {
    mockUseLogin.mockReturnValue({
      handleGoogleLogin: jest.fn<() => Promise<void>>(),
      isLoading: true,
    });

    const screen = render(
      <PaperProvider>
        <Login />
      </PaperProvider>
    );

    expect(screen.queryByText('Sign in with Google')).toBeNull();
    expect(screen.UNSAFE_getByType(ActivityIndicator)).toBeTruthy();
  });
});

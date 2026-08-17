import React from 'react';
import { describe, expect, it, jest } from '@jest/globals';
import { fireEvent, render } from '@testing-library/react-native';
import { PaperProvider } from 'react-native-paper';
import { Settings } from '@/components/settings/Settings';
import { useSettings } from '@/hooks/settings/useSettings';

jest.mock('@/hooks/settings/useSettings', () => ({ useSettings: jest.fn() }));

const mockUseSettings = useSettings as jest.MockedFunction<typeof useSettings>;

describe('Settings', () => {
  it('renders account data and delegates each account action to its hook', () => {
    const updateUsername = jest.fn<(newUserName: string) => Promise<void>>().mockResolvedValue();
    const changeEmail = jest.fn<() => Promise<void>>().mockResolvedValue();
    const logout = jest.fn<() => Promise<void>>().mockResolvedValue();
    mockUseSettings.mockReturnValue({
      user: {
        user_id: 'user-1',
        email: 'user@example.com',
        displayName: 'MowerUser',
      },
      updateUsername,
      changeEmail,
      logout,
      isUpdatingUsername: false,
      isUpdatingEmail: false,
      isLoggingOut: false,
    });

    const screen = render(
      <PaperProvider>
        <Settings />
      </PaperProvider>
    );

    expect(screen.getByText('Account settings')).toBeTruthy();
    expect(screen.getByDisplayValue('user@example.com')).toBeTruthy();
    fireEvent.press(screen.getByText('Change Email'));
    fireEvent.press(screen.getByText('Logout'));

    expect(changeEmail).toHaveBeenCalledTimes(1);
    expect(logout).toHaveBeenCalledTimes(1);
  });
});

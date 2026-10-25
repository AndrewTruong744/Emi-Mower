import React from 'react';
import { describe, expect, it, jest } from '@jest/globals';
import { act, fireEvent, render, waitFor } from '@testing-library/react-native';
import { ActivityIndicator, PaperProvider } from 'react-native-paper';
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
      nameUpdateFeedback: null,
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
    fireEvent.press(screen.getByText('Change Google Account'));
    fireEvent.press(screen.getByText('Logout'));

    expect(changeEmail).toHaveBeenCalledTimes(1);
    expect(logout).toHaveBeenCalledTimes(1);
  });

  it('validates display names and submits a valid changed name', async () => {
    const updateUsername = jest.fn<(newUserName: string) => Promise<void>>().mockResolvedValue();
    mockUseSettings.mockReturnValue({
      user: { user_id: 'user-1', email: 'user@example.com', displayName: 'Old Name' },
      updateUsername,
      changeEmail: jest.fn<() => Promise<void>>().mockResolvedValue(),
      logout: jest.fn<() => Promise<void>>().mockResolvedValue(),
      isUpdatingUsername: false,
      nameUpdateFeedback: null,
      isUpdatingEmail: false,
      isLoggingOut: false,
    });

    const screen = render(
      <PaperProvider>
        <Settings />
      </PaperProvider>
    );
    const input = screen.getAllByTestId('text-input-outlined')[2];

    await act(async () => {
      fireEvent.changeText(input, '');
    });
    await act(async () => {
      fireEvent(input, 'blur', { persist: jest.fn(), target: { name: 'displayName' } });
    });
    await waitFor(() => expect(screen.getByText('Name is required')).toBeTruthy());

    await act(async () => {
      fireEvent.changeText(input, 'bad\nname');
    });
    await act(async () => {
      fireEvent(input, 'blur', { persist: jest.fn(), target: { name: 'displayName' } });
    });
    await waitFor(() =>
      expect(screen.getByText('Name must not contain control characters')).toBeTruthy()
    );

    await act(async () => {
      fireEvent.changeText(input, 'a'.repeat(65));
    });
    await act(async () => {
      fireEvent(input, 'blur', { persist: jest.fn(), target: { name: 'displayName' } });
    });
    await waitFor(() =>
      expect(screen.getByText('Name must be at most 64 characters')).toBeTruthy()
    );

    await act(async () => {
      fireEvent.changeText(input, "New Name-O'Neil");
    });
    const updateButton = screen.getByRole('button', { name: 'Update Name' });
    await waitFor(() => expect(updateButton.props.accessibilityState?.disabled).toBe(false));
    await act(async () => {
      fireEvent.press(updateButton);
    });
    expect(updateUsername).toHaveBeenCalledWith("New Name-O'Neil");
  });

  it('renders empty profile fallbacks and the loading overlay', () => {
    mockUseSettings.mockReturnValue({
      user: { user_id: null, email: null, displayName: null },
      updateUsername: jest.fn<() => Promise<void>>().mockResolvedValue(),
      changeEmail: jest.fn<() => Promise<void>>().mockResolvedValue(),
      logout: jest.fn<() => Promise<void>>().mockResolvedValue(),
      isUpdatingUsername: false,
      nameUpdateFeedback: null,
      isUpdatingEmail: true,
      isLoggingOut: false,
    });

    const screen = render(
      <PaperProvider>
        <Settings />
      </PaperProvider>
    );

    expect(screen.getByText('No Name Set')).toBeTruthy();
    expect(screen.getByText('No Email Set')).toBeTruthy();
    expect(screen.UNSAFE_getAllByType(ActivityIndicator).length).toBeGreaterThan(0);
  });

  it('shows saving, success and failure feedback next to the name action', () => {
    const state: ReturnType<typeof useSettings> = {
      user: { user_id: 'user-1', email: 'user@example.com', displayName: 'Name' },
      updateUsername: jest.fn<() => Promise<void>>().mockResolvedValue(),
      changeEmail: jest.fn<() => Promise<void>>().mockResolvedValue(),
      logout: jest.fn<() => Promise<void>>().mockResolvedValue(),
      isUpdatingUsername: true,
      nameUpdateFeedback: null,
      isUpdatingEmail: false,
      isLoggingOut: false,
    };
    mockUseSettings.mockReturnValue(state);
    const content = () => (
      <PaperProvider>
        <Settings />
      </PaperProvider>
    );
    const screen = render(content());
    expect(screen.getByRole('button', { name: 'Saving name…' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Change Google Account' })).toBeDisabled();
    mockUseSettings.mockReturnValue({
      ...state,
      isUpdatingUsername: false,
      nameUpdateFeedback: { type: 'success', message: 'Name updated successfully.' },
    });
    screen.rerender(content());
    expect(screen.getByText('Name updated successfully.')).toBeTruthy();
    mockUseSettings.mockReturnValue({
      ...state,
      isUpdatingUsername: false,
      nameUpdateFeedback: {
        type: 'error',
        message: 'Name could not be updated. Please try again.',
      },
    });
    screen.rerender(content());
    expect(screen.getByText('Name could not be updated. Please try again.')).toBeTruthy();
    expect(screen.queryByText('Name updated successfully.')).toBeNull();
  });
});

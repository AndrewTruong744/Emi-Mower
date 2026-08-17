import React from 'react';
import { beforeEach, describe, expect, it, jest } from '@jest/globals';
import { render, waitFor } from '@testing-library/react-native';
import { PaperProvider } from 'react-native-paper';
import HomeScreen from '@/app/(tabs)/home';
import { useBoundStore } from '@/store/useBoundStore';

jest.mock('expo-router', () => {
  const { View } = require('react-native');
  return { Link: ({ children }: { children: React.ReactNode }) => <View>{children}</View> };
});

describe('HomeSummary', () => {
  beforeEach(() => {
    useBoundStore.getState().resetStore();
    useBoundStore.getState().setMowers(['mower-1']);
  });

  it('summarizes and links to each operational tab', async () => {
    const screen = render(
      <PaperProvider>
        <HomeScreen />
      </PaperProvider>
    );

    await waitFor(() => expect(screen.getByText('1 mowers')).toBeTruthy());
    expect(screen.getByTestId('home-summary-controller')).toBeTruthy();
    expect(screen.getByTestId('home-summary-mowers')).toBeTruthy();
    expect(screen.getByTestId('home-summary-map')).toBeTruthy();
    expect(screen.getByTestId('home-summary-settings')).toBeTruthy();
    expect(screen.getAllByText('No active session')).toHaveLength(2);
    expect(screen.getByText('Mower mower-1')).toBeTruthy();
  });
});

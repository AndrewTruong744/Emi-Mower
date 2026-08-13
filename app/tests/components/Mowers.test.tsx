import React from 'react';
import { beforeEach, describe, expect, it } from '@jest/globals';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import { PaperProvider } from 'react-native-paper';
import { Mowers } from '@/components/mowers/Mowers';
import { useBoundStore } from '@/store/useBoundStore';

describe('Mowers', () => {
  beforeEach(() => useBoundStore.getState().resetStore());

  it('displays mower identity, status, and grouped 30-second telemetry charts', async () => {
    const screen = render(
      <PaperProvider>
        <Mowers />
      </PaperProvider>
    );

    await waitFor(() =>
      expect(screen.getByTestId('mower-selector-a0f6f58e-ef97-4fa9-aede-002467ca11ed')).toBeTruthy()
    );
    expect(screen.getByText('UUID')).toBeTruthy();
    expect(screen.getByText('Current status')).toBeTruthy();
    expect(screen.getByText('Drive motors')).toBeTruthy();
    expect(screen.getAllByText('Left motor speed')).toHaveLength(2);
    expect(screen.getByText('Safety')).toBeTruthy();
    expect(screen.getByText('Slippage detected')).toBeTruthy();
    expect(screen.getByText('IMU accelerometer')).toBeTruthy();
    expect(screen.getByTestId('drive-motor-charts')).toBeTruthy();
  });

  it('adds a mower and renames the selected mower through the modals', async () => {
    const screen = render(
      <PaperProvider>
        <Mowers />
      </PaperProvider>
    );

    await waitFor(() =>
      expect(screen.getByTestId('mower-selector-a0f6f58e-ef97-4fa9-aede-002467ca11ed')).toBeTruthy()
    );
    fireEvent.press(screen.getByText('Add mower'));
    fireEvent.changeText(screen.getByTestId('add-mower-uuid'), 'new-mower-uuid');
    fireEvent.press(screen.getByTestId('confirm-add-mower'));

    await waitFor(() => expect(screen.getAllByText('Mower new-mowe')).toHaveLength(2));
    fireEvent.press(screen.getByTestId('edit-mower-name'));
    fireEvent.changeText(screen.getByTestId('rename-mower-name'), 'Patio Mower');
    fireEvent.press(screen.getByTestId('confirm-rename-mower'));

    await waitFor(() => expect(screen.getAllByText('Patio Mower')).toHaveLength(2));
  });
});

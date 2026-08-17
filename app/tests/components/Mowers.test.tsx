import React from 'react';
import { beforeEach, describe, expect, it } from '@jest/globals';
import { act, fireEvent, render, waitFor } from '@testing-library/react-native';
import { PaperProvider } from 'react-native-paper';
import { Mowers } from '@/components/mowers/Mowers';
import { useBoundStore } from '@/store/useBoundStore';

jest.mock('@/hooks/api/mower/useMowerTelemetryHistory', () => ({
  useMowerTelemetryHistory: () => ({ data: undefined, isFetching: false }),
}));

describe('Mowers', () => {
  const firstMowerId = 'a0f6f58e-ef97-4fa9-aede-002467ca11ed';
  const secondMowerId = '7c3d863b-5778-4ae6-9177-151d2f9f846d';
  const liveSample = {
    timestamp: 1_700_000_000_000,
    latitude: 40.7128, longitude: -74.006, batteryPercentage: 82,
    leftMotorSpeed: 0.7, leftMotorDirection: 1 as const,
    rightMotorSpeed: 0.6, rightMotorDirection: 1 as const,
    cuttingMotorSpeed: 2800, slippageDetected: false,
    imuData: { accelX: 0.1, accelY: 0.2, accelZ: 9.8, gyroX: 0.1, gyroY: 0.1, gyroZ: 0.1, magX: 20, magY: 2, magZ: 40 },
  };

  beforeEach(() => {
    useBoundStore.getState().resetStore();
    useBoundStore.getState().setMowers([firstMowerId, secondMowerId]);
    useBoundStore.getState().appendTelemetryBatch({ [firstMowerId]: [liveSample] });
  });

  it('displays mower identity, status, and grouped 30-second telemetry charts', async () => {
    const screen = render(
      <PaperProvider>
        <Mowers />
      </PaperProvider>
    );

    await waitFor(() =>
      expect(screen.getByTestId(`mower-selector-${firstMowerId}`)).toBeTruthy()
    );
    expect(screen.getByText('UUID')).toBeTruthy();
    expect(screen.getByText('Current status')).toBeTruthy();
    expect(screen.getByText('Drive motors')).toBeTruthy();
    expect(screen.getAllByText('Left motor speed')).toHaveLength(1);
    expect(screen.getByText('Safety')).toBeTruthy();
    expect(screen.getByText('Slippage detected')).toBeTruthy();
    expect(screen.getByText('IMU accelerometer')).toBeTruthy();
    expect(screen.getByTestId('drive-motor-charts')).toBeTruthy();
  });

  it('explains how to get started when the fleet is empty', () => {
    useBoundStore.getState().clearMowers();
    const screen = render(
      <PaperProvider>
        <Mowers />
      </PaperProvider>
    );

    expect(screen.getByText('No mowers have been added yet.')).toBeTruthy();
    expect(screen.getByText('No mowers in your fleet')).toBeTruthy();
    expect(screen.getByText('Add a mower to view its status, location, and telemetry.')).toBeTruthy();
  });

  it('adds a mower and renames the selected mower through the modals', async () => {
    const screen = render(
      <PaperProvider>
        <Mowers />
      </PaperProvider>
    );

    await waitFor(() =>
      expect(screen.getByTestId(`mower-selector-${firstMowerId}`)).toBeTruthy()
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

  it('opens a focused graph with the received live telemetry window', async () => {
    const screen = render(
      <PaperProvider>
        <Mowers />
      </PaperProvider>
    );

    await waitFor(() => expect(screen.getByTestId('metric-chart-left-motor-speed')).toBeTruthy());
    fireEvent.press(screen.getByTestId('metric-chart-left-motor-speed'));

    expect(screen.getByText('Left motor speed history')).toBeTruthy();
    expect(screen.getByText('Live telemetry window · 1 received samples')).toBeTruthy();
  });

  it('switches the selected mower while telemetry is updating', async () => {
    const screen = render(
      <PaperProvider>
        <Mowers />
      </PaperProvider>
    );

    await waitFor(() => expect(screen.getByTestId(`mower-selector-${secondMowerId}`)).toBeTruthy());
    act(() => useBoundStore.getState().appendTelemetryBatch({ [secondMowerId]: [{ ...liveSample, timestamp: liveSample.timestamp + 1 }] }));
    fireEvent.press(screen.getByTestId(`mower-selector-${secondMowerId}`));

    await waitFor(() => expect(screen.getByText(secondMowerId)).toBeTruthy());
    expect(useBoundStore.getState().selectedMowerUuid).toBe(secondMowerId);
  });
});

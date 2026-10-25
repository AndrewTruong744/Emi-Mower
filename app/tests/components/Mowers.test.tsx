import { mockedZenohQuery, resetHookState } from '../hooks/testUtils';
import React from 'react';
import { beforeEach, describe, expect, it, jest } from '@jest/globals';
import { act, fireEvent, render, waitFor } from '@testing-library/react-native';
import { PaperProvider } from 'react-native-paper';
import { Mowers } from '@/components/mowers/Mowers';
import { useBoundStore } from '@/store/useBoundStore';
import { mockFirebaseUser } from '../mocks/firebase';

jest.mock('@/zenoh/mowerTelemetry', () => ({
  initializeMowerTelemetrySubscription: jest
    .fn<(...args: any[]) => Promise<void>>()
    .mockResolvedValue(undefined),
}));
jest.mock('@/zenoh/mowerLiveliness', () => ({
  initializeMowerLivelinessSubscription: jest
    .fn<(...args: any[]) => Promise<void>>()
    .mockResolvedValue(undefined),
}));

jest.mock('@/hooks/api/mower/useMowerTelemetryHistory', () => ({
  useMowerTelemetryHistory: () => ({ data: undefined, isFetching: false }),
}));

describe('Mowers', () => {
  const firstMowerId = 'a0f6f58e-ef97-4fa9-aede-002467ca11ed';
  const secondMowerId = '7c3d863b-5778-4ae6-9177-151d2f9f846d';
  const liveSample = {
    timestamp: 1_700_000_000_000,
    latitude: 40.7128,
    longitude: -74.006,
    batteryPercentage: 82,
    leftMotorSpeed: 0.7,
    leftMotorDirection: 1 as const,
    rightMotorSpeed: 0.6,
    rightMotorDirection: 1 as const,
    cuttingMotorSpeed: 2800,
    slippageDetected: false,
    imuData: {
      accelX: 0.1,
      accelY: 0.2,
      accelZ: 9.8,
      gyroX: 0.1,
      gyroY: 0.1,
      gyroZ: 0.1,
      magX: 20,
      magY: 2,
      magZ: 40,
    },
  };

  beforeEach(() => {
    resetHookState();
    useBoundStore
      .getState()
      .setUser({ user_id: mockFirebaseUser.uid, email: 'user@example.com', displayName: 'User' });
    mockedZenohQuery.mockImplementation(async (_path: string, payload: any) => ({
      user_id: mockFirebaseUser.uid,
      mower_id: payload.mower_id,
      new_owner_id: payload.new_owner_id,
    }));
    useBoundStore.getState().setMowers([firstMowerId, secondMowerId]);
    useBoundStore.getState().appendTelemetryBatch({ [firstMowerId]: [liveSample] });
  });

  it('displays mower identity, status, and grouped 30-second telemetry charts', async () => {
    const screen = render(
      <PaperProvider>
        <Mowers />
      </PaperProvider>
    );

    await waitFor(() => expect(screen.getByTestId(`mower-selector-${firstMowerId}`)).toBeTruthy());
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
    expect(
      screen.getByText('Add a mower to view its status, location, and telemetry.')
    ).toBeTruthy();
  });

  it('adds a mower and renames the selected mower through the modals', async () => {
    const screen = render(
      <PaperProvider>
        <Mowers />
      </PaperProvider>
    );

    await waitFor(() => expect(screen.getByTestId(`mower-selector-${firstMowerId}`)).toBeTruthy());
    fireEvent.press(screen.getByText('Add mower'));
    fireEvent.changeText(
      screen.getByTestId('add-mower-uuid'),
      'c7ea8f21-7c9c-4d01-8a3b-a3efeaf0f9b0'
    );
    fireEvent.press(screen.getByTestId('confirm-add-mower'));

    await waitFor(() => expect(screen.getAllByText('Mower c7ea8f21')).toHaveLength(2));
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

  it('requires confirmation and backend success before removing a mower', async () => {
    const screen = render(
      <PaperProvider>
        <Mowers />
      </PaperProvider>
    );
    fireEvent.press(screen.getByTestId('remove-mower'));
    expect(mockedZenohQuery).not.toHaveBeenCalled();
    fireEvent.press(screen.getByText('Cancel'));
    expect(useBoundStore.getState().mowers).toContain(firstMowerId);
    fireEvent.press(screen.getByTestId('remove-mower'));
    await act(async () => {
      fireEvent.press(screen.getByTestId('confirm-mower-ownership'));
    });
    await waitFor(() => expect(useBoundStore.getState().mowers).not.toContain(firstMowerId));
    expect(useBoundStore.getState().mowers).toContain(secondMowerId);
    expect(mockedZenohQuery).toHaveBeenCalledWith('user/remove_mower', {
      id_token: 'firebase-token',
      mower_id: firstMowerId,
    });
    expect(screen.getByText('Mower removed from your account.')).toBeTruthy();
  });

  it('keeps the transfer form and mower on rejection, then transfers to the supplied user UID', async () => {
    const screen = render(
      <PaperProvider>
        <Mowers />
      </PaperProvider>
    );
    fireEvent.press(screen.getByTestId('transfer-mower'));
    fireEvent.changeText(screen.getByTestId('transfer-recipient-uid'), 'recipient-uid');
    mockedZenohQuery.mockRejectedValueOnce(new Error('Recipient does not exist'));
    await act(async () => {
      fireEvent.press(screen.getByTestId('confirm-mower-ownership'));
    });
    expect(screen.getByText('Recipient does not exist')).toBeTruthy();
    expect(useBoundStore.getState().mowers).toContain(firstMowerId);
    await act(async () => {
      fireEvent.press(screen.getByTestId('confirm-mower-ownership'));
    });
    await waitFor(() => expect(useBoundStore.getState().mowers).not.toContain(firstMowerId));
    expect(mockedZenohQuery).toHaveBeenLastCalledWith('user/transfer_mower', {
      id_token: 'firebase-token',
      mower_id: firstMowerId,
      new_owner_id: 'recipient-uid',
    });
  });

  it('switches the selected mower while telemetry is updating', async () => {
    const screen = render(
      <PaperProvider>
        <Mowers />
      </PaperProvider>
    );

    await waitFor(() => expect(screen.getByTestId(`mower-selector-${secondMowerId}`)).toBeTruthy());
    act(() =>
      useBoundStore
        .getState()
        .appendTelemetryBatch({
          [secondMowerId]: [{ ...liveSample, timestamp: liveSample.timestamp + 1 }],
        })
    );
    fireEvent.press(screen.getByTestId(`mower-selector-${secondMowerId}`));

    await waitFor(() => expect(screen.getByText(secondMowerId)).toBeTruthy());
    expect(useBoundStore.getState().selectedMowerUuid).toBe(secondMowerId);
  });
});

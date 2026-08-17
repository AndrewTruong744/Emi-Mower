import React from 'react';
import { beforeEach, describe, expect, it, jest } from '@jest/globals';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import { PaperProvider } from 'react-native-paper';
import { Map } from '@/components/map/Map';
import { useBoundStore } from '@/store/useBoundStore';

jest.mock('expo-router', () => {
  const React = require('react');
  return {
    useFocusEffect: (effect: () => void | (() => void)) => React.useEffect(effect, [effect]),
  };
});

describe('Map', () => {
  beforeEach(() => useBoundStore.getState().resetStore());

  it('creates a boundary, confirms a session, pauses it, and returns to drawing on cancellation', async () => {
    const screen = render(
      <PaperProvider>
        <Map />
      </PaperProvider>
    );

    await waitFor(() =>
      expect(screen.getByText('Tap the map to add boundary points (0/3 minimum).')).toBeTruthy()
    );
    const map = screen.getByTestId('mower-map');
    fireEvent.press(map, { nativeEvent: { lngLat: [-74.006, 40.7128] } });
    fireEvent.press(map, { nativeEvent: { lngLat: [-74.005, 40.7128] } });
    fireEvent.press(map, { nativeEvent: { lngLat: [-74.005, 40.7138] } });

    fireEvent.press(screen.getByTestId('accept-boundary'));
    await waitFor(() => expect(screen.getByText('Start cutting session?')).toBeTruthy());
    fireEvent.press(screen.getByTestId('confirm-cutting-area'));
    await waitFor(() => expect(screen.getByText('Mowing session active')).toBeTruthy());
    expect(useBoundStore.getState().areaImageUri).toMatch(/cutting-area-preview/);
    // Markers are driven only by received live telemetry; starting a session
    // must not invent mower positions inside the boundary.
    expect(Object.keys(useBoundStore.getState().mowerPositions)).toHaveLength(0);

    fireEvent.press(screen.getByTestId('pause-mowing-session'));
    expect(screen.getByText('Mowing paused')).toBeTruthy();
    fireEvent.press(screen.getByTestId('cancel-mowing-session'));
    await waitFor(() =>
      expect(screen.getByText('Tap the map to add boundary points (0/3 minimum).')).toBeTruthy()
    );
    expect(useBoundStore.getState().isSessionActive).toBe(false);
  });

  it('allows drawing only while satellite imagery is selected', async () => {
    const screen = render(
      <PaperProvider>
        <Map />
      </PaperProvider>
    );

    const map = screen.getByTestId('mower-map');
    fireEvent.press(screen.getByTestId('map-style-street'));
    expect(screen.getByText('Switch to satellite imagery to place boundary points.')).toBeTruthy();

    fireEvent.press(map, { nativeEvent: { lngLat: [-74.006, 40.7128] } });
    expect(useBoundStore.getState().cuttingBoundary).toEqual([]);

    fireEvent.press(screen.getByTestId('map-style-satellite'));
    fireEvent.press(map, { nativeEvent: { lngLat: [-74.006, 40.7128] } });
    await waitFor(() =>
      expect(screen.getByText('Tap the map to add boundary points (1/3 minimum).')).toBeTruthy()
    );
  });

  it('preserves a drawing when the confirmation modal is canceled', async () => {
    const screen = render(
      <PaperProvider>
        <Map />
      </PaperProvider>
    );
    const map = screen.getByTestId('mower-map');

    fireEvent.press(map, { nativeEvent: { lngLat: [-74.006, 40.7128] } });
    fireEvent.press(map, { nativeEvent: { lngLat: [-74.005, 40.7128] } });
    fireEvent.press(map, { nativeEvent: { lngLat: [-74.005, 40.7138] } });
    fireEvent.press(screen.getByTestId('accept-boundary'));
    await waitFor(() => expect(screen.getByText('Start cutting session?')).toBeTruthy());

    fireEvent.press(screen.getByText('Cancel'));
    await waitFor(() =>
      expect(screen.getByText('Review the boundary, then accept it to continue.')).toBeTruthy()
    );
    expect(screen.getByText('Clear boundary')).toBeTruthy();
    expect(screen.getByTestId('accept-boundary')).toBeTruthy();
  });
});

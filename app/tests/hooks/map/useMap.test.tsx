import { beforeEach, describe, expect, it, jest } from '@jest/globals';
import { act, renderHook, waitFor } from '@testing-library/react-native';
import * as ScreenOrientation from 'expo-screen-orientation';
import { useMap } from '@/hooks/map/useMap';
import { useBoundStore } from '@/store/useBoundStore';

jest.mock('expo-router', () => {
  const React = require('react');
  return {
    useFocusEffect: (effect: () => void | (() => void)) => React.useEffect(effect, [effect]),
  };
});

describe('useMap', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useBoundStore.getState().resetStore();
  });

  it('locks to landscape, accepts a drawing into a mowing session, and unlocks on exit', async () => {
    const { result, unmount } = renderHook(() => useMap());
    await waitFor(() => expect(result.current.mowerMarkers).toHaveLength(6));
    expect(ScreenOrientation.lockAsync).toHaveBeenCalledWith(
      ScreenOrientation.OrientationLock.LANDSCAPE
    );

    act(() => {
      result.current.addBoundaryPoint({ x: -74.006, y: 40.7128 });
      result.current.addBoundaryPoint({ x: -74.005, y: 40.7128 });
      result.current.addBoundaryPoint({ x: -74.005, y: 40.7138 });
    });
    expect(result.current.isConfirmModalVisible).toBe(false);

    act(() => result.current.acceptBoundary());
    expect(result.current.isConfirmModalVisible).toBe(true);

    act(() => result.current.dismissConfirmModal());
    expect(result.current).toMatchObject({
      isConfirmModalVisible: false,
      drawingBoundary: expect.any(Array),
    });
    expect(result.current.drawingBoundary).toHaveLength(3);

    act(() => result.current.acceptBoundary());

    act(() => result.current.confirmCuttingArea());
    expect(result.current).toMatchObject({ isSessionActive: true, isSessionPaused: false });
    expect(useBoundStore.getState().areaImageUri).toMatch(/cutting-area-preview/);

    unmount();
    expect(ScreenOrientation.lockAsync).toHaveBeenCalledWith(
      ScreenOrientation.OrientationLock.PORTRAIT_UP
    );
  });
});

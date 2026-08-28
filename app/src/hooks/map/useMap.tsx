import { useCallback, useMemo, useState } from 'react';
import { Image } from 'react-native';
import { useBoundaryDrawing } from './useBoundaryDrawing';
import { useLandscapeMap } from './useLandscapeMap';
import { useBoundStore } from '@/store/useBoundStore';

const LOCAL_CUTTING_AREA_IMAGE_URI =
  Image.resolveAssetSource(require('@/assets/images/cutting-area-preview.png'))?.uri ??
  'asset:///cutting-area-preview.png';

export function useMap() {
  const [isConfirmModalVisible, setConfirmModalVisible] = useState(false);
  const { addPoint, clear, points, undo } = useBoundaryDrawing();
  const mowerDetails = useBoundStore((state) => state.mowerDetails);
  const mowerPositions = useBoundStore((state) => state.mowerPositions);
  const isSessionActive = useBoundStore((state) => state.isSessionActive);
  const isSessionPaused = useBoundStore((state) => state.isSessionPaused);
  const cuttingBoundary = useBoundStore((state) => state.cuttingBoundary);
  const startMowingSession = useBoundStore((state) => state.startMowingSession);
  const setSessionPaused = useBoundStore((state) => state.setSessionPaused);
  const cancelMowingSession = useBoundStore((state) => state.cancelMowingSession);

  useLandscapeMap();
  const confirmCuttingArea = useCallback(() => {
    if (points.length < 3) return;
    startMowingSession(points, LOCAL_CUTTING_AREA_IMAGE_URI);
    setConfirmModalVisible(false);
    clear();
  }, [clear, points, startMowingSession]);

  const acceptBoundary = useCallback(() => {
    if (points.length >= 3) setConfirmModalVisible(true);
  }, [points.length]);

  const dismissConfirmModal = useCallback(() => {
    setConfirmModalVisible(false);
  }, []);

  const clearBoundary = useCallback(() => {
    setConfirmModalVisible(false);
    clear();
  }, [clear]);

  const undoBoundaryPoint = useCallback(() => {
    setConfirmModalVisible(false);
    undo();
  }, [undo]);

  const cancelSession = useCallback(() => {
    cancelMowingSession();
    clear();
  }, [cancelMowingSession, clear]);

  const mowerMarkers = useMemo(
    () =>
      Object.entries(mowerPositions).map(([uuid, position]) => ({
        id: uuid,
        name: mowerDetails[uuid]?.name ?? `Mower ${uuid.slice(0, 8)}`,
        ...position,
      })),
    [mowerDetails, mowerPositions]
  );

  return {
    addBoundaryPoint: addPoint,
    acceptBoundary,
    cancelSession,
    clearBoundary,
    confirmCuttingArea,
    cuttingBoundary,
    drawingBoundary: points,
    dismissConfirmModal,
    isConfirmModalVisible,
    isSessionActive,
    isSessionPaused,
    mowerMarkers,
    setConfirmModalVisible,
    setSessionPaused,
    undoBoundaryPoint,
  };
}

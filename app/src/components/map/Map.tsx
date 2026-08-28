import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { useMap } from '@/hooks/map/useMap';
import { BoundaryControls } from './BoundaryControls';
import { ConfirmCuttingAreaModal } from './ConfirmCuttingAreaModal';
import { MapCanvas } from './MapCanvas';
import { MapStyleSelector } from './MapStyleSelector';
import { MapSessionControls } from './MapSessionControls';

export function Map() {
  const [baseMap, setBaseMap] = useState<'satellite' | 'street'>('satellite');
  const {
    addBoundaryPoint,
    acceptBoundary,
    cancelSession,
    clearBoundary,
    confirmCuttingArea,
    cuttingBoundary,
    dismissConfirmModal,
    drawingBoundary,
    isConfirmModalVisible,
    isSessionActive,
    isSessionPaused,
    mowerMarkers,
    setSessionPaused,
    undoBoundaryPoint,
  } = useMap();

  const boundary = isSessionActive ? cuttingBoundary : drawingBoundary;

  return (
    <View style={styles.container}>
      <MapCanvas
        baseMap={baseMap}
        boundary={boundary}
        isBoundaryClosed={isConfirmModalVisible || isSessionActive}
        isSessionActive={isSessionActive}
        mowerMarkers={isSessionActive ? mowerMarkers : []}
        onMapPress={addBoundaryPoint}
      />
      <MapStyleSelector baseMap={baseMap} onChange={setBaseMap} />
      {isSessionActive ? (
        <MapSessionControls
          isPaused={isSessionPaused}
          mowerCount={mowerMarkers.length}
          onCancel={cancelSession}
          onPauseToggle={() => setSessionPaused(!isSessionPaused)}
        />
      ) : (
        <BoundaryControls
          canPlacePoints={baseMap === 'satellite'}
          pointCount={drawingBoundary.length}
          onAccept={acceptBoundary}
          onClear={clearBoundary}
          onUndo={undoBoundaryPoint}
        />
      )}
      <ConfirmCuttingAreaModal
        visible={isConfirmModalVisible}
        onCancel={dismissConfirmModal}
        onConfirm={confirmCuttingArea}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
});

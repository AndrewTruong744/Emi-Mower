import { StyleSheet, View } from 'react-native';
import { Button, Text } from 'react-native-paper';

interface BoundaryControlsProps {
  canPlacePoints?: boolean;
  pointCount: number;
  onAccept: () => void;
  onClear: () => void;
}

export function BoundaryControls({
  canPlacePoints = true,
  pointCount,
  onAccept,
  onClear,
}: BoundaryControlsProps) {
  return (
    <View style={styles.container}>
      <Text variant="labelLarge" style={styles.text}>
        {!canPlacePoints
          ? 'Switch to satellite imagery to place boundary points.'
          : pointCount < 3
            ? `Tap the map to add boundary points (${pointCount}/3 minimum).`
            : 'Review the boundary, then accept it to continue.'}
      </Text>
      {pointCount > 0 && (
        <View style={styles.actions} testID="boundary-actions">
          <Button onPress={onClear}>Clear boundary</Button>
          {canPlacePoints && pointCount >= 3 && (
            <Button mode="contained" onPress={onAccept} testID="accept-boundary">
              Accept boundary
            </Button>
          )}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  actions: { alignItems: 'center', flexDirection: 'row', gap: 8, justifyContent: 'space-between' },
  container: {
    alignItems: 'center',
    backgroundColor: 'rgba(15, 23, 42, 0.92)',
    borderRadius: 12,
    bottom: 16,
    left: 16,
    padding: 10,
    position: 'absolute',
    right: 16,
  },
  text: { color: '#FFFFFF', textAlign: 'center' },
});

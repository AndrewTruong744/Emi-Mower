import { StyleSheet, View } from 'react-native';
import { Button } from 'react-native-paper';
import type { MapBaseLayer } from './MapCanvas';

interface MapStyleSelectorProps {
  baseMap: MapBaseLayer;
  onChange: (baseMap: MapBaseLayer) => void;
}

export function MapStyleSelector({ baseMap, onChange }: MapStyleSelectorProps) {
  return (
    <View style={styles.container} testID="map-style-selector">
      <Button
        compact
        mode={baseMap === 'satellite' ? 'contained' : 'outlined'}
        onPress={() => onChange('satellite')}
        testID="map-style-satellite"
      >
        Satellite
      </Button>
      <Button
        compact
        mode={baseMap === 'street' ? 'contained' : 'outlined'}
        onPress={() => onChange('street')}
        testID="map-style-street"
      >
        Street
      </Button>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: 'rgba(255, 255, 255, 0.94)',
    borderRadius: 12,
    flexDirection: 'row',
    gap: 6,
    left: 16,
    padding: 6,
    position: 'absolute',
    top: 16,
  },
});

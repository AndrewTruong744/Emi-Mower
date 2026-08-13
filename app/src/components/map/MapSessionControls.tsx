import { StyleSheet, View } from 'react-native';
import { Button, Surface, Text } from 'react-native-paper';

interface MapSessionControlsProps {
  isPaused: boolean;
  mowerCount: number;
  onCancel: () => void;
  onPauseToggle: () => void;
}

export function MapSessionControls({ isPaused, mowerCount, onCancel, onPauseToggle }: MapSessionControlsProps) {
  return (
    <Surface elevation={3} style={styles.container}>
      <View>
        <Text variant="titleMedium" style={styles.title}>
          {isPaused ? 'Mowing paused' : 'Mowing session active'}
        </Text>
        <Text variant="bodySmall">{mowerCount} mower{mowerCount === 1 ? '' : 's'} assigned to this area</Text>
      </View>
      <View style={styles.actions}>
        <Button mode="contained" onPress={onPauseToggle} testID="pause-mowing-session">
          {isPaused ? 'Resume' : 'Pause'}
        </Button>
        <Button mode="outlined" textColor="#dc2626" onPress={onCancel} testID="cancel-mowing-session">
          Cancel
        </Button>
      </View>
    </Surface>
  );
}

const styles = StyleSheet.create({
  actions: { flexDirection: 'row', gap: 8 },
  container: { alignItems: 'center', borderRadius: 12, bottom: 16, flexDirection: 'row', justifyContent: 'space-between', left: 16, padding: 12, position: 'absolute', right: 16 },
  title: { fontWeight: '700' },
});

import { ActivityIndicator, Text } from 'react-native-paper';
import { StyleSheet, View } from 'react-native';
import { useBoundStore } from '@/store/useBoundStore';
import { MowerIdentitySection } from './MowerIdentitySection';
import { MowerStatusSection } from './MowerStatusSection';
import { MowerTelemetrySection } from './MowerTelemetrySection';

interface MowerDetailsContentProps {
  mowerId: string | null;
  onEditName: () => void;
}

/** Renders only the selected mower so unrelated fleet telemetry cannot redraw it. */
export function MowerDetailsContent({ mowerId, onEditName }: MowerDetailsContentProps) {
  const mower = useBoundStore((state) => (mowerId ? state.mowerDetails[mowerId] ?? null : null));

  if (!mower) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator />
        <Text>Loading mower data…</Text>
      </View>
    );
  }

  return (
    <>
      <MowerIdentitySection mower={mower} onEditName={onEditName} />
      <MowerStatusSection mower={mower} />
      <MowerTelemetrySection mower={mower} />
    </>
  );
}

const styles = StyleSheet.create({
  loading: { alignItems: 'center', gap: 10, paddingVertical: 48 },
});

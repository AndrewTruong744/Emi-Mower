import { StyleSheet, View } from 'react-native';
import { Surface, Text } from 'react-native-paper';
import { MowerDetails } from '@/store/types';

interface MowerStatusSectionProps {
  mower: MowerDetails;
}

const stateColors = { on: '#16a34a', off: '#64748b', stopped: '#dc2626', unknown: '#64748b' };
const healthColors = { healthy: '#16a34a', attention: '#d97706', critical: '#dc2626', unknown: '#64748b' };

export function MowerStatusSection({ mower }: MowerStatusSectionProps) {
  return (
    <Surface elevation={1} style={styles.card}>
      <Text variant="titleMedium" style={styles.title}>
        Current status
      </Text>
      <View style={styles.metrics}>
        <StatusMetric label="Battery" value={mower.battery == null ? '—' : `${Math.round(mower.battery)}%`} color="#2563eb" />
        <StatusMetric label="State" value={mower.state.toUpperCase()} color={stateColors[mower.state]} />
        <StatusMetric label="Health" value={mower.health.replace('-', ' ').toUpperCase()} color={healthColors[mower.health]} />
      </View>
    </Surface>
  );
}

function StatusMetric({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <View style={styles.metric}>
      <Text variant="labelMedium" style={styles.label}>
        {label}
      </Text>
      <Text variant="titleMedium" style={[styles.value, { color }]}> 
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderRadius: 16, marginBottom: 16, padding: 16 },
  label: { opacity: 0.65 },
  metrics: { flexDirection: 'row', gap: 12, justifyContent: 'space-between' },
  metric: { flex: 1 },
  title: { fontWeight: '700', marginBottom: 14 },
  value: { fontWeight: '700', marginTop: 3 },
});

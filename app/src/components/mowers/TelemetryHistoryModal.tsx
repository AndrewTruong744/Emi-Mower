import { StyleSheet, View } from 'react-native';
import { Button, Modal, Portal, Text } from 'react-native-paper';
import { MetricChartProps, MetricChart } from './MetricChart';
import { useTelemetryHistoryModal } from '@/hooks/mowers/useTelemetryHistoryModal';

interface TelemetryHistoryModalProps {
  chart: MetricChartProps;
  mowerId: string;
  onDismiss: () => void;
}

export function TelemetryHistoryModal({ chart, mowerId, onDismiss }: TelemetryHistoryModalProps) {
  const { canViewNewer, canViewOlder, isLoadingOlder, page, pages, viewNewer, viewOlder } =
    useTelemetryHistoryModal({ chart, mowerId });
  const values = pages[page] ?? chart.values;

  return (
    <Portal>
      <Modal visible={Boolean(chart)} onDismiss={onDismiss} contentContainerStyle={styles.modal}>
        <Text variant="titleLarge" style={styles.title}>
          {chart.title} history
        </Text>
        <Text variant="bodySmall" style={styles.caption}>
          {page === 0 ? `Live telemetry window · ${chart.values.length} received samples` : `Historical page ${page} · ${values.length} records`}
        </Text>
        <View>
          <MetricChart {...chart} values={values} style={styles.chart} />
        </View>
        <View style={styles.controls}>
          <Button disabled={!canViewNewer} onPress={viewNewer} testID="telemetry-history-newer">Newer</Button>
          <Text variant="labelMedium">Page {page + 1}</Text>
          <Button disabled={!canViewOlder} loading={isLoadingOlder} onPress={viewOlder} testID="telemetry-history-older">Older</Button>
        </View>
        <Button mode="contained-tonal" onPress={onDismiss}>
          Close
        </Button>
      </Modal>
    </Portal>
  );
}

const styles = StyleSheet.create({
  caption: { marginBottom: 12, opacity: 0.7 },
  chart: { marginBottom: 12 },
  controls: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  modal: { backgroundColor: 'white', borderRadius: 20, margin: 20, padding: 20 },
  title: { fontWeight: '700' },
});

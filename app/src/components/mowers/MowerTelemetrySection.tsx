import { ReactNode, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Surface, Text } from 'react-native-paper';
import { MowerDetails } from '@/store/types';
import { LoopingMetricCarousel } from './LoopingMetricCarousel';
import { MetricChartProps } from './MetricChart';
import { TelemetryHistoryModal } from './TelemetryHistoryModal';

interface MowerTelemetrySectionProps {
  mower: MowerDetails;
}

export function MowerTelemetrySection({ mower }: MowerTelemetrySectionProps) {
  const [focusedChart, setFocusedChart] = useState<MetricChartProps | null>(null);
  const telemetry = mower.telemetry;
  const latest = telemetry.at(-1);

  if (!latest) {
    return (
      <Surface elevation={1} style={styles.emptyCard}>
        <Text variant="titleMedium" style={styles.title}>Session telemetry</Text>
        <Text variant="bodyMedium" style={styles.emptyText}>
          Waiting for live telemetry from this mower.
        </Text>
      </Surface>
    );
  }

  const focusable = (chart: MetricChartProps) => ({ ...chart, onPress: () => setFocusedChart(chart) });

  return (
    <View>
      <Text variant="titleMedium" style={styles.title}>
        Session telemetry
      </Text>
      <TelemetryGroup title="Drive motors">
        <LoopingMetricCarousel
          testID="drive-motor-charts"
          charts={[
            focusable({
              title: 'Left motor speed',
              telemetryType: 'left_motor_speed',
              value: `${latest.leftMotorSpeed.toFixed(2)} × (${formatDirection(latest.leftMotorDirection)})`,
              values: telemetry.map((sample) => sample.leftMotorSpeed),
              color: '#2563eb',
            }),
            focusable({
              title: 'Right motor speed',
              telemetryType: 'right_motor_speed',
              value: `${latest.rightMotorSpeed.toFixed(2)} × (${formatDirection(latest.rightMotorDirection)})`,
              values: telemetry.map((sample) => sample.rightMotorSpeed),
              color: '#7c3aed',
            }),
            focusable({
              title: 'Cutting motor speed',
              telemetryType: 'cutting_motor_speed',
              value: `${latest.cuttingMotorSpeed.toLocaleString()} RPM`,
              values: telemetry.map((sample) => sample.cuttingMotorSpeed),
              color: '#059669',
            }),
          ]}
        />
      </TelemetryGroup>

      <TelemetryGroup title="Safety">
        <LoopingMetricCarousel
          testID="safety-charts"
          charts={[
            focusable({
              title: 'Slippage detected',
              telemetryType: 'slippage_detected',
              value: latest.slippageDetected ? 'Detected' : 'None',
              values: telemetry.map((sample) => (sample.slippageDetected ? 1 : 0)),
              color: '#dc2626',
            }),
          ]}
        />
      </TelemetryGroup>

      {latest.imuData && <ImuTelemetry telemetry={telemetry} latest={latest.imuData} focusable={focusable} />}
      {focusedChart && <TelemetryHistoryModal chart={focusedChart} mowerId={mower.uuid} onDismiss={() => setFocusedChart(null)} />}
    </View>
  );
}

function ImuTelemetry({
  telemetry,
  latest,
  focusable,
}: {
  telemetry: MowerDetails['telemetry'];
  latest: NonNullable<MowerDetails['telemetry'][number]['imuData']>;
  focusable: (chart: MetricChartProps) => MetricChartProps;
}) {
  const values = (key: keyof typeof latest) =>
    telemetry.flatMap((sample) => (sample.imuData ? [sample.imuData[key]] : []));

  return (
    <>
      <TelemetryGroup title="IMU accelerometer">
        <LoopingMetricCarousel testID="accelerometer-charts" charts={[
          focusable(imuChart('Acceleration X', latest.accelX, values('accelX'), '#0891b2', 'm/s²', 'accel_x')),
          focusable(imuChart('Acceleration Y', latest.accelY, values('accelY'), '#0284c7', 'm/s²', 'accel_y')),
          focusable(imuChart('Acceleration Z', latest.accelZ, values('accelZ'), '#0369a1', 'm/s²', 'accel_z')),
        ]} />
      </TelemetryGroup>
      <TelemetryGroup title="IMU gyroscope">
        <LoopingMetricCarousel testID="gyroscope-charts" charts={[
          focusable(imuChart('Gyroscope X', latest.gyroX, values('gyroX'), '#ea580c', 'rad/s', 'gyro_x')),
          focusable(imuChart('Gyroscope Y', latest.gyroY, values('gyroY'), '#f97316', 'rad/s', 'gyro_y')),
          focusable(imuChart('Gyroscope Z', latest.gyroZ, values('gyroZ'), '#c2410c', 'rad/s', 'gyro_z')),
        ]} />
      </TelemetryGroup>
      <TelemetryGroup title="IMU magnetometer">
        <LoopingMetricCarousel testID="magnetometer-charts" charts={[
          focusable(imuChart('Magnetometer X', latest.magX, values('magX'), '#a21caf', 'µT', 'mag_x')),
          focusable(imuChart('Magnetometer Y', latest.magY, values('magY'), '#c026d3', 'µT', 'mag_y')),
          focusable(imuChart('Magnetometer Z', latest.magZ, values('magZ'), '#86198f', 'µT', 'mag_z')),
        ]} />
      </TelemetryGroup>
    </>
  );
}

function TelemetryGroup({ title, children }: { title: string; children: ReactNode }) {
  return (
    <View style={styles.group}>
      <Text variant="titleSmall" style={styles.groupTitle}>
        {title}
      </Text>
      {children}
    </View>
  );
}

function formatDirection(direction: -1 | 0 | 1) {
  return direction === 1 ? 'forward' : direction === -1 ? 'reverse' : 'stopped';
}

function imuChart(title: string, value: number, values: number[], color: string, unit = 'm/s²', telemetryType?: string) {
  return { title, telemetryType, value: `${value.toFixed(2)} ${unit}`, values, color };
}

const styles = StyleSheet.create({
  emptyCard: { borderRadius: 16, marginTop: 16, padding: 16 },
  emptyText: { marginTop: 6, opacity: 0.65 },
  group: { marginTop: 12 },
  groupTitle: { fontWeight: '700', marginBottom: 8 },
  title: { fontWeight: '700' },
});

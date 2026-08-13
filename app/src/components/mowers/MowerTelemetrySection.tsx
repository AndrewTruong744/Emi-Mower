import { ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
import { MowerDetails } from '@/store/types';
import { LoopingMetricCarousel } from './LoopingMetricCarousel';

interface MowerTelemetrySectionProps {
  mower: MowerDetails;
}

export function MowerTelemetrySection({ mower }: MowerTelemetrySectionProps) {
  const telemetry = mower.telemetry;
  const latest = telemetry.at(-1);

  if (!latest) return null;

  return (
    <View>
      <Text variant="titleMedium" style={styles.title}>
        Session telemetry
      </Text>
      <TelemetryGroup title="Drive motors">
        <LoopingMetricCarousel
          testID="drive-motor-charts"
          charts={[
            {
              title: 'Left motor speed',
              value: `${latest.leftMotorSpeed.toFixed(2)} × (${formatDirection(latest.leftMotorDirection)})`,
              values: telemetry.map((sample) => sample.leftMotorSpeed),
              color: '#2563eb',
            },
            {
              title: 'Right motor speed',
              value: `${latest.rightMotorSpeed.toFixed(2)} × (${formatDirection(latest.rightMotorDirection)})`,
              values: telemetry.map((sample) => sample.rightMotorSpeed),
              color: '#7c3aed',
            },
            {
              title: 'Cutting motor speed',
              value: `${latest.cuttingMotorSpeed.toLocaleString()} RPM`,
              values: telemetry.map((sample) => sample.cuttingMotorSpeed),
              color: '#059669',
            },
          ]}
        />
      </TelemetryGroup>

      <TelemetryGroup title="Safety">
        <LoopingMetricCarousel
          testID="safety-charts"
          charts={[
            {
              title: 'Slippage detected',
              value: latest.slippageDetected ? 'Detected' : 'None',
              values: telemetry.map((sample) => (sample.slippageDetected ? 1 : 0)),
              color: '#dc2626',
            },
          ]}
        />
      </TelemetryGroup>

      <TelemetryGroup title="IMU accelerometer">
        <LoopingMetricCarousel
          testID="accelerometer-charts"
          charts={[
            imuChart('Acceleration X', latest.imuData.accelX, telemetry.map((sample) => sample.imuData.accelX), '#0891b2'),
            imuChart('Acceleration Y', latest.imuData.accelY, telemetry.map((sample) => sample.imuData.accelY), '#0284c7'),
            imuChart('Acceleration Z', latest.imuData.accelZ, telemetry.map((sample) => sample.imuData.accelZ), '#0369a1'),
          ]}
        />
      </TelemetryGroup>

      <TelemetryGroup title="IMU gyroscope">
        <LoopingMetricCarousel
          testID="gyroscope-charts"
          charts={[
            imuChart('Gyroscope X', latest.imuData.gyroX, telemetry.map((sample) => sample.imuData.gyroX), '#ea580c', 'rad/s'),
            imuChart('Gyroscope Y', latest.imuData.gyroY, telemetry.map((sample) => sample.imuData.gyroY), '#f97316', 'rad/s'),
            imuChart('Gyroscope Z', latest.imuData.gyroZ, telemetry.map((sample) => sample.imuData.gyroZ), '#c2410c', 'rad/s'),
          ]}
        />
      </TelemetryGroup>

      <TelemetryGroup title="IMU magnetometer">
        <LoopingMetricCarousel
          testID="magnetometer-charts"
          charts={[
            imuChart('Magnetometer X', latest.imuData.magX, telemetry.map((sample) => sample.imuData.magX), '#a21caf', 'µT'),
            imuChart('Magnetometer Y', latest.imuData.magY, telemetry.map((sample) => sample.imuData.magY), '#c026d3', 'µT'),
            imuChart('Magnetometer Z', latest.imuData.magZ, telemetry.map((sample) => sample.imuData.magZ), '#86198f', 'µT'),
          ]}
        />
      </TelemetryGroup>
    </View>
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

function imuChart(title: string, value: number, values: number[], color: string, unit = 'm/s²') {
  return { title, value: `${value.toFixed(2)} ${unit}`, values, color };
}

const styles = StyleSheet.create({
  group: { marginTop: 12 },
  groupTitle: { fontWeight: '700', marginBottom: 8 },
  title: { fontWeight: '700' },
});

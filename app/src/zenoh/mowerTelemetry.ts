import { zenohSubscribe } from '@/config/zenohClient';
import type { ImuTelemetry, TelemetryList, TelemetryRecord } from '@/generated/zenoh';
import { MowerImuTelemetry, MowerTelemetrySample } from '@/store/types';

export const MOWER_TELEMETRY_KEY_EXPR = 'mower/*/telemetry';

export interface MowerTelemetryMessage {
  mowerId: string;
  sample: MowerTelemetrySample;
}

function asFiniteNumber(value: unknown, field: string): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new Error(`Telemetry ${field} must be a finite number`);
  }
  return value;
}

function asDirection(value: unknown, field: string): -1 | 0 | 1 {
  if (value == null) return 0;
  if (value === -1 || value === 0 || value === 1) return value;
  throw new Error(`Telemetry ${field} must be -1, 0, or 1`);
}

function parseImu(value: ImuTelemetry | null | undefined): MowerImuTelemetry | null {
  if (value == null) return null;
  return {
    accelX: asFiniteNumber(value.accel_x, 'imu_data.accel_x'),
    accelY: asFiniteNumber(value.accel_y, 'imu_data.accel_y'),
    accelZ: asFiniteNumber(value.accel_z, 'imu_data.accel_z'),
    gyroX: asFiniteNumber(value.gyro_x, 'imu_data.gyro_x'),
    gyroY: asFiniteNumber(value.gyro_y, 'imu_data.gyro_y'),
    gyroZ: asFiniteNumber(value.gyro_z, 'imu_data.gyro_z'),
    magX: asFiniteNumber(value.mag_x, 'imu_data.mag_x'),
    magY: asFiniteNumber(value.mag_y, 'imu_data.mag_y'),
    magZ: asFiniteNumber(value.mag_z, 'imu_data.mag_z'),
  };
}

function parseRecord(record: TelemetryRecord): MowerTelemetryMessage {
  if (!record || typeof record.mower_id !== 'string' || !record.mower_id.trim()) {
    throw new Error('Telemetry mower_id is required');
  }
  const timestamp = Date.parse(record.timestamp);
  if (!Number.isFinite(timestamp)) throw new Error('Telemetry timestamp must be an ISO date');

  return {
    mowerId: record.mower_id,
    sample: {
      timestamp,
      latitude: asFiniteNumber(record.latitude, 'latitude'),
      longitude: asFiniteNumber(record.longitude, 'longitude'),
      batteryPercentage: asFiniteNumber(record.battery_percentage, 'battery_percentage'),
      leftMotorSpeed:
        record.left_motor_speed == null
          ? 0
          : asFiniteNumber(record.left_motor_speed, 'left_motor_speed'),
      leftMotorDirection: asDirection(record.left_motor_direction, 'left_motor_direction'),
      rightMotorSpeed:
        record.right_motor_speed == null
          ? 0
          : asFiniteNumber(record.right_motor_speed, 'right_motor_speed'),
      rightMotorDirection: asDirection(record.right_motor_direction, 'right_motor_direction'),
      cuttingMotorSpeed:
        record.cutting_motor_speed == null
          ? 0
          : asFiniteNumber(record.cutting_motor_speed, 'cutting_motor_speed'),
      slippageDetected: record.slippage_detected ?? false,
      imuData: parseImu(record.imu_data),
    },
  };
}

/** Parse the backend's AsyncAPI TelemetryList payload into app telemetry samples. */
export function parseMowerTelemetryPayload(payload: string): MowerTelemetryMessage[] {
  let value: unknown;
  try {
    value = JSON.parse(payload);
  } catch {
    throw new Error('Telemetry payload is not valid JSON');
  }
  if (!Array.isArray(value)) throw new Error('Telemetry payload must be an array');
  return (value as TelemetryList).map(parseRecord);
}

/** Subscribe to the same mower telemetry model accepted by the backend listener. */
export async function subscribeToMowerTelemetry(
  onTelemetry: (messages: MowerTelemetryMessage[]) => void,
  onError: (error: Error) => void,
  onClose?: () => void
): Promise<() => Promise<void>> {
  return zenohSubscribe(
    MOWER_TELEMETRY_KEY_EXPR,
    (payload) => {
      try {
        onTelemetry(parseMowerTelemetryPayload(payload));
      } catch (error) {
        onError(error instanceof Error ? error : new Error('Unable to decode mower telemetry'));
      }
    },
    onClose
  );
}

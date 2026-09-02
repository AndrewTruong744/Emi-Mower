import { describe, expect, it } from '@jest/globals';
import { parseMowerTelemetryPayload } from '@/zenoh/mowerTelemetry';
import type { TelemetryList } from '@/generated/zenoh';

const backendRecord: TelemetryList[number] = {
  mower_id: 'mower-1',
  timestamp: '2026-08-16T12:00:00.000Z',
  latitude: 40.7128,
  longitude: -74.006,
  battery_percentage: 81,
  left_motor_speed: 0.7,
  left_motor_direction: -1,
  right_motor_speed: 0.6,
  right_motor_direction: 1,
  cutting_motor_speed: 2780,
  slippage_detected: true,
  imu_data: {
    accel_x: 0.1,
    accel_y: 0.2,
    accel_z: 9.8,
    gyro_x: 0.01,
    gyro_y: 0.02,
    gyro_z: 0.03,
    mag_x: 20,
    mag_y: 2,
    mag_z: 40,
  },
};

describe('mower telemetry Zenoh listener', () => {
  it('decodes the backend telemetry list model, including optional fields', () => {
    const messages = parseMowerTelemetryPayload(
      JSON.stringify([
        backendRecord,
        {
          ...backendRecord,
          mower_id: 'mower-2',
          timestamp: '2026-08-16T12:00:01.000Z',
          imu_data: null,
        },
      ])
    );

    expect(messages).toEqual([
      expect.objectContaining({
        mowerId: 'mower-1',
        sample: expect.objectContaining({
          timestamp: Date.parse(backendRecord.timestamp),
          leftMotorDirection: -1,
          imuData: {
            accelX: 0.1,
            accelY: 0.2,
            accelZ: 9.8,
            gyroX: 0.01,
            gyroY: 0.02,
            gyroZ: 0.03,
            magX: 20,
            magY: 2,
            magZ: 40,
          },
        }),
      }),
      expect.objectContaining({
        mowerId: 'mower-2',
        sample: expect.objectContaining({ imuData: null }),
      }),
    ]);
  });

  it('rejects malformed payloads', () => {
    expect(() => parseMowerTelemetryPayload('{')).toThrow('not valid JSON');
    expect(() => parseMowerTelemetryPayload(JSON.stringify({ ...backendRecord }))).toThrow(
      'must be an array'
    );
    expect(() => parseMowerTelemetryPayload(JSON.stringify([null]))).toThrow('mower_id');
    expect(() =>
      parseMowerTelemetryPayload(JSON.stringify([{ ...backendRecord, mower_id: '   ' }]))
    ).toThrow('mower_id');
    expect(() =>
      parseMowerTelemetryPayload(JSON.stringify([{ ...backendRecord, timestamp: 'not-a-date' }]))
    ).toThrow('timestamp');
    expect(() =>
      parseMowerTelemetryPayload(JSON.stringify([{ ...backendRecord, left_motor_direction: 2 }]))
    ).toThrow('left_motor_direction');
  });

  it('rejects non-finite numeric fields and malformed IMU data', () => {
    for (const field of ['latitude', 'longitude', 'battery_percentage'] as const) {
      expect(() =>
        parseMowerTelemetryPayload(
          JSON.stringify([{ ...backendRecord, [field]: Number.NaN }])
        )
      ).toThrow(field);
    }

    expect(() =>
      parseMowerTelemetryPayload(
        JSON.stringify([{ ...backendRecord, imu_data: { ...backendRecord.imu_data, gyro_z: null } }])
      )
    ).toThrow('imu_data.gyro_z');
  });

  it('applies defaults for omitted optional motion and direction fields', () => {
    const [message] = parseMowerTelemetryPayload(
      JSON.stringify([
        {
          ...backendRecord,
          left_motor_speed: null,
          left_motor_direction: null,
          right_motor_speed: undefined,
          right_motor_direction: undefined,
          cutting_motor_speed: null,
          slippage_detected: undefined,
        },
      ])
    );

    expect(message.sample).toMatchObject({
      leftMotorSpeed: 0,
      leftMotorDirection: 0,
      rightMotorSpeed: 0,
      rightMotorDirection: 0,
      cuttingMotorSpeed: 0,
      slippageDetected: false,
    });
  });
});

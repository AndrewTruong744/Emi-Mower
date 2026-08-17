import { describe, expect, it, jest } from '@jest/globals';
import {
  MOWER_TELEMETRY_KEY_EXPR,
  parseMowerTelemetryPayload,
  subscribeToMowerTelemetry,
} from '@/zenoh/mowerTelemetry';
import { zenohSubscribe } from '@/config/zenohClient';
import type { TelemetryList } from '@/generated/zenoh';

jest.mock('@/config/zenohClient', () => ({ zenohSubscribe: jest.fn() }));
const mockZenohSubscribe = zenohSubscribe as jest.Mock<(...args: any[]) => any>;

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
    accel_x: 0.1, accel_y: 0.2, accel_z: 9.8,
    gyro_x: 0.01, gyro_y: 0.02, gyro_z: 0.03,
    mag_x: 20, mag_y: 2, mag_z: 40,
  },
};

describe('mower telemetry Zenoh listener', () => {
  it('decodes the backend telemetry list model, including optional fields', () => {
    const messages = parseMowerTelemetryPayload(JSON.stringify([
      backendRecord,
      { ...backendRecord, mower_id: 'mower-2', timestamp: '2026-08-16T12:00:01.000Z', imu_data: null },
    ]));

    expect(messages).toEqual([
      expect.objectContaining({
        mowerId: 'mower-1',
        sample: expect.objectContaining({
          timestamp: Date.parse(backendRecord.timestamp),
          leftMotorDirection: -1,
          imuData: { accelX: 0.1, accelY: 0.2, accelZ: 9.8, gyroX: 0.01, gyroY: 0.02, gyroZ: 0.03, magX: 20, magY: 2, magZ: 40 },
        }),
      }),
      expect.objectContaining({ mowerId: 'mower-2', sample: expect.objectContaining({ imuData: null }) }),
    ]);
  });

  it('rejects malformed payloads and reports a bad subscription message without ending the listener', async () => {
    expect(() => parseMowerTelemetryPayload('{')).toThrow('not valid JSON');
    expect(() => parseMowerTelemetryPayload(JSON.stringify({ ...backendRecord }))).toThrow('must be an array');
    expect(() => parseMowerTelemetryPayload(JSON.stringify([{ ...backendRecord, timestamp: 'not-a-date' }]))).toThrow('timestamp');
    expect(() => parseMowerTelemetryPayload(JSON.stringify([{ ...backendRecord, left_motor_direction: 2 }]))).toThrow('left_motor_direction');

    let payloadHandler: ((payload: string) => void) | undefined;
    mockZenohSubscribe.mockImplementation(async (_key: string, handler: (payload: string) => void) => {
      payloadHandler = handler;
      return async () => undefined;
    });
    const onTelemetry = jest.fn();
    const onError = jest.fn();
    await subscribeToMowerTelemetry(onTelemetry, onError);

    expect(mockZenohSubscribe).toHaveBeenCalledWith(MOWER_TELEMETRY_KEY_EXPR, expect.any(Function));
    payloadHandler!('invalid');
    payloadHandler!(JSON.stringify([backendRecord]));
    expect((onError.mock.calls[0][0] as Error).message).toContain('not valid JSON');
    expect(onTelemetry).toHaveBeenCalledWith([expect.objectContaining({ mowerId: 'mower-1' })]);
  });
});

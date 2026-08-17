import { describe, expect, it } from '@jest/globals';
import {
  ACTIVE_TELEMETRY_FLUSH_MS,
  BACKGROUND_TELEMETRY_FLUSH_MS,
  MAX_PENDING_TELEMETRY_PER_MOWER,
  TelemetryBuffer,
} from '@/hooks/mowers/telemetryBuffer';
import { MowerTelemetrySample } from '@/store/types';

const sample = (timestamp: number): MowerTelemetrySample => ({
  timestamp, latitude: 40, longitude: -74, batteryPercentage: 80,
  leftMotorSpeed: 0, leftMotorDirection: 0, rightMotorSpeed: 0, rightMotorDirection: 0,
  cuttingMotorSpeed: 0, slippageDetected: false, imuData: null,
});

describe('TelemetryBuffer', () => {
  it('flushes the active mower quickly and other mowers once per second without dropping queued samples', () => {
    const buffer = new TelemetryBuffer();
    buffer.enqueue('active', sample(1));
    buffer.enqueue('other', sample(1));

    expect(buffer.flush('active', ACTIVE_TELEMETRY_FLUSH_MS)).toEqual({ active: [sample(1)] });
    expect(buffer.flush('active', BACKGROUND_TELEMETRY_FLUSH_MS)).toEqual({ other: [sample(1)] });

    buffer.enqueue('other', sample(2));
    buffer.enqueue('other', sample(3));
    expect(buffer.flush('active', BACKGROUND_TELEMETRY_FLUSH_MS + ACTIVE_TELEMETRY_FLUSH_MS)).toEqual({});
    expect(buffer.flush('other', BACKGROUND_TELEMETRY_FLUSH_MS * 2)).toEqual({ other: [sample(2), sample(3)] });
  });

  it('bounds a stalled mower queue and reports overflow', () => {
    const buffer = new TelemetryBuffer();
    let overflowed = false;
    for (let index = 0; index <= MAX_PENDING_TELEMETRY_PER_MOWER; index += 1) {
      overflowed ||= buffer.enqueue('mower-1', sample(index));
    }
    expect(overflowed).toBe(true);
    const flushed = buffer.flush('mower-1', ACTIVE_TELEMETRY_FLUSH_MS);
    expect(flushed['mower-1']).toHaveLength(MAX_PENDING_TELEMETRY_PER_MOWER);
    expect(flushed['mower-1'][0].timestamp).toBe(1);
  });
});

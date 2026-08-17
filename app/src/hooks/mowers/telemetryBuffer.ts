import { MowerTelemetrySample } from '@/store/types';

export const ACTIVE_TELEMETRY_FLUSH_MS = 200;
export const BACKGROUND_TELEMETRY_FLUSH_MS = 1_000;
export const MAX_PENDING_TELEMETRY_PER_MOWER = 240;

/** Buffers every live message, then exposes due active/background batches. */
export class TelemetryBuffer {
  private readonly pending = new Map<string, MowerTelemetrySample[]>();
  private readonly lastFlushAt = new Map<string, number>();

  enqueue(mowerId: string, sample: MowerTelemetrySample): boolean {
    const queue = this.pending.get(mowerId) ?? [];
    queue.push(sample);
    const overflowed = queue.length > MAX_PENDING_TELEMETRY_PER_MOWER;
    if (overflowed) queue.splice(0, queue.length - MAX_PENDING_TELEMETRY_PER_MOWER);
    this.pending.set(mowerId, queue);
    return overflowed;
  }

  flush(activeMowerId: string | null, now: number): Record<string, MowerTelemetrySample[]> {
    const due: Record<string, MowerTelemetrySample[]> = {};
    for (const [mowerId, queue] of this.pending) {
      const interval = mowerId === activeMowerId ? ACTIVE_TELEMETRY_FLUSH_MS : BACKGROUND_TELEMETRY_FLUSH_MS;
      if (now - (this.lastFlushAt.get(mowerId) ?? 0) < interval) continue;
      due[mowerId] = queue.splice(0, queue.length);
      this.lastFlushAt.set(mowerId, now);
      if (queue.length === 0) this.pending.delete(mowerId);
    }
    return due;
  }

  clear(): void {
    this.pending.clear();
    this.lastFlushAt.clear();
  }
}

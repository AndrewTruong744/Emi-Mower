import { jest, describe, it, expect, beforeEach } from '@jest/globals';
import type { NativeSample } from '../../modules/emi-zenoh';

const mockCall = jest.fn<(request: string) => Promise<string>>();
const mockRemove = jest.fn();
let mockListener: (event: NativeSample) => void;
jest.mock('../../modules/emi-zenoh', () => ({
  __esModule: true,
  default: {
    call: (request: string) => mockCall(request),
    addListener: (_name: string, listener: typeof mockListener) => {
      mockListener = listener;
      return { remove: mockRemove };
    },
  },
}));
import { open } from '../../src/config/nativeZenoh';

const requests = () => mockCall.mock.calls.map(([request]) => JSON.parse(request));
beforeEach(() => {
  mockCall.mockReset();
  mockRemove.mockClear();
  mockCall.mockImplementation(async (request) => {
    const value = JSON.parse(request);
    return JSON.stringify({
      ok: true,
      result: value.op === 'connect' ? 123 : value.op === 'query' ? '{"name":"草🌱"}' : null,
    });
  });
});

describe('native Rust Zenoh adapter', () => {
  it('returns one payload per overlapping request and isolates out-of-order errors', async () => {
    const session = await open('tcp/127.0.0.1:7447');
    const pending = new Map<string, (response: string) => void>();
    mockCall.mockImplementation((request) => {
      const value = JSON.parse(request);
      if (value.op === 'query') return new Promise((resolve) => pending.set(value.key, resolve));
      return Promise.resolve(JSON.stringify({ ok: true, result: null }));
    });
    const slow = session.query('test/slow', '{}');
    const fast = session.query('test/fast', '{}');
    const failed = session.query('test/failed', '{}');
    const failure = expect(failed).rejects.toThrow('request rejected');
    expect(pending.size).toBe(3);
    await session.put('mower/A/joystick', '{}');
    pending.get('test/fast')!(JSON.stringify({ ok: true, result: 'fast 🌱' }));
    await expect(fast).resolves.toBe('fast 🌱');
    pending.get('test/failed')!(JSON.stringify({ ok: false, error: 'request rejected' }));
    await failure;
    pending.get('test/slow')!(JSON.stringify({ ok: true, result: 'slow 草🌱' }));
    await expect(slow).resolves.toBe('slow 草🌱');
    await session.close();
  });

  it('forwards plain samples and transport events, leaving replay to Rust', async () => {
    const session = await open('tls/example.test:7447');
    const transport = jest.fn();
    const samples = jest.fn();
    session.onTransport = transport;
    const unsubscribe = await session.subscribe('mower/A/telemetry', samples);
    const subscription = requests().find((r) => r.op === 'subscribe');
    expect(subscription.kind).toBe('data');
    const sample = {
      subscriptionId: subscription.subscription_id,
      key: 'mower/A/telemetry',
      payload: '草🌱',
      put: true,
    };
    mockListener(sample);
    expect(samples).toHaveBeenCalledWith(sample);
    mockListener({ subscriptionId: '@transport:123', key: '', payload: '', put: false });
    mockListener({ subscriptionId: '@transport:123', key: '', payload: '', put: true });
    expect(transport.mock.calls).toEqual([[false], [true]]);
    await session.restoreSubscriptions();
    expect(requests().filter((r) => r.op === 'subscribe')).toHaveLength(1);
    expect(requests().at(-1)).toEqual({ op: 'restore_subscriptions', session: 123 });
    await unsubscribe();
    await unsubscribe();
    mockListener(sample);
    expect(samples).toHaveBeenCalledTimes(1);
    expect(requests().filter((r) => r.op === 'unsubscribe')).toHaveLength(1);
    await session.close();
    expect(mockRemove).toHaveBeenCalledTimes(1);
    mockListener({ subscriptionId: '@transport:123', key: '', payload: '', put: true });
    expect(transport).toHaveBeenCalledTimes(2);
    await expect(session.subscribe('closed', samples)).rejects.toThrow('closed');
    await session.close();
    expect(requests().filter((r) => r.op === 'close')).toHaveLength(1);
  });

  it('cleans up failed or late native declarations', async () => {
    const session = await open('tcp/127.0.0.1:7447');
    mockCall.mockResolvedValueOnce(JSON.stringify({ ok: false, error: 'closed transport' }));
    await expect(session.subscribe('mower/A/telemetry', jest.fn())).rejects.toThrow(
      'closed transport'
    );
    expect(requests().at(-1).op).toBe('unsubscribe');
    let finish!: (result: string) => void;
    mockCall.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        })
    );
    const late = session.subscribeLiveliness('mower/A/liveliness', jest.fn());
    expect(requests().at(-1).kind).toBe('liveliness');
    await session.close();
    finish(JSON.stringify({ ok: true, result: null }));
    await expect(late).rejects.toThrow('closed');
    expect(requests().at(-1).op).toBe('unsubscribe');
  });

  it('preserves Unicode replies and sends the requested timeout', async () => {
    const session = await open('tls/example.test:7447');
    await expect(session.query('user/login', '{}', 250)).resolves.toBe('{"name":"草🌱"}');
    expect(requests().at(-1).timeout_ms).toBe(250);
    mockCall.mockResolvedValueOnce(JSON.stringify({ ok: false }));
    await expect(session.query('bad', '{}')).rejects.toThrow('Native Zenoh operation failed');
    await session.close();
  });
});

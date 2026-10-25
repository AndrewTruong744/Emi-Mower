/** Typed Android transport adapter. Account and authorization policy live in zenohClient. */
import Native, { type NativeSample } from '../../modules/emi-zenoh';

export type Sample = Pick<NativeSample, 'key' | 'payload' | 'put'>;
export type Cleanup = () => Promise<void>;
let nextSubscription = 1;

async function call<T>(request: object): Promise<T> {
  const response = JSON.parse(await Native.call(JSON.stringify(request))) as {
    ok: boolean;
    result: T;
    error?: string;
  };
  if (!response.ok) throw new Error(response.error || 'Native Zenoh operation failed');
  return response.result;
}

export class NativeSession {
  private closed = false;
  private callbacks = new Map<string, (sample: Sample) => void>();
  private listener;
  onTransport?: (connected: boolean) => void;

  constructor(private id: number) {
    this.listener = Native.addListener('sample', (event) => {
      if (this.closed) return;
      if (event.subscriptionId === `@transport:${id}`) this.onTransport?.(event.put);
      else this.callbacks.get(event.subscriptionId)?.(event);
    });
  }

  query(key: string, payload: string, timeoutMs = 5000): Promise<string> {
    return call({ op: 'query', session: this.id, key, payload, timeout_ms: timeoutMs });
  }

  put(key: string, payload: string): Promise<void> {
    return call({ op: 'put', session: this.id, key, payload });
  }

  restoreSubscriptions(): Promise<void> {
    return call({ op: 'restore_subscriptions', session: this.id });
  }

  subscribe(key: string, onSample: (sample: Sample) => void): Promise<Cleanup> {
    return this.declare(key, onSample, 'data');
  }

  subscribeLiveliness(key: string, onSample: (sample: Sample) => void): Promise<Cleanup> {
    return this.declare(key, onSample, 'liveliness');
  }

  private async declare(
    key: string,
    onSample: (sample: Sample) => void,
    kind: 'data' | 'liveliness'
  ): Promise<Cleanup> {
    if (this.closed) throw new Error('Zenoh session is closed');
    const id = `${this.id}:${nextSubscription++}`;
    this.callbacks.set(id, onSample);
    try {
      await call({ op: 'subscribe', session: this.id, key, subscription_id: id, kind });
      if (this.closed) throw new Error('Zenoh session is closed');
    } catch (error) {
      this.callbacks.delete(id);
      await call({ op: 'unsubscribe', subscription_id: id }).catch(() => {});
      throw error;
    }
    return async () => {
      if (this.callbacks.delete(id)) await call({ op: 'unsubscribe', subscription_id: id });
    };
  }

  async close(): Promise<void> {
    if (this.closed) return;
    this.closed = true;
    this.onTransport = undefined;
    this.listener.remove();
    this.callbacks.clear();
    await call({ op: 'close', session: this.id });
  }
}

export async function open(endpoint: string): Promise<NativeSession> {
  return new NativeSession(
    await call<number>({
      op: 'connect',
      endpoint,
      root_ca_pem: process.env.EXPO_PUBLIC_ZENOH_CA_PEM || null,
    })
  );
}

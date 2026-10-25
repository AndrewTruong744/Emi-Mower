import { open, type NativeSession, type Sample, type Cleanup } from '@/config/nativeZenoh';
import { reportAppError } from '@/errors/reporter';
import type { ErrorCode } from '@/errors/types';
import { isOperationCancelled, OperationCancelled } from '@/errors/operationCancelled';
import { useBoundStore } from '@/store/useBoundStore';
import { env } from './env';

const zenohQueryTimeoutMs = 5_000;
let sessionPromise: Promise<Connection> | null = null;
let sessionGeneration: number | null = null;
let closingPromise: Promise<void> | null = null;
const activeSubscriberCleanups = new Set<Cleanup>();

interface Connection {
  session: NativeSession;
  operation: ZenohOperation;
  closed: boolean;
  connected: boolean;
  revision: number;
  authorizedUntil: number;
  refresh?: () => Promise<unknown>;
  renewalTimer?: ReturnType<typeof setTimeout>;
  recovering?: Promise<void>;
}

/** Whether a captured Zenoh auth generation still owns the active session. */
export function isZenohOperationActive(generation: number): boolean {
  const state = useBoundStore.getState();
  return state.zenohEnabled && state.authGeneration === generation;
}

interface ZenohOperation {
  isActive: () => boolean;
  assertActive: () => void;
  waitFor: <T>(promise: Promise<T>) => Promise<T>;
}

function createZenohOperation(): ZenohOperation {
  const generation = useBoundStore.getState().authGeneration;
  const isActive = () => isZenohOperationActive(generation);
  const assertActive = () => {
    if (!isActive()) throw new OperationCancelled('Zenoh operation cancelled');
  };
  assertActive();
  return {
    isActive,
    assertActive,
    async waitFor<T>(promise: Promise<T>): Promise<T> {
      const result = await promise;
      assertActive();
      return result;
    },
  };
}

function isActive(connection: Connection): boolean {
  return !connection.closed && connection.operation.isActive();
}

/** Zenoh reconnects the transport; the app reauthorizes before Rust replays declarations. */
function transportChanged(connection: Connection, connected: boolean): void {
  if (!isActive(connection)) return;
  connection.connected = connected;
  connection.revision++;
  connection.authorizedUntil = 0;
  if (!connected || !connection.refresh || connection.recovering) return;
  connection.recovering = (async () => {
    // A second disconnect/reconnect during login invalidates that login's transport.
    while (isActive(connection) && connection.connected) {
      const revision = connection.revision;
      try {
        await connection.refresh!();
        if (!isActive(connection) || !connection.connected) return;
        if (revision !== connection.revision) continue;
        await connection.session.restoreSubscriptions();
      } catch (error) {
        if (isActive(connection) && connection.connected && revision !== connection.revision)
          continue;
        throw error;
      }
      if (revision === connection.revision) return;
    }
  })()
    .catch((error) => {
      connection.authorizedUntil = 0;
      if (isActive(connection)) reportAppError('zenoh.request_failed', error);
    })
    .finally(() => {
      connection.recovering = undefined;
    });
}

async function openConnection(operation: ZenohOperation): Promise<Connection> {
  const session = await open(env.zenohUrl);
  try {
    operation.assertActive();
    const connection: Connection = {
      session,
      operation,
      closed: false,
      connected: true,
      revision: 0,
      authorizedUntil: 0,
    };
    session.onTransport = (connected) => transportChanged(connection, connected);
    return connection;
  } catch (error) {
    await session.close().catch(() => {});
    throw error;
  }
}

async function getConnection(): Promise<Connection> {
  const operation = createZenohOperation();
  const generation = useBoundStore.getState().authGeneration;
  if (closingPromise) await operation.waitFor(closingPromise);
  if (sessionPromise && sessionGeneration !== generation) await operation.waitFor(closeZenoh());
  if (!sessionPromise) {
    const pending = openConnection(operation);
    sessionPromise = pending;
    sessionGeneration = generation;
    void pending.catch(() => {
      if (sessionPromise === pending) sessionPromise = null;
    });
  }
  return operation.waitFor(sessionPromise);
}

export async function connectZenoh(): Promise<NativeSession> {
  return (await getConnection()).session;
}

/** The app alone owns Firebase authorization, expiry and renewal. */
export async function maintainZenohAuthorization(
  seconds: number,
  refresh: () => Promise<unknown>
): Promise<void> {
  const connection = await getConnection();
  connection.refresh = refresh;
  connection.authorizedUntil = connection.connected ? Date.now() + seconds * 1000 : 0;
  if (connection.renewalTimer) clearTimeout(connection.renewalTimer);
  connection.renewalTimer = setTimeout(
    () => {
      if (isActive(connection))
        void refresh().catch(async (error) => {
          if (!isActive(connection)) return;
          reportAppError('zenoh.request_failed', error);
          await closeZenoh();
        });
    },
    Math.max(1, seconds * 0.8) * 1000
  );
  (connection.renewalTimer as unknown as { unref?: () => void }).unref?.();
}

export async function closeZenoh(): Promise<void> {
  if (closingPromise) return closingPromise;
  const pending = sessionPromise;
  sessionPromise = null;
  sessionGeneration = null;
  const closing = (async () => {
    const connection = await pending?.catch(() => undefined);
    if (connection) {
      connection.closed = true;
      connection.authorizedUntil = 0;
      if (connection.renewalTimer) clearTimeout(connection.renewalTimer);
    }
    await Promise.allSettled([...activeSubscriberCleanups].map((cleanup) => cleanup()));
    await connection?.session.close().catch(() => {});
  })();
  closingPromise = closing;
  try {
    await closing;
  } finally {
    if (closingPromise === closing) closingPromise = null;
  }
}

async function withConnection<T>(
  code: ErrorCode,
  work: (connection: Connection, operation: ZenohOperation) => Promise<T>
): Promise<T> {
  const operation = createZenohOperation();
  try {
    const connection = await operation.waitFor(getConnection());
    if (connection.closed) throw new OperationCancelled('Zenoh operation cancelled');
    const result = await operation.waitFor(work(connection, operation));
    if (connection.closed) throw new OperationCancelled('Zenoh operation cancelled');
    return result;
  } catch (error) {
    if (isOperationCancelled(error) || !operation.isActive())
      throw new OperationCancelled('Zenoh operation cancelled');
    reportAppError(code, error);
    throw error;
  }
}

export function zenohQuery<T>(key: string, payload: unknown): Promise<T> {
  return withConnection('zenoh.request_failed', async ({ session }) => {
    const text = await session.query(key, JSON.stringify(payload), zenohQueryTimeoutMs);
    if (!text) throw new Error(`Zenoh returned an empty response for ${key}`);
    return JSON.parse(text) as T;
  });
}

/** Publish a JSON command without waiting for a reply from the mower. */
export function zenohPut(key: string, payload: unknown): Promise<void> {
  return withConnection('zenoh.command_failed', async (connection) => {
    if (!connection.connected || connection.recovering || Date.now() >= connection.authorizedUntil)
      throw new Error('Zenoh transport is not authorized');
    await connection.session.put(key, JSON.stringify(payload));
  });
}

function trackSubscriber(unsubscribe: Cleanup, onClose?: () => void): Cleanup {
  let pending: Promise<void> | undefined;
  const cleanup = () => {
    pending ??= (async () => {
      try {
        onClose?.();
      } catch {
        /* Continue native cleanup. */
      }
      await unsubscribe().catch(() => {});
    })().finally(() => activeSubscriberCleanups.delete(cleanup));
    return pending;
  };
  activeSubscriberCleanups.add(cleanup);
  return cleanup;
}

function subscribe(
  key: string,
  onSample: (sample: Sample) => void,
  kind: 'data' | 'liveliness',
  onClose?: () => void
): Promise<void> {
  return withConnection('zenoh.subscription_failed', async (connection, operation) => {
    const handler = (sample: Sample) => {
      if (isActive(connection)) onSample(sample);
    };
    const unsubscribe = await (kind === 'data'
      ? connection.session.subscribe(key, handler)
      : connection.session.subscribeLiveliness(key, handler));
    const cleanup = trackSubscriber(unsubscribe, onClose);
    try {
      if (connection.closed) throw new OperationCancelled('Zenoh operation cancelled');
      operation.assertActive();
    } catch (error) {
      await cleanup();
      throw error;
    }
  });
}

export function zenohSubscribe(
  key: string,
  onPayload: (payload: string) => void,
  onClose?: () => void
): Promise<void> {
  return subscribe(key, (sample) => onPayload(sample.payload), 'data', onClose);
}

/** Rust declares historical liveliness subscribers and emits plain token changes. */
export function zenohSubscribeLiveliness(
  key: string,
  onChange: (key: string, connected: boolean) => void,
  onClose?: () => void
): Promise<void> {
  return subscribe(key, (sample) => onChange(sample.key, sample.put), 'liveliness', onClose);
}

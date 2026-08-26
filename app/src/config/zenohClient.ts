import {
  Config,
  Duration,
  Encoding,
  open,
  ReplyError,
  type Session,
} from '@eclipse-zenoh/zenoh-ts';
import { reportAppError } from '@/errors/reporter';
import { isOperationCancelled, OperationCancelled } from '@/errors/operationCancelled';
import { useBoundStore } from '@/store/useBoundStore';
import { env } from './env';

const zenohQueryTimeoutMs = 5_000;
const zenohLocator = env.zenohUrl;

let sessionPromise: Promise<Session> | null = null;
let sessionLocator: string | null = null;
const activeSubscriberCleanups = new Set<() => Promise<void>>();

function getZenohLifecycle(): { enabled: boolean; generation: number } {
  const { zenohEnabled, authGeneration } = useBoundStore.getState();
  return { enabled: zenohEnabled, generation: authGeneration };
}

/** Whether a captured Zenoh auth generation still owns the active session. */
export function isZenohOperationActive(operationGeneration: number): boolean {
  const { enabled, generation } = getZenohLifecycle();
  return enabled && generation === operationGeneration;
}

interface ZenohOperation {
  isActive: () => boolean;
  assertActive: () => void;
  waitFor: <T>(promise: Promise<T>) => Promise<T>;
}

/** Captures one auth generation for a finite Zenoh operation. */
function createZenohOperation(): ZenohOperation {
  const { generation } = getZenohLifecycle();
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

function trackSubscriber(
  subscriber: { undeclare(): Promise<void> },
  onClose?: () => void
): () => Promise<void> {
  let cleanupPromise: Promise<void> | undefined;
  const cleanup = () => {
    cleanupPromise ??= (async () => {
      try {
        onClose?.();
      } catch {
        // Local cleanup must not prevent the Zenoh declaration from closing.
      }
      try {
        await subscriber.undeclare();
      } catch {
        // Session shutdown can undeclare the subscriber before local cleanup.
      }
    })().finally(() => activeSubscriberCleanups.delete(cleanup));
    return cleanupPromise;
  };
  activeSubscriberCleanups.add(cleanup);
  return cleanup;
}

async function openZenohSession(locator: string, operation: ZenohOperation): Promise<Session> {
  const session = await open(new Config(locator, zenohQueryTimeoutMs));
  try {
    operation.assertActive();
    return session;
  } catch (error) {
    try {
      await session.close();
    } catch {
      // The connection is already invalidated; preserve the cancellation error.
    }
    throw error;
  }
}

async function clearFailedSession(pendingSession: Promise<Session>): Promise<void> {
  try {
    await pendingSession;
  } catch {
    if (sessionPromise === pendingSession) {
      sessionPromise = null;
      sessionLocator = null;
    }
  }
}

export async function connectZenoh(username?: string, password?: string): Promise<Session> {
  const hasCredentials = username !== undefined;
  if (hasCredentials !== (password !== undefined)) {
    throw new Error('Zenoh username and token must be provided together');
  }
  const operation = createZenohOperation();

  // A no-credential call reuses whichever session is active. This keeps all
  // post-login queries on the authenticated session established below.
  if (sessionPromise && !hasCredentials) {
    return operation.waitFor(sessionPromise);
  }

  let targetLocator = zenohLocator;
  if (hasCredentials) {
    const authenticatedUrl = new URL(zenohLocator);
    authenticatedUrl.username = username!;
    authenticatedUrl.password = password!;
    targetLocator = authenticatedUrl.toString();
  }

  if (sessionPromise && sessionLocator !== targetLocator) {
    await closeZenoh();
    operation.assertActive();
  }

  if (!sessionPromise) {
    sessionLocator = targetLocator;
    const pendingSession = openZenohSession(targetLocator, operation);
    sessionPromise = pendingSession;
    void clearFailedSession(pendingSession);
  }

  return operation.waitFor(sessionPromise!);
}

export async function closeZenoh(): Promise<void> {
  await Promise.allSettled([...activeSubscriberCleanups].map((cleanup) => cleanup()));

  const pendingSession = sessionPromise;
  sessionPromise = null;
  sessionLocator = null;

  try {
    await (await pendingSession)?.close();
  } catch {
    // A failed connection or closed transport must not block local logout.
  }
}

export async function zenohQuery<T>(keyExpr: string, payload: unknown): Promise<T> {
  const operation = createZenohOperation();
  try {
    const session = await operation.waitFor(connectZenoh());
    const receiver = await operation.waitFor(
      session.get(keyExpr, {
        encoding: Encoding.APPLICATION_JSON,
        payload: JSON.stringify(payload),
        timeout: Duration.milliseconds.of(zenohQueryTimeoutMs),
      })
    );

    if (!receiver) {
      throw new Error(`Zenoh returned no receiver for ${keyExpr}`);
    }

    for await (const reply of receiver) {
      operation.assertActive();
      const result = reply.result();
      if (result instanceof ReplyError) {
        throw new Error(result.payload().toString() || `Zenoh request failed: ${keyExpr}`);
      }

      const text = result.payload().toString();
      if (!text) {
        throw new Error(`Zenoh returned an empty response for ${keyExpr}`);
      }

      return JSON.parse(text) as T;
    }

    throw new Error(`Zenoh returned no response for ${keyExpr}`);
  } catch (error) {
    if (isOperationCancelled(error) || !operation.isActive()) {
      throw new OperationCancelled('Zenoh operation cancelled');
    }
    reportAppError('zenoh.request_failed', error);
    throw error;
  }
}

/** Publish a JSON command without waiting for a reply from the mower. */
export async function zenohPut(keyExpr: string, payload: unknown): Promise<void> {
  const operation = createZenohOperation();
  try {
    const session = await operation.waitFor(connectZenoh());

    await operation.waitFor(
      session.put(keyExpr, JSON.stringify(payload), {
        encoding: Encoding.APPLICATION_JSON,
      })
    );
  } catch (error) {
    if (isOperationCancelled(error) || !operation.isActive()) {
      throw new OperationCancelled('Zenoh operation cancelled');
    }
    reportAppError('zenoh.command_failed', error);
    throw error;
  }
}

/** Declare a JSON subscriber; closeZenoh owns its registered cleanup. */
export async function zenohSubscribe(
  keyExpr: string,
  onPayload: (payload: string) => void,
  onClose?: () => void
): Promise<void> {
  const operation = createZenohOperation();
  try {
    const session = await operation.waitFor(connectZenoh());
    const subscriber = await session.declareSubscriber(keyExpr, {
      handler: (sample) => {
        if (operation.isActive()) {
          onPayload(sample.payload().toString());
        }
      },
    });

    const cleanup = trackSubscriber(subscriber, onClose);
    try {
      operation.assertActive();
    } catch (error) {
      await cleanup();
      throw error;
    }
  } catch (error) {
    if (isOperationCancelled(error) || !operation.isActive()) {
      throw new OperationCancelled('Zenoh operation cancelled');
    }
    reportAppError('zenoh.subscription_failed', error);
    throw error;
  }
}

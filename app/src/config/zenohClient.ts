import type { Session } from '@eclipse-zenoh/zenoh-ts';
import { Platform } from 'react-native';
import { useBoundStore } from '@/store/useBoundStore';
import { loadZenoh } from './runtime';

const defaultZenohHost = Platform.OS === 'android' ? '10.0.2.2' : '127.0.0.1';
const configuredZenohHost =
  process.env.EXPO_PUBLIC_ZENOH_HOST?.replace(/^['"]|['"]$/g, '') || defaultZenohHost;
const configuredZenohPort =
  process.env.EXPO_PUBLIC_ZENOH_PORT?.replace(/^['"]|['"]$/g, '') || '10000';
const zenohQueryTimeoutMs = 5_000;

const zenohLocator =
  process.env.EXPO_PUBLIC_ZENOH_URL?.replace(/^['"]|['"]$/g, '') ||
  `ws://${configuredZenohHost}:${configuredZenohPort}`;

let sessionPromise: Promise<Session> | null = null;
let sessionLocator: string | null = null;
let zenohSessionVersion = 0;

export class ZenohOperationCancelled extends Error {
  constructor() {
    super('Zenoh operation cancelled');
    this.name = 'ZenohOperationCancelled';
  }
}

export function cancelZenohOperations(): void {
  zenohSessionVersion += 1;
}

export function isZenohOperationCancelled(error: unknown): boolean {
  return error instanceof ZenohOperationCancelled;
}

function getAuthenticatedLocator(username: string, password: string): string {
  const schemeSeparator = zenohLocator.indexOf('://');
  if (schemeSeparator < 0) {
    throw new Error('Zenoh locator must include a URL scheme before authenticating');
  }

  const scheme = zenohLocator.slice(0, schemeSeparator + 3);
  const authorityAndPath = zenohLocator.slice(schemeSeparator + 3);
  return `${scheme}${encodeURIComponent(username)}:${encodeURIComponent(password)}@${authorityAndPath}`;
}

export function getZenohLocator(): string {
  return zenohLocator;
}

export async function connectZenoh(
  username?: string,
  password?: string,
  assertCurrent?: () => void
): Promise<Session> {
  if ((username === undefined) !== (password === undefined)) {
    throw new Error('Zenoh username and token must be provided together');
  }
  assertCurrent?.();

  // A no-credential call reuses whichever session is active. This keeps all
  // post-login queries on the authenticated session established below.
  if (sessionPromise && username === undefined) {
    return sessionPromise;
  }

  const targetLocator =
    username === undefined ? zenohLocator : getAuthenticatedLocator(username, password!);

  if (sessionPromise && sessionLocator !== targetLocator) {
    await closeZenoh();
    assertCurrent?.();
  }

  if (!sessionPromise) {
    const operationVersion = zenohSessionVersion;
    sessionLocator = targetLocator;
    const pendingSession = loadZenoh()
      .then(async ({ Config, open }) => {
        const session = await open(new Config(targetLocator, zenohQueryTimeoutMs));
        try {
          assertCurrent?.();
          if (operationVersion !== zenohSessionVersion) {
            throw new ZenohOperationCancelled();
          }
        } catch (error) {
          await session.close();
          throw error;
        }
        return session;
      })
      .catch((error) => {
        if (sessionPromise === pendingSession) {
          sessionPromise = null;
          sessionLocator = null;
        }
        throw error;
      });
    sessionPromise = pendingSession;
  }

  return sessionPromise;
}

export async function closeZenoh(): Promise<void> {
  const pendingSession = sessionPromise;
  sessionPromise = null;
  sessionLocator = null;

  let session: Session | null = null;
  try {
    session = pendingSession ? await pendingSession : null;
  } catch {
    // A cancelled connection attempt has no session to close.
  }
  try {
    await session?.close();
  } catch {
    // Logout must still clear local auth state if the transport is already down.
  }
}

export async function zenohQuery<T>(keyExpr: string, payload: unknown): Promise<T> {
  const operationVersion = zenohSessionVersion;
  try {
    const { Duration, Encoding, ReplyError } = await loadZenoh();
    const session = await connectZenoh();
    if (operationVersion !== zenohSessionVersion) {
      throw new ZenohOperationCancelled();
    }
    const receiver = await session.get(keyExpr, {
      encoding: Encoding.APPLICATION_JSON,
      payload: JSON.stringify(payload),
      timeout: Duration.milliseconds.of(zenohQueryTimeoutMs),
    });

    if (operationVersion !== zenohSessionVersion) {
      throw new ZenohOperationCancelled();
    }

    if (!receiver) {
      throw new Error(`Zenoh returned no receiver for ${keyExpr}`);
    }

    for await (const reply of receiver) {
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
    if (isZenohOperationCancelled(error) || operationVersion !== zenohSessionVersion) {
      throw new ZenohOperationCancelled();
    }
    useBoundStore.getState().reportError(error, {
      source: 'zenoh',
      title: 'Zenoh request failed',
    });
    throw error;
  }
}

/** Publish a JSON command without waiting for a reply from the mower. */
export async function zenohPut(keyExpr: string, payload: unknown): Promise<void> {
  const operationVersion = zenohSessionVersion;
  try {
    const { Encoding } = await loadZenoh();
    const session = await connectZenoh();
    if (operationVersion !== zenohSessionVersion) {
      throw new ZenohOperationCancelled();
    }

    await session.put(keyExpr, JSON.stringify(payload), {
      encoding: Encoding.APPLICATION_JSON,
    });

    if (operationVersion !== zenohSessionVersion) {
      throw new ZenohOperationCancelled();
    }
  } catch (error) {
    if (isZenohOperationCancelled(error) || operationVersion !== zenohSessionVersion) {
      throw new ZenohOperationCancelled();
    }
    useBoundStore.getState().reportError(error, {
      source: 'zenoh',
      title: 'Zenoh command failed',
    });
    throw error;
  }
}

/** Declare a JSON subscriber on the authenticated shared Zenoh session. */
export async function zenohSubscribe(
  keyExpr: string,
  onPayload: (payload: string) => void
): Promise<() => Promise<void>> {
  const operationVersion = zenohSessionVersion;
  try {
    const session = await connectZenoh();
    if (operationVersion !== zenohSessionVersion) throw new ZenohOperationCancelled();

    const subscriber = await session.declareSubscriber(keyExpr, {
      handler: (sample) => onPayload(sample.payload().toString()),
    });

    return async () => {
      try {
        await subscriber.undeclare();
      } catch {
        // Session shutdown can undeclare the subscriber before React cleanup.
      }
    };
  } catch (error) {
    if (isZenohOperationCancelled(error) || operationVersion !== zenohSessionVersion) {
      throw new ZenohOperationCancelled();
    }
    useBoundStore.getState().reportError(error, {
      source: 'zenoh',
      title: 'Zenoh telemetry subscription failed',
    });
    throw error;
  }
}

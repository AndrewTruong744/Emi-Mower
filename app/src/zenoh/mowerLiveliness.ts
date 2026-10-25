import { isZenohOperationActive, zenohSubscribeLiveliness } from '@/config/zenohClient';
import { mowerLivelinessPath } from '@/generated/zenohPaths';
import { useBoundStore } from '@/store/useBoundStore';

const routePrefix = 'mower/';
const routeSuffix = '/liveliness';

/** Return the mower ID only for the exact liveliness route shape. */
export function mowerIdFromLivelinessKey(keyExpr: string): string | null {
  if (!keyExpr.startsWith(routePrefix) || !keyExpr.endsWith(routeSuffix)) return null;
  const mowerId = keyExpr.slice(routePrefix.length, -routeSuffix.length);
  return mowerId && !mowerId.includes('/') ? mowerId : null;
}

/**
 * Observe Zenoh gateway-session tokens for the signed-in user's mowers.
 * This reports connectivity to Zenoh only; it is not a health, safety, or
 * telemetry-freshness signal.
 */
let activeGeneration: number | undefined;
const activeSubscriptions = new Map<string, Promise<void>>();

export function initializeMowerLivelinessSubscription(authGeneration: number): Promise<void> {
  if (activeGeneration !== authGeneration) {
    activeSubscriptions.clear();
    activeGeneration = authGeneration;
  }
  // Router ACLs grant exact owned keys. A wildcard declaration can be denied
  // even when every token it would currently match belongs to this user.
  return Promise.all(useBoundStore.getState().mowers.map((mowerId) => {
    const existing = activeSubscriptions.get(mowerId);
    if (existing) return existing;
    const clear = () => {
      if (activeSubscriptions.get(mowerId) === promise) activeSubscriptions.delete(mowerId);
    };
    const promise = subscribe(authGeneration, mowerId, clear).catch((error) => {
      clear();
      throw error;
    });
    activeSubscriptions.set(mowerId, promise);
    return promise;
  })).then(() => undefined);
}

async function subscribe(authGeneration: number, mowerId: string, onClose: () => void): Promise<void> {
  await zenohSubscribeLiveliness(
    mowerLivelinessPath(mowerId),
    (keyExpr, connected) => {
      if (!isZenohOperationActive(authGeneration)) return;

      const mowerId = mowerIdFromLivelinessKey(keyExpr);
      if (!mowerId || !useBoundStore.getState().mowers.includes(mowerId)) return;
      useBoundStore
        .getState()
        .setMowerConnection(mowerId, connected ? 'connected' : 'disconnected');
    },
    onClose
  );
}

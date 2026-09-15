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
export async function initializeMowerLivelinessSubscription(authGeneration: number): Promise<void> {
  if (useBoundStore.getState().mowers.length === 0) return;

  await zenohSubscribeLiveliness(mowerLivelinessPath('*'), (keyExpr, connected) => {
    if (!isZenohOperationActive(authGeneration)) return;

    const mowerId = mowerIdFromLivelinessKey(keyExpr);
    if (!mowerId || !useBoundStore.getState().mowers.includes(mowerId)) return;
    useBoundStore.getState().setMowerConnection(
      mowerId,
      connected ? 'connected' : 'disconnected'
    );
  });
}

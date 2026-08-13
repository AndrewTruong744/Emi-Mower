import { useEffect } from 'react';
import { MOWER_TELEMETRY_INTERVAL_MS } from '@/store/slices/mowerSlice';
import { useBoundStore } from '@/store/useBoundStore';

/** Temporary session position feed; replace with live mower position subscriptions. */
export function useMowerPositionSimulator() {
  const isSessionActive = useBoundStore((state) => state.isSessionActive);
  const isSessionPaused = useBoundStore((state) => state.isSessionPaused);
  const advanceFakeMowerPositions = useBoundStore((state) => state.advanceFakeMowerPositions);

  useEffect(() => {
    if (!isSessionActive || isSessionPaused) return;

    const interval = setInterval(advanceFakeMowerPositions, MOWER_TELEMETRY_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [advanceFakeMowerPositions, isSessionActive, isSessionPaused]);
}

import { useEffect, useState } from 'react';
import type { LiveKitTokenResponse } from '@/generated/zenoh';
import { useLiveKitConsume } from '@/hooks/api/mower/useLiveKitConsume';

/** Owns the selected mower's short-lived LiveKit viewer credential. */
export function useLivestream(mowerId: string | null) {
  const [credentials, setCredentials] = useState<LiveKitTokenResponse | null>(null);
  const streamCredentials = useLiveKitConsume();

  useEffect(() => {
    setCredentials(null);
    streamCredentials.reset();
  }, [mowerId]);

  const connect = async () => {
    if (!mowerId) return;
    try {
      setCredentials(await streamCredentials.mutateAsync(mowerId));
    } catch {
      // The global error host reports the failed connection; keep this panel disconnected.
    }
  };

  const disconnect = () => {
    setCredentials(null);
    streamCredentials.reset();
  };

  return {
    connect,
    disconnect,
    isConnected: credentials !== null,
    isPending: streamCredentials.isPending,
  };
}

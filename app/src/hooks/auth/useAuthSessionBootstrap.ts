import { useEffect } from 'react';
import { onAuthStateChanged } from '@react-native-firebase/auth';
import { firebaseAuth } from '@/config/firebase';
import { clearAuthenticatedQueryCache } from '@/config/queryClient';
import { closeZenoh, isZenohOperationActive } from '@/config/zenohClient';
import { isOperationCancelled } from '@/errors/operationCancelled';
import { reportAppError } from '@/errors/reporter';
import { useBoundStore } from '@/store/useBoundStore';
import { loginUser } from '@/zenoh/UserLogin';
import { initializeMowerTelemetrySubscription } from '@/zenoh/mowerTelemetry';

/** Keep Firebase identity, the Zenoh session, and user-scoped app state in sync. */
export function useAuthSessionBootstrap(): void {
  const setUser = useBoundStore((state) => state.setUser);
  const setMowers = useBoundStore((state) => state.setMowers);
  const setAuthStatus = useBoundStore((state) => state.setAuthStatus);
  const startZenohSession = useBoundStore((state) => state.startZenohSession);
  const resetStore = useBoundStore((state) => state.resetStore);

  useEffect(() => {
    let unsubscribe: (() => void) | undefined;
    setAuthStatus('initializing');
    try {
      unsubscribe = onAuthStateChanged(firebaseAuth, async (firebaseUser) => {
        if (!firebaseUser) {
          clearAuthenticatedQueryCache();

          // Explicit logout owns this barrier so login is not exposed until
          // every subscriber and the previous session have been torn down.
          if (useBoundStore.getState().authStatus === 'signingOut') return;

          setAuthStatus('signingOut');
          await closeZenoh();
          resetStore();
          return;
        }

        // A restored or different Firebase identity must never receive the
        // previous session's server data or mutation state.
        clearAuthenticatedQueryCache();
        startZenohSession();
        const authGeneration = useBoundStore.getState().authGeneration;
        setAuthStatus('authenticating');
        try {
          const userData = await loginUser();
          if (!isZenohOperationActive(authGeneration)) return;
          setUser({
            user_id: userData.id,
            email: userData.email,
            displayName: userData.name,
          });
          setMowers(userData.mowers);
          await initializeMowerTelemetrySubscription(authGeneration);
          if (!isZenohOperationActive(authGeneration)) return;
          setAuthStatus('authenticated');
        } catch (error) {
          if (!isZenohOperationActive(authGeneration) || isOperationCancelled(error)) {
            return;
          }
          console.error('Error establishing authenticated Zenoh session:', error);
          await closeZenoh();
          resetStore();
          reportAppError('auth.sign_in_failed', error);
        }
      });
    } catch (error) {
      console.error('Firebase Auth is not initialized or failed to start:', error);
      reportAppError('auth.session_failed', error);
      setAuthStatus('signedOut');
    }

    return () => {
      unsubscribe?.();
    };
  }, [setUser, setMowers, setAuthStatus, startZenohSession, resetStore]);
}

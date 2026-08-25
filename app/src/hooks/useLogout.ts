import { GoogleSignin } from '@react-native-google-signin/google-signin';
import { signOut as signOutFromFirebase } from '@react-native-firebase/auth';
import { useState } from 'react';
import { firebaseAuth } from '@/config/firebase';
import { closeZenoh } from '@/config/zenohClient';
import { reportAppError } from '@/errors/reporter';
import { useBoundStore } from '@/store/useBoundStore';
import { clearAuthenticatedQueryCache } from '@/config/queryClient';

export const useLogout = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const setAuthStatus = useBoundStore((state) => state.setAuthStatus);
  const disableZenoh = useBoundStore((state) => state.disableZenoh);
  const enableZenoh = useBoundStore((state) => state.enableZenoh);
  const resetStore = useBoundStore((state) => state.resetStore);

  const logout = async () => {
    setIsLoading(true);
    setError(null);

    // Invalidate Zenoh work before Firebase emits its signed-out auth state.
    setAuthStatus('signingOut');
    disableZenoh();
    clearAuthenticatedQueryCache();

    // Google is an identity-provider session only. Its failure must not prevent
    // the Firebase sign-out that controls access to the application.
    void GoogleSignin.signOut().catch((googleSignOutError) => {
      console.error('Google Sign Out Error:', googleSignOutError);
      reportAppError('auth.sign_out_failed', googleSignOutError);
    });

    try {
      await signOutFromFirebase(firebaseAuth);

      // Do not expose login until every old-session subscription is undeclared
      // and the underlying Zenoh session is closed.
      await closeZenoh();
      resetStore();
    } catch (signOutError) {
      console.error('Firebase Sign Out Error:', signOutError);
      const message =
        signOutError instanceof Error ? signOutError.message : 'An error occurred during sign out';
      setError(message);
      reportAppError('auth.sign_out_failed', signOutError);

      // Firebase still has a user, so keep the authenticated route available
      // and restore the Zenoh lifecycle that was paused for logout.
      if (firebaseAuth.currentUser) {
        enableZenoh();
        setAuthStatus('authenticated');
      } else {
        await closeZenoh();
        resetStore();
      }
    } finally {
      setIsLoading(false);
    }
  };

  return {
    logout,
    isLoading,
    error,
  };
};

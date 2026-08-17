import { useRouter } from 'expo-router';
import { useGoogleAuth } from './useGoogleAuth';
import { loginUserAndStore } from '@/zenoh/UserLogin';
import { useBoundStore } from '@/store/useBoundStore';
import { isAuthOperationCancelled } from '@/auth/session';
import { isZenohOperationCancelled } from '@/config/zenohClient';

export const useLogin = () => {
  const router = useRouter();
  const { signInWithGoogle, isLoading } = useGoogleAuth();
  const setUser = useBoundStore((state) => state.setUser);
  const setMowers = useBoundStore((state) => state.setMowers);
  const clearError = useBoundStore((state) => state.clearError);
  const reportError = useBoundStore((state) => state.reportError);

  const handleGoogleLogin = async () => {
    try {
      clearError();
      const firebaseUser = await signInWithGoogle();
      const idToken = await firebaseUser.getIdToken(true);
      await loginUserAndStore(idToken, setUser, setMowers);
      // On success, navigate to the Home tab.
      router.replace('/(tabs)/home' as any);
    } catch (err: any) {
      if (isAuthOperationCancelled(err) || isZenohOperationCancelled(err)) return;
      console.error('Login screen sign-in failure:', err);
      reportError(err, { source: 'auth', title: 'Sign-in failed' });
    }
  };

  return {
    handleGoogleLogin,
    isLoading,
  };
};

import { useGoogleAuth } from './useGoogleAuth';
import { useBoundStore } from '@/store/useBoundStore';
import { isOperationCancelled } from '@/errors/operationCancelled';
import { reportAppError } from '@/errors/reporter';
import { clearAuthenticatedQueryCache } from '@/config/queryClient';

export const useLogin = () => {
  const { signInWithGoogle, isLoading } = useGoogleAuth();
  const clearErrors = useBoundStore((state) => state.clearErrors);

  const handleGoogleLogin = async () => {
    try {
      clearAuthenticatedQueryCache();
      clearErrors();
      await signInWithGoogle();
      // The Firebase auth-state listener handles Zenoh login and routing.
    } catch (err: any) {
      if (isOperationCancelled(err)) return;
      console.error('Login screen sign-in failure:', err);
      reportAppError('auth.sign_in_failed', err);
    }
  };

  return {
    handleGoogleLogin,
    isLoading,
  };
};

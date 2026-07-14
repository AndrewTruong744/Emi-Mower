import { useState } from 'react';
import { useRouter } from 'expo-router';
import { useGoogleAuth } from './useGoogleAuth';

export const useLogin = () => {
  const router = useRouter();
  const { signInWithGoogle, isLoading } = useGoogleAuth();

  const [errorVisible, setErrorVisible] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleGoogleLogin = async () => {
    try {
      setErrorVisible(false);
      setErrorMessage(null);
      await signInWithGoogle();
      // On success, navigate to the tabs layout (specifically the default index screen)
      router.replace('/(tabs)');
    } catch (err: any) {
      console.error('Login screen sign-in failure:', err);
      setErrorMessage(err?.message || 'Failed to sign in with Google. Please try again.');
      setErrorVisible(true);
    }
  };

  const dismissError = () => {
    setErrorVisible(false);
  };

  return {
    handleGoogleLogin,
    isLoading,
    errorVisible,
    errorMessage,
    dismissError,
  };
};

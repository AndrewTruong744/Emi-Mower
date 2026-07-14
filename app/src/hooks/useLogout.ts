import { useGoogleAuth } from './useGoogleAuth';

export const useLogout = () => {
  const { signOut, isLoading, error } = useGoogleAuth();

  return {
    logout: signOut,
    isLoading,
    error,
  };
};

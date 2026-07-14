import { GoogleSignin } from '@react-native-google-signin/google-signin';
import { auth } from '@/config/firebase';
import { useState } from 'react';

export const useChangeEmail = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const triggerChangeEmail = async () => {
    setIsLoading(true);
    setError(null);
    try {
      await GoogleSignin.hasPlayServices({ showPlayServicesUpdateDialog: true });
      const signInResult = await GoogleSignin.signIn();
      if (signInResult.type !== 'success') {
        throw new Error('Google Sign-In was cancelled or failed.');
      }

      const { serverAuthCode } = signInResult.data;
      const { idToken, accessToken } = await GoogleSignin.getTokens();

      if (!idToken || !accessToken) {
        throw new Error('Could not retrieve tokens from Google.');
      }

      const googleCredential = auth.GoogleAuthProvider.credential(idToken, accessToken);
      const userCredential = await auth().signInWithCredential(googleCredential);
      const firebaseIdToken = await userCredential.user.getIdToken();
      const refreshToken = serverAuthCode || 'firebase-handled';

      return {
        idToken: firebaseIdToken,
        refreshToken,
        email: userCredential.user.email,
      };
    } catch (err: any) {
      console.error('Change Email Google Auth Error:', err);
      const errMsg = err.message || 'Failed to authenticate with Google';
      setError(errMsg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  return {
    triggerChangeEmail,
    isLoading,
    error,
  };
};

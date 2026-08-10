import { GoogleSignin } from '@react-native-google-signin/google-signin';
import nativeAuth, { getIdToken, signInWithCredential } from '@react-native-firebase/auth';
import { firebaseAuth } from '@/config/firebase';
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

      const { idToken, accessToken } = await GoogleSignin.getTokens();

      if (!idToken || !accessToken) {
        throw new Error('Could not retrieve tokens from Google.');
      }

      const googleCredential = nativeAuth.GoogleAuthProvider.credential(
        idToken,
        accessToken
      ) as unknown as Parameters<typeof signInWithCredential>[1];
      const userCredential = await signInWithCredential(firebaseAuth, googleCredential);
      const firebaseIdToken = await getIdToken(userCredential.user);
      return {
        idToken: firebaseIdToken,
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

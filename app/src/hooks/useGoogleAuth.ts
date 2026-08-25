import { GoogleSignin } from '@react-native-google-signin/google-signin';
import nativeAuth, { signInWithCredential } from '@react-native-firebase/auth';
import { env } from '@/config/env';
import { firebaseAuth } from '@/config/firebase';
import { useState } from 'react';

// Configure Google Sign-In using the OAuth client ID from the environment.
GoogleSignin.configure({
  webClientId: env.googleWebClientId,
  offlineAccess: true,
});

export const useGoogleAuth = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const signInWithGoogle = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Ensure Play Services are available (Android only)
      await GoogleSignin.hasPlayServices({ showPlayServicesUpdateDialog: true });

      // Perform Google Sign-In
      const signInResult = await GoogleSignin.signIn();
      if (signInResult.type !== 'success') {
        throw new Error('Google Sign-In was cancelled or failed.');
      }

      // Get the tokens containing both idToken and accessToken from Google Sign-In
      const { idToken, accessToken } = await GoogleSignin.getTokens();
      if (!idToken) {
        throw new Error('No ID Token received from Google Sign-In.');
      }
      if (!accessToken) {
        throw new Error('No Access Token received from Google Sign-In.');
      }

      // Authenticate with Firebase using both Google ID and Access tokens
      const googleCredential = nativeAuth.GoogleAuthProvider.credential(
        idToken,
        accessToken
      ) as unknown as Parameters<typeof signInWithCredential>[1];
      const userCredential = await signInWithCredential(firebaseAuth, googleCredential);
      // The Firebase auth-state listener completes Zenoh login and publishes
      // authenticated app state only after both steps have succeeded.
      return userCredential.user;
    } catch (err: any) {
      console.error('Google Sign-In Error:', err);
      const errMsg = err.message || 'An error occurred during Google Sign-In';
      setError(errMsg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  return {
    signInWithGoogle,
    isLoading,
    error,
  };
};

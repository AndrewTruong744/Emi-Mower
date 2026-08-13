import { GoogleSignin } from '@react-native-google-signin/google-signin';
import nativeAuth, {
  getIdToken,
  signInWithCredential,
  signOut as signOutFromFirebase,
} from '@react-native-firebase/auth';
import { firebaseAuth } from '@/config/firebase';
import { useBoundStore } from '@/store/useBoundStore';
import { invalidateAuthSession } from '@/auth/session';
import { cancelZenohOperations, closeZenoh } from '@/config/zenohClient';
import { useState } from 'react';

// Configure Google Sign-In using the OAuth client ID from the environment.
const webClientId = process.env.EXPO_PUBLIC_WEB_CLIENT_ID;
if (webClientId) {
  GoogleSignin.configure({
    webClientId,
    offlineAccess: true,
  });
} else {
  console.warn('EXPO_PUBLIC_WEB_CLIENT_ID is not defined in the environment variables');
}

// Simple base64 decoding helper for JWT tokens
function decodeBase64(input: string): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
  const lookup = new Uint8Array(256);
  for (let i = 0; i < chars.length; i++) {
    lookup[chars.charCodeAt(i)] = i;
  }

  const cleanInput = input.replace(/=+$/, '');
  const len = cleanInput.length;
  const bufferLength = len * 0.75;
  const bytes = new Uint8Array(Math.floor(bufferLength));

  let p = 0;
  for (let i = 0; i < len; i += 4) {
    const encoded1 = lookup[cleanInput.charCodeAt(i)];
    const encoded2 = lookup[cleanInput.charCodeAt(i + 1)];
    const encoded3 = i + 2 < len ? lookup[cleanInput.charCodeAt(i + 2)] : 0;
    const encoded4 = i + 3 < len ? lookup[cleanInput.charCodeAt(i + 3)] : 0;

    bytes[p++] = (encoded1 << 2) | (encoded2 >> 4);
    if (p < bytes.length) {
      bytes[p++] = ((encoded2 & 15) << 4) | (encoded3 >> 2);
    }
    if (p < bytes.length) {
      bytes[p++] = ((encoded3 & 3) << 6) | (encoded4 & 63);
    }
  }

  let out = '';
  for (let j = 0; j < bytes.length; j++) {
    out += String.fromCharCode(bytes[j]);
  }
  return out;
}

// JWT decoder helper
function decodeJwt(token: string) {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const base64Url = parts[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const decoded = typeof atob === 'function' ? atob(base64) : decodeBase64(base64);
    return JSON.parse(decoded);
  } catch (error) {
    console.error('Failed to decode JWT:', error);
    return null;
  }
}

export const useGoogleAuth = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setAuthToken = useBoundStore((state) => state.setAuthToken);
  const setUser = useBoundStore((state) => state.setUser);
  const resetStore = useBoundStore((state) => state.resetStore);
  const reportError = useBoundStore((state) => state.reportError);

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

      // Get the ID token from Firebase
      const firebaseIdToken = await getIdToken(userCredential.user);

      // Decode the Firebase ID Token to get user information
      const decodedClaims = decodeJwt(firebaseIdToken);
      const user_id = decodedClaims?.sub || userCredential.user.uid;
      const email = decodedClaims?.email || userCredential.user.email;
      const displayName = decodedClaims?.name || userCredential.user.displayName;

      setAuthToken(firebaseIdToken);
      setUser({
        user_id,
        email,
        displayName,
      });

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

  const signOut = async () => {
    setIsLoading(true);
    setError(null);
    invalidateAuthSession();
    cancelZenohOperations();

    let signOutError: unknown = null;
    try {
      await GoogleSignin.signOut();
    } catch (err: any) {
      console.error('Sign Out Error:', err);
      signOutError = err;
    }

    try {
      await signOutFromFirebase(firebaseAuth);
    } catch (err: any) {
      console.error('Sign Out Error:', err);
      signOutError ??= err;
    }

    try {
      await closeZenoh();
    } catch (err: any) {
      console.error('Zenoh close error:', err);
      signOutError ??= err;
    }

    resetStore();
    if (signOutError) {
      const message = signOutError instanceof Error ? signOutError.message : 'An error occurred during sign out';
      setError(message);
      reportError(signOutError, { source: 'auth', title: 'Sign-out failed' });
    }
    setIsLoading(false);
  };

  return {
    signInWithGoogle,
    signOut,
    isLoading,
    error,
  };
};

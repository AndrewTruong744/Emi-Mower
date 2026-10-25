import { GoogleSignin } from '@react-native-google-signin/google-signin';
import { deleteApp, initializeApp } from '@react-native-firebase/app';
import nativeAuth, {
  getIdToken,
  signInWithCredential,
  signOut,
  type Auth,
} from '@react-native-firebase/auth';
import { firebaseApp, firebaseAuth } from '@/config/firebase';
import { useState } from 'react';

/** Verify the destination without changing the active Firebase/Zenoh identity. */
export const useChangeEmail = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const triggerChangeEmail = async () => {
    setIsLoading(true);
    setError(null);
    const originalUser = firebaseAuth.currentUser;
    let secondary: Awaited<ReturnType<typeof initializeApp>> | undefined;
    let secondaryAuth: Auth | undefined;
    const cleanup = async () => {
      if (secondaryAuth) await signOut(secondaryAuth).catch(() => undefined);
      if (secondary) await deleteApp(secondary).catch(() => undefined);
      secondary = undefined;
      secondaryAuth = undefined;
    };
    try {
      if (!originalUser) throw new Error('No authenticated Firebase user found');
      const originalIdToken = await getIdToken(originalUser, true);
      // RNFirebase requires strings for these optional services when creating
      // a named app. Android accepts empty values; no Realtime Database is used.
      secondary = await initializeApp(
        {
          ...firebaseApp.options,
          databaseURL: firebaseApp.options.databaseURL ?? '',
          storageBucket: firebaseApp.options.storageBucket ?? '',
          messagingSenderId: firebaseApp.options.messagingSenderId ?? '',
        },
        {
          name: `account-switch-${Date.now()}`,
          automaticDataCollectionEnabled: false,
        }
      );
      secondaryAuth = nativeAuth(secondary) as unknown as Auth;
      await GoogleSignin.hasPlayServices({ showPlayServicesUpdateDialog: true });
      // Clear Google's saved selection so signIn opens the account chooser.
      // Firebase and the current Zenoh connection remain signed in throughout.
      await GoogleSignin.signOut();
      const result = await GoogleSignin.signIn();
      if (result.type !== 'success') throw new Error('Google Sign-In was cancelled or failed.');
      const { idToken, accessToken } = await GoogleSignin.getTokens();
      if (!idToken || !accessToken) throw new Error('Could not retrieve tokens from Google.');
      const credential = nativeAuth.GoogleAuthProvider.credential(
        idToken,
        accessToken
      ) as unknown as Parameters<typeof signInWithCredential>[1];
      const { user } = await signInWithCredential(secondaryAuth, credential);
      if (user.uid === originalUser.uid)
        throw new Error('Choose a different Google account to switch your login.');
      if (!user.email) throw new Error('The selected Google account has no email address.');
      const newIdToken = await getIdToken(user, true);
      return {
        originalIdToken,
        idToken: newIdToken,
        email: user.email,
        userId: user.uid,
        cleanup,
        complete: async () => {
          if (firebaseAuth.currentUser?.uid !== originalUser.uid)
            throw new Error('Your signed-in account changed. Try again.');
          await signInWithCredential(firebaseAuth, credential);
        },
      };
    } catch (err) {
      await cleanup();
      const message = err instanceof Error ? err.message : 'Failed to authenticate with Google';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };
  return { triggerChangeEmail, isLoading, error };
};

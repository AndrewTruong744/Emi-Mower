import { getApp } from '@react-native-firebase/app';
import nativeAuth, { type Auth } from '@react-native-firebase/auth';

export const firebaseApp = getApp();
// Use the native auth singleton for Android/iOS. RNFirebase's modular getAuth(app)
// delegates through app.auth(), which can be unavailable while the native module
// is being registered in an Expo dev-client bundle.
export const firebaseAuth = nativeAuth() as unknown as Auth;

/** Return Firebase's current ID token, refreshing it when requested. */
export async function getFirebaseIdToken(forceRefresh = false): Promise<string> {
  const user = firebaseAuth.currentUser;
  if (!user) {
    throw new Error('No authenticated Firebase user found');
  }

  return user.getIdToken(forceRefresh);
}

export default firebaseApp;

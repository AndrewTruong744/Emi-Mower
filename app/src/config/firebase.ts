import { getApp } from '@react-native-firebase/app';
import nativeAuth, { type Auth } from '@react-native-firebase/auth';

export const firebaseApp = getApp();
// Use the native auth singleton for Android/iOS. RNFirebase's modular getAuth(app)
// delegates through app.auth(), which can be unavailable while the native module
// is being registered in an Expo dev-client bundle.
export const firebaseAuth = nativeAuth() as unknown as Auth;

// Keep this named export for callers from older bundles while all current code uses
// firebaseAuth directly.
export const auth = nativeAuth;
export default firebaseApp;

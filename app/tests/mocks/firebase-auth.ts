import { jest } from '@jest/globals';
import { mockFirebaseAuth, mockFirebaseUser } from './firebase';

const auth = Object.assign(
  jest.fn(() => mockFirebaseAuth),
  {
    GoogleAuthProvider: { credential: jest.fn(() => ({ provider: 'google' })) },
  }
);

export const GoogleAuthProvider = {
  credential: jest.fn(() => ({ provider: 'google' })),
};
export const signInWithCredential = jest.fn((_auth: unknown, credential: unknown) =>
  auth().signInWithCredential(credential)
);
export const signOut = jest.fn((_auth: unknown) => auth().signOut());
export const getIdToken = jest.fn((user: typeof mockFirebaseUser, forceRefresh?: boolean) =>
  user.getIdToken(forceRefresh)
);
export const updateEmail = jest.fn((user: typeof mockFirebaseUser, email: string) =>
  user.updateEmail(email)
);
export const onAuthStateChanged = jest.fn(
  (authInstance: ReturnType<typeof auth>, listener: (user: typeof mockFirebaseUser | null) => void) =>
    (authInstance.onAuthStateChanged as unknown as (callback: typeof listener) => () => void)(listener)
);

export { auth };
export default auth;

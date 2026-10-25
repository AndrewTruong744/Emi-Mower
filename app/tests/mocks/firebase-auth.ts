import { jest } from '@jest/globals';
import { mockFirebaseAuth, mockFirebaseUser, mockSecondaryAuth } from './firebase';

const auth = Object.assign(
  jest.fn((app?: { name: string }) =>
    app && app.name !== '[DEFAULT]' ? mockSecondaryAuth : mockFirebaseAuth
  ),
  {
    GoogleAuthProvider: { credential: jest.fn(() => ({ provider: 'google' })) },
  }
);

export const GoogleAuthProvider = {
  credential: jest.fn(() => ({ provider: 'google' })),
};
export const signInWithCredential = jest.fn(
  (instance: typeof mockFirebaseAuth | typeof mockSecondaryAuth, credential: unknown) =>
    instance.signInWithCredential(credential)
);
export const signOut = jest.fn((instance: typeof mockFirebaseAuth | typeof mockSecondaryAuth) =>
  instance.signOut()
);
export const getIdToken = jest.fn(
  (user: Pick<typeof mockFirebaseUser, 'getIdToken'>, forceRefresh?: boolean) =>
    user.getIdToken(forceRefresh)
);
export const updateEmail = jest.fn((user: typeof mockFirebaseUser, email: string) =>
  user.updateEmail(email)
);
export const onAuthStateChanged = jest.fn(
  (
    authInstance: typeof mockFirebaseAuth,
    listener: (user: typeof mockFirebaseUser | null) => void
  ) =>
    (authInstance.onAuthStateChanged as unknown as (callback: typeof listener) => () => void)(
      listener
    )
);

export { auth };
export default auth;

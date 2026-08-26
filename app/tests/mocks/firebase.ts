import { jest } from '@jest/globals';

export const mockFirebaseUser = {
  uid: 'firebase-user',
  email: 'user@example.com',
  displayName: 'Test User',
  getIdToken: jest.fn<(...args: any[]) => any>().mockResolvedValue('firebase-token'),
  updateEmail: jest.fn<(...args: any[]) => any>().mockResolvedValue(undefined),
};

export const mockFirebaseAuth = {
  currentUser: mockFirebaseUser as typeof mockFirebaseUser | null,
  signInWithCredential: jest.fn<(...args: any[]) => any>().mockResolvedValue({ user: mockFirebaseUser }),
  signOut: jest.fn<(...args: any[]) => any>().mockResolvedValue(undefined),
  onAuthStateChanged: jest.fn(() => jest.fn()),
};

export const firebaseAuth = mockFirebaseAuth;

export async function getFirebaseIdToken(forceRefresh = false): Promise<string> {
  const user = mockFirebaseAuth.currentUser;
  if (!user) {
    throw new Error('No authenticated Firebase user found');
  }

  return user.getIdToken(forceRefresh);
}

const auth = Object.assign(
  jest.fn(() => mockFirebaseAuth),
  {
    GoogleAuthProvider: { credential: jest.fn(() => ({ provider: 'google' })) },
  }
);

export { auth };
export default {};

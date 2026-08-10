import React from 'react';
import { jest } from '@jest/globals';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { mockFirebaseAuth, mockFirebaseUser } from '../mocks/firebase';
import { mockGoogleSignin } from '../mocks/google-signin';
import { useBoundStore } from '@/store/useBoundStore';
import { zenohQuery } from '@/zenoh/client';

export const mockReplace = jest.fn();

jest.mock('@/zenoh/client', () => ({
  zenohQuery: jest.fn(),
  closeZenoh: jest.fn<(...args: any[]) => any>().mockResolvedValue(undefined),
  cancelZenohOperations: jest.fn(),
  isZenohOperationCancelled: jest.fn(() => false),
}));
jest.mock('expo-router', () => ({
  useRouter: () => ({ replace: mockReplace }),
}));

export const mockedZenohQuery = zenohQuery as jest.Mock<(...args: any[]) => any>;

export function createWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

export function resetHookState() {
  jest.clearAllMocks();
  mockFirebaseUser.getIdToken.mockResolvedValue('firebase-token');
  mockFirebaseUser.updateEmail.mockResolvedValue(undefined);
  mockFirebaseAuth.currentUser = mockFirebaseUser;
  mockFirebaseAuth.signInWithCredential.mockResolvedValue({ user: mockFirebaseUser });
  mockFirebaseAuth.signOut.mockResolvedValue(undefined);
  mockGoogleSignin.signIn.mockResolvedValue({
    type: 'success',
    data: { serverAuthCode: 'server-auth-code' },
  });
  mockGoogleSignin.getTokens.mockResolvedValue({
    idToken: 'google-id-token',
    accessToken: 'access-token',
  });
  useBoundStore.getState().resetStore();
}

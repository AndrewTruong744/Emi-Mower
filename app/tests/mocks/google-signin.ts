import { jest } from '@jest/globals';

export const mockGoogleSignin = {
  configure: jest.fn(),
  hasPlayServices: jest.fn<(...args: any[]) => any>().mockResolvedValue(undefined),
  signIn: jest.fn<(...args: any[]) => any>().mockResolvedValue({
    type: 'success',
    data: { serverAuthCode: 'server-auth-code' },
  }),
  getTokens: jest.fn<(...args: any[]) => any>().mockResolvedValue({ idToken: 'google-id-token', accessToken: 'access-token' }),
  signOut: jest.fn<(...args: any[]) => any>().mockResolvedValue(undefined),
};

export const GoogleSignin = mockGoogleSignin;

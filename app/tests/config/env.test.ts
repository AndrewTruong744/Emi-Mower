import { afterEach, describe, expect, it, jest } from '@jest/globals';

const originalZenohUrl = process.env.EXPO_PUBLIC_ZENOH_URL;
const originalGoogleWebClientId = process.env.EXPO_PUBLIC_WEB_CLIENT_ID;

function loadEnv() {
  let loadedEnv: typeof import('@/config/env').env | undefined;
  jest.isolateModules(() => {
    loadedEnv = require('@/config/env').env;
  });
  return loadedEnv!;
}

afterEach(() => {
  process.env.EXPO_PUBLIC_ZENOH_URL = originalZenohUrl;
  process.env.EXPO_PUBLIC_WEB_CLIENT_ID = originalGoogleWebClientId;
});

describe('environment configuration', () => {
  it('accepts a credential-free WebSocket URL and Google client ID', () => {
    process.env.EXPO_PUBLIC_ZENOH_URL = 'wss://zenoh.example.com/ws';
    process.env.EXPO_PUBLIC_WEB_CLIENT_ID = 'google-client-id';

    expect(loadEnv()).toEqual({
      zenohUrl: 'wss://zenoh.example.com/ws',
      googleWebClientId: 'google-client-id',
    });
  });

  it('rejects a missing required variable', () => {
    delete process.env.EXPO_PUBLIC_WEB_CLIENT_ID;

    expect(loadEnv).toThrow('Missing required environment variable: EXPO_PUBLIC_WEB_CLIENT_ID');
  });

  it('rejects an invalid Zenoh locator', () => {
    process.env.EXPO_PUBLIC_ZENOH_URL = 'https://zenoh.example.com';

    expect(loadEnv).toThrow('EXPO_PUBLIC_ZENOH_URL must use ws:// or wss://');
  });
});

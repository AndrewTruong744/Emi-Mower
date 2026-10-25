function required(value: string | undefined, name: string): string {
  const trimmedValue = value?.trim();
  if (!trimmedValue) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return trimmedValue;
}

function validateZenohUrl(value: string): string {
  if (!/^(tls|tcp)\/[^\s/@]+:\d+$/.test(value)) {
    throw new Error('EXPO_PUBLIC_ZENOH_URL must be a native tls/ or tcp/ endpoint');
  }
  return value;
}

// Expo inlines EXPO_PUBLIC_* values at build time, so keep these accesses direct.
export const env = Object.freeze({
  zenohUrl: validateZenohUrl(required(process.env.EXPO_PUBLIC_ZENOH_URL, 'EXPO_PUBLIC_ZENOH_URL')),
  googleWebClientId: required(process.env.EXPO_PUBLIC_WEB_CLIENT_ID, 'EXPO_PUBLIC_WEB_CLIENT_ID'),
});

function required(value, name) {
  const trimmedValue = value?.trim();
  if (!trimmedValue) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return trimmedValue;
}

function validateZenohUrl(value) {
  let url;
  try {
    url = new URL(value);
  } catch {
    throw new Error('EXPO_PUBLIC_ZENOH_URL must be a valid ws:// or wss:// URL');
  }

  if (url.protocol !== 'ws:' && url.protocol !== 'wss:') {
    throw new Error('EXPO_PUBLIC_ZENOH_URL must use ws:// or wss://');
  }
  if (!url.hostname) {
    throw new Error('EXPO_PUBLIC_ZENOH_URL must include a host');
  }
  if (url.username || url.password) {
    throw new Error('EXPO_PUBLIC_ZENOH_URL must not include credentials');
  }
}

module.exports = ({ config }) => {
  validateZenohUrl(required(process.env.EXPO_PUBLIC_ZENOH_URL, 'EXPO_PUBLIC_ZENOH_URL'));
  required(process.env.EXPO_PUBLIC_WEB_CLIENT_ID, 'EXPO_PUBLIC_WEB_CLIENT_ID');
  return config;
};

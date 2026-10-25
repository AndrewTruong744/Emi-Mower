require('@expo/env').load(__dirname);

function required(value, name) {
  const trimmedValue = value?.trim();
  if (!trimmedValue) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return trimmedValue;
}

function validateZenohUrl(value) {
  if (!/^(tls|tcp)\/[^\s/@]+:\d+$/.test(value)) {
    throw new Error('EXPO_PUBLIC_ZENOH_URL must be a native tls/ or tcp/ endpoint');
  }
}

module.exports = ({ config }) => {
  validateZenohUrl(required(process.env.EXPO_PUBLIC_ZENOH_URL, 'EXPO_PUBLIC_ZENOH_URL'));
  required(process.env.EXPO_PUBLIC_WEB_CLIENT_ID, 'EXPO_PUBLIC_WEB_CLIENT_ID');
  return config;
};

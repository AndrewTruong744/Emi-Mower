process.env.EXPO_PUBLIC_ZENOH_URL = 'tcp/127.0.0.1:7447';
process.env.EXPO_PUBLIC_WEB_CLIENT_ID = 'test-google-web-client-id';

jest.mock('@expo/vector-icons/MaterialCommunityIcons', () => ({
  __esModule: true,
  default: () => null,
}));

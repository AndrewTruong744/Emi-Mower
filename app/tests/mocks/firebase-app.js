const { jest: jestGlobal } = require('@jest/globals');
const app = { name: '[DEFAULT]', options: { projectId: 'test-project' } };
module.exports = {
  getApp: () => app,
  initializeApp: jestGlobal.fn(async (options, config) => {
    // Match RNFirebase's validation: named apps require strings even for
    // Database, Storage and Messaging, which this auth-only session doesn't use.
    for (const key of [
      'apiKey',
      'appId',
      'projectId',
      'databaseURL',
      'storageBucket',
      'messagingSenderId',
    ]) {
      if (typeof options[key] !== 'string') {
        throw new Error(`Missing or invalid FirebaseOptions property '${key}'.`);
      }
    }
    return { name: config.name, options };
  }),
  deleteApp: jestGlobal.fn(async () => undefined),
  default: app,
};

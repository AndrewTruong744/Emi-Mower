// Learn more https://docs.expo.io/guides/customizing-metro
/** @type {import('expo/metro-config').MetroConfig} */

const { getDefaultConfig } = require('expo/metro-config');
const path = require('path');

const config = getDefaultConfig(__dirname);

const keyExprShim = path.resolve(__dirname, 'src/config/keyExprShim.ts');
const leb128Shim = path.resolve(__dirname, 'src/config/leb128Shim.ts');
const defaultResolveRequest = config.resolver.resolveRequest;
config.resolver.resolveRequest = (context, moduleName, platform) => {
  if (
    (moduleName === './key_expr/zenoh_keyexpr_wrapper.js' ||
      moduleName.endsWith('/key_expr/zenoh_keyexpr_wrapper.js')) &&
    context.originModulePath.includes('@eclipse-zenoh/zenoh-ts/dist')
  ) {
    return { type: 'sourceFile', filePath: keyExprShim };
  }

  if (moduleName === '@thi.ng/leb128' || moduleName.startsWith('@thi.ng/leb128/')) {
    return { type: 'sourceFile', filePath: leb128Shim };
  }

  return defaultResolveRequest
    ? defaultResolveRequest(context, moduleName, platform)
    : context.resolveRequest(context, moduleName, platform);
};

module.exports = config;

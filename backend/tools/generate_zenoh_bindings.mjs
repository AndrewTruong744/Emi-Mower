import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import yaml from 'js-yaml';

import { renderPaths } from './zenoh_bindings/paths.mjs';
import { createPythonRenderer } from './zenoh_bindings/python.mjs';
import { createRustRenderer } from './zenoh_bindings/rust.mjs';
import { createSchemaContext } from './zenoh_bindings/schema.mjs';
import { createTypeScriptRenderer } from './zenoh_bindings/typescript.mjs';

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const backendDirectory = resolve(scriptDirectory, '..');
const repositoryDirectory = resolve(backendDirectory, '..');
const contractPath = resolve(backendDirectory, 'zenoh_asyncapi.yaml');
const { load } = yaml;

const contract = load(readFileSync(contractPath, 'utf8'));
if (contract.asyncapi !== '3.0.0') {
  throw new Error(`Expected AsyncAPI 3.0.0, received ${contract.asyncapi}`);
}
const schemas = contract.components?.schemas;
const channels = contract.channels;
if (!schemas || !channels) throw new Error('Missing AsyncAPI schemas or channels');

const schemaContext = createSchemaContext(schemas);
const { backendTypes, backendExports } = createPythonRenderer(schemaContext);
const { appTypes } = createTypeScriptRenderer(schemaContext);
const { gatewayTypes } = createRustRenderer(schemaContext);
const paths = renderPaths(channels);

const outputs = new Map([
  [resolve(repositoryDirectory, 'app/src/generated/zenoh.ts'), appTypes()],
  [resolve(repositoryDirectory, 'app/src/generated/zenohPaths.ts'), paths.app],
  [resolve(backendDirectory, 'src/zenoh/generated/types.py'), backendTypes()],
  [resolve(backendDirectory, 'src/zenoh/generated/__init__.py'), backendExports()],
  [resolve(backendDirectory, 'src/zenoh/generated/paths.py'), paths.backend],
  [resolve(repositoryDirectory, 'nvidia_jetson/ros_ws/src/emi_mower_zenoh_gateway/src/generated/zenoh.rs'), gatewayTypes()],
  [resolve(repositoryDirectory, 'nvidia_jetson/ros_ws/src/emi_mower_zenoh_gateway/src/generated/zenoh_paths.rs'), paths.rust],
]);

if (process.argv.includes('--check')) {
  const stale = [...outputs].filter(([path, output]) => readFileSync(path, 'utf8') !== output);
  if (stale.length) throw new Error(`Generated bindings are stale: ${stale.map(([path]) => path).join(', ')}`);
} else {
  for (const [path, output] of outputs) writeFileSync(path, output);
}

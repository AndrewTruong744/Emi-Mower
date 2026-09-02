import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const asyncApiPath = resolve(scriptDirectory, '../zenoh_asyncapi.yaml');
const appOutputPath = resolve(scriptDirectory, '../../app/src/generated/zenohPaths.ts');
const backendOutputPath = resolve(scriptDirectory, '../src/zenoh/generated/paths.py');
const rustOutputPath = resolve(
  scriptDirectory,
  '../../nvidia_jetson/ros_ws/src/emi_mower_zenoh_gateway/src/generated/zenoh_paths.rs'
);
const document = readFileSync(asyncApiPath, 'utf8');

const channels = document.match(/^channels:\n([\s\S]*?)^operations:/m)?.[1];
if (!channels) throw new Error('AsyncAPI document has no channels section');

const channelDefinitions = [...channels.matchAll(/^  ([A-Za-z][A-Za-z0-9]*):\n    address: (.+)$/gm)].map(
  ([, name, address]) => ({
    name,
    address,
    parameters: [...address.matchAll(/\{([A-Za-z_][A-Za-z0-9_]*)\}/g)].map(([, parameter]) => parameter),
  })
);
if (channelDefinitions.length === 0) throw new Error('No AsyncAPI channel addresses found');

function toUpperSnakeCase(value) {
  return value.replace(/([a-z0-9])([A-Z])/g, '$1_$2').toUpperCase();
}

function toSnakeCase(value) {
  return value.replace(/([a-z0-9])([A-Z])/g, '$1_$2').toLowerCase();
}

function toCamelCase(value) {
  return value.replace(/_([a-z])/g, (_, character) => character.toUpperCase());
}

function typescriptPathFunction({ name, address, parameters }) {
  const constant = `${toUpperSnakeCase(name)}_ADDRESS`;
  const args = parameters.map((parameter) => `${toCamelCase(parameter)}: string`).join(', ');
  const expression =
    parameters.length === 0
      ? constant
      : `(
    ${constant}
${parameters.map((parameter) => `      .replace('{${parameter}}', ${toCamelCase(parameter)})`).join('\n')}
  )`;

  return `export const ${constant} = ${JSON.stringify(address)} as const;

export function ${name}Path(${args}): string {
  return ${expression};
}`;
}

function pythonPathFunction({ name, address, parameters }) {
  const constant = `${toUpperSnakeCase(name)}_ADDRESS`;
  const functionName = `${toSnakeCase(name)}_path`;
  const args = parameters.map((parameter) => `${parameter}: str`).join(', ');
  const expression =
    parameters.length === 0
      ? constant
      : `(
        ${constant}
${parameters.map((parameter) => `        .replace("{${parameter}}", ${parameter})`).join('\n')}
    )`;

  return `${constant} = ${JSON.stringify(address)}


def ${functionName}(${args}) -> str:
    return ${expression}`;
}

function rustPathFunction({ name, address, parameters }) {
  const constant = `${toUpperSnakeCase(name)}_ADDRESS`;
  const functionName = `${toSnakeCase(name)}_path`;
  const args = parameters.map((parameter) => `${parameter}: &str`).join(', ');
  const replacements = parameters
    .map((parameter) => `    path = path.replace("{${parameter}}", ${parameter});`)
    .join('\n');
  return `pub const ${constant}: &str = ${JSON.stringify(address)};

pub fn ${functionName}(${args}) -> String {
    let ${parameters.length ? 'mut ' : ''}path = ${constant}.to_owned();
${replacements}
    path
}`;
}

const appOutput = `/** Generated from backend/zenoh_asyncapi.yaml. Do not edit manually. */

${channelDefinitions.map(typescriptPathFunction).join('\n\n')}
`;
const backendOutput = `"""Generated from \`\`backend/zenoh_asyncapi.yaml\`\`. Do not edit manually."""

${channelDefinitions.map(pythonPathFunction).join('\n\n')}
`;
const rustOutput = `//! Generated from \`backend/zenoh_asyncapi.yaml\`. Do not edit manually.
//!
//! Regenerate with \`backend/scripts/generate_types.sh\`.

${channelDefinitions.map(rustPathFunction).join('\n\n')}
`;

writeFileSync(appOutputPath, appOutput);
writeFileSync(backendOutputPath, backendOutput);
writeFileSync(rustOutputPath, rustOutput);

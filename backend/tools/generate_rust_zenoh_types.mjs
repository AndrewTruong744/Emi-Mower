import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const asyncApiPath = resolve(scriptDirectory, '../zenoh_asyncapi.yaml');
const outputDirectory = resolve(
  scriptDirectory,
  '../../nvidia_jetson/ros_ws/src/emi_mower_zenoh_gateway/src/generated'
);
const outputPath = resolve(outputDirectory, 'zenoh.rs');
const document = readFileSync(asyncApiPath, 'utf8');

// These are the native Zenoh payloads consumed or produced by the gateway.
// ROS messages are intentionally not generated here: they are owned by ROS IDL.
const gatewaySchemas = [
  'JoystickCommand',
  'ImuTelemetry',
  'TelemetryRecord',
  'TelemetryList',
  'MowerCertificateRenewChallengeRequest',
  'MowerCertificateRenewChallengeResponse',
  'MowerCertificateRenewCompleteRequest',
  'MowerCertificateRenewCompleteResponse',
];

function schemaBlock(name) {
  const schemas = document.split('  schemas:\n')[1];
  if (!schemas) throw new Error('AsyncAPI document has no components.schemas section');
  const match = schemas.match(
    new RegExp(`^    ${name}:\\n(?<body>[\\s\\S]*?)(?=^    [A-Z][A-Za-z0-9]*:|(?![\\s\\S]))`, 'm')
  );
  if (!match?.groups?.body) throw new Error(`Missing AsyncAPI schema: ${name}`);
  return match.groups.body;
}

function requiredFields(block) {
  const match = block.match(/^      required: \[([^\]]*)\]/m);
  return new Set(match ? match[1].split(',').map((field) => field.trim()) : []);
}

function properties(block) {
  const section = block.match(
    /^      properties:\n(?<body>[\s\S]*?)(?=^      [a-zA-Z_]+:|^    [A-Z]|(?![\s\S]))/m
  )
    ?.groups?.body;
  if (!section) return [];

  return [...section.matchAll(/^        (?<name>[a-zA-Z_][a-zA-Z0-9_]*):(?<inline>.*)\n(?<nested>(?:^          .*\n?)*)/gm)].map(
    ({ groups }) => ({ name: groups.name, definition: `${groups.inline}\n${groups.nested}` })
  );
}

function rustType(definition) {
  const reference = definition.match(/\$ref: '#\/components\/schemas\/([A-Za-z0-9_]+)'/);
  if (reference) return reference[1];
  if (/type: array/.test(definition)) {
    const item = definition.match(/items: \{\$ref: '#\/components\/schemas\/([A-Za-z0-9_]+)'\}/);
    if (!item) throw new Error(`Unsupported array schema: ${definition.trim()}`);
    return `Vec<${item[1]}>`;
  }
  if (/type: string/.test(definition)) return 'String';
  if (/type: integer/.test(definition)) return 'i64';
  if (/type: number/.test(definition)) return 'f64';
  if (/type: boolean/.test(definition)) return 'bool';
  throw new Error(`Unsupported schema property: ${definition.trim()}`);
}

function rustStruct(name, block) {
  const required = requiredFields(block);
  const denyUnknown = /additionalProperties: false/.test(block);
  const fields = properties(block).map(({ name: field, definition }) => {
    const nullable = /nullable: true/.test(definition);
    const hasDefault = /default: /.test(definition);
    const isRequired = required.has(field);
    const type = rustType(definition);
    const optional = nullable || !isRequired;
    const attributes = [];
    if (!isRequired || hasDefault) attributes.push('    #[serde(default)]');
    return `${attributes.join('\n')}${attributes.length ? '\n' : ''}    pub ${field}: ${optional ? `Option<${type}>` : type},`;
  });
  const serdeAttribute = denyUnknown ? '#[serde(deny_unknown_fields)]\n' : '';
  return `#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]\n${serdeAttribute}pub struct ${name} {\n${fields.join('\n')}\n}`;
}

function rustSchema(name) {
  const block = schemaBlock(name);
  if (/^      type: array/m.test(block)) {
    const item = block.match(/items: \{\$ref: '#\/components\/schemas\/([A-Za-z0-9_]+)'\}/);
    if (!item) throw new Error(`Unsupported Rust array schema: ${name}`);
    return `pub type ${name} = Vec<${item[1]}>;`;
  }
  if (!/^      type: object/m.test(block)) throw new Error(`Unsupported Rust schema shape: ${name}`);
  return rustStruct(name, block);
}

const output = `//! Generated from \`backend/zenoh_asyncapi.yaml\`. Do not edit manually.\n//!\n//! Regenerate with \`backend/tools/generate_types.sh\`. These are the native\n//! Zenoh payloads used by \`emi_mower_zenoh_gateway\`; ROS messages remain ROS IDL.\n\nuse serde::{Deserialize, Serialize};\n\n${gatewaySchemas.map(rustSchema).join('\n\n')}\n`;

mkdirSync(outputDirectory, { recursive: true });
writeFileSync(outputPath, output);

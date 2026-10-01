const gatewaySchemas = [
  'JoystickCommand',
  'ImuTelemetry',
  'TelemetryRecord',
  'TelemetryList',
  'MowerCutoutDelivery',
  'MowerCertificateRenewChallengeRequest',
  'MowerCertificateRenewChallengeResponse',
  'MowerCertificateRenewCompleteRequest',
  'MowerCertificateRenewCompleteResponse',
];

export function createRustRenderer({ schemas, schemaReference, splitNullable }) {
  function rustType(schema) {
    const value = splitNullable(schema).schema;
    if (value.$ref) return schemaReference(value.$ref);
    if (value.type === 'array') return `Vec<${rustType(value.items)}>`;
    if (value.type === 'string') return 'String';
    if (value.type === 'integer') return 'i64';
    if (value.type === 'number') return 'f64';
    if (value.type === 'boolean') return 'bool';
    throw new Error(`Unsupported Rust schema: ${JSON.stringify(schema)}`);
  }

  function rustModel(name) {
    const schema = schemas[name];
    if (schema.type === 'array') return `pub type ${name} = ${rustType(schema)};`;
    if (schema.type !== 'object') throw new Error(`Unsupported gateway schema ${name}`);
    const required = new Set(schema.required ?? []);
    const fields = Object.entries(schema.properties ?? {}).map(([field, property]) => {
      const optional = splitNullable(property).nullable || (!required.has(field) && !Object.hasOwn(property, 'default'));
      const defaultAttribute = !required.has(field) ? '    #[serde(default)]\n' : '';
      const type = rustType(property);
      return `${defaultAttribute}    pub ${field}: ${optional ? `Option<${type}>` : type},`;
    });
    return `#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]\npub struct ${name} {${fields.length ? `\n${fields.join('\n')}\n` : ''}}`;
  }

  function gatewayTypes() {
    return `//! Generated from \`backend/zenoh_asyncapi.yaml\`. Do not edit manually.\n//!\n//! Regenerate with \`npm --prefix tools run generate\`. These are the native\n//! Zenoh payloads used by \`emi_mower_zenoh_gateway\`; ROS messages remain ROS IDL.\n\nuse serde::{Deserialize, Serialize};\n\n${gatewaySchemas.map(rustModel).join('\n\n')}\n`;
  }

  return { gatewayTypes };
}

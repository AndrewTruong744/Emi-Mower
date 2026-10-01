export function createTypeScriptRenderer({
  schemas, namesInDependencyOrder, splitNullable, schemaReference, literal,
}) {
  function tsType(schema) {
    const { schema: value, nullable } = splitNullable(schema);
    let type;
    if (value.$ref) type = schemaReference(value.$ref);
    else if (Object.hasOwn(value, 'const')) type = literal(value.const, 'typescript');
    else if (value.enum) type = value.enum.map((item) => literal(item, 'typescript')).join(' | ');
    else if (value.type === 'array') type = `${tsType(value.items)}[]`;
    else if (value.type === 'string') type = 'string';
    else if (value.type === 'integer' || value.type === 'number') type = 'number';
    else if (value.type === 'boolean') type = 'boolean';
    else throw new Error(`Unsupported TypeScript schema: ${JSON.stringify(schema)}`);
    return nullable ? `${type} | null` : type;
  }

  function typeDeclaration(name) {
    const schema = schemas[name];
    if (schema.oneOf) {
      return `export type ${name} = ${schema.oneOf.map((item) => schemaReference(item.$ref)).join(' | ')};`;
    }
    if (schema.type === 'array') return `export type ${name} = ${tsType(schema)};`;
    if (schema.type !== 'object') return `export type ${name} = ${tsType(schema)};`;
    if (Object.keys(schema.properties ?? {}).length === 0) return `export type ${name} = Record<string, unknown>;`;
    const required = new Set(schema.required ?? []);
    const fields = Object.entries(schema.properties ?? {}).map(([field, property]) =>
      `  ${field}${required.has(field) ? '' : '?'}: ${tsType(property)};`);
    return `export interface ${name} {\n${fields.join('\n')}\n}`;
  }

  function appTypes() {
    const declarations = namesInDependencyOrder.map(typeDeclaration).join('\n\n');
    return `/** Generated from backend/zenoh_asyncapi.yaml. Do not edit manually. */\n\n${declarations}\n`;
  }

  return { appTypes };
}

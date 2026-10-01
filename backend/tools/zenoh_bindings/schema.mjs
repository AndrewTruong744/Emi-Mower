export function createSchemaContext(schemas) {
  function splitNullable(schema) {
    if (Object.hasOwn(schema, 'nullable')) {
      throw new Error('Use JSON Schema null unions instead of nullable: true');
    }
    if (Array.isArray(schema.type)) {
      const nonNull = schema.type.filter((type) => type !== 'null');
      if (schema.type.length !== 2 || nonNull.length !== 1) {
        throw new Error(`Unsupported schema type union: ${JSON.stringify(schema)}`);
      }
      return { schema: { ...schema, type: nonNull[0] }, nullable: true };
    }
    if (schema.oneOf?.some((variant) => variant.type === 'null')) {
      if (schema.oneOf.length !== 2) {
        throw new Error(`Unsupported nullable oneOf: ${JSON.stringify(schema)}`);
      }
      return { schema: schema.oneOf.find((variant) => variant.type !== 'null'), nullable: true };
    }
    return { schema, nullable: false };
  }

  function schemaReference(reference) {
    const prefix = '#/components/schemas/';
    if (!reference?.startsWith(prefix)) throw new Error(`Unsupported schema reference: ${reference}`);
    const name = reference.slice(prefix.length);
    if (!schemas[name]) throw new Error(`Missing referenced schema ${name}`);
    return name;
  }

  function orderedSchemas() {
    const ordered = [];
    const visited = new Set();
    const visiting = new Set();
    function visit(name) {
      if (visited.has(name)) return;
      if (visiting.has(name)) throw new Error(`Cyclic schema references at ${name}`);
      visiting.add(name);
      const schema = schemas[name];
      for (const property of Object.values(schema.properties ?? {})) {
        const value = splitNullable(property).schema;
        const reference = value.$ref ?? splitNullable(value.items ?? {}).schema.$ref;
        if (reference) visit(schemaReference(reference));
      }
      for (const item of schema.oneOf ?? []) visit(schemaReference(item.$ref));
      if (schema.items?.$ref) visit(schemaReference(schema.items.$ref));
      visiting.delete(name);
      visited.add(name);
      ordered.push(name);
    }
    for (const name of Object.keys(schemas)) visit(name);
    return ordered;
  }

  const namesInDependencyOrder = orderedSchemas();

  function literal(value, language) {
    if (language === 'python' && value === null) return 'None';
    if (language === 'python' && typeof value === 'boolean') return value ? 'True' : 'False';
    return JSON.stringify(value);
  }

  return {
    schemas, namesInDependencyOrder, schemaReference, splitNullable,
    literal,
  };
}

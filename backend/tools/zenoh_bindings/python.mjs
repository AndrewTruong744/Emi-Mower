export function createPythonRenderer({
  schemas, namesInDependencyOrder, schemaReference, splitNullable, literal,
}) {
  function pythonType(schema) {
    const { schema: value, nullable } = splitNullable(schema);
    let type;
    if (value.$ref) type = schemaReference(value.$ref);
    else if (Object.hasOwn(value, 'const')) type = `Literal[${literal(value.const, 'python')}]`;
    else if (value.enum) type = `Literal[${value.enum.map((item) => literal(item, 'python')).join(', ')}]`;
    else if (value.type === 'array') type = `list[${pythonType(value.items)}]`;
    else if (value.type === 'string') type = 'str';
    else if (value.type === 'integer') type = 'int';
    else if (value.type === 'number') type = 'float';
    else if (value.type === 'boolean') type = 'bool';
    else throw new Error(`Unsupported Python schema: ${JSON.stringify(schema)}`);
    return nullable ? `${type} | None` : type;
  }

  function pythonField(name, property, required) {
    const { schema: value } = splitNullable(property);
    const hasDefault = Object.hasOwn(property, 'default');
    const type = pythonType(property);
    if (required) return `    ${name}: ${type}`;
    if (hasDefault) {
      const defaultValue = value.type === 'number' && Number.isInteger(property.default)
        ? `${property.default}.0`
        : literal(property.default, 'python');
      return `    ${name}: ${type} = ${defaultValue}`;
    }
    return `    ${name}: ${type} = None`;
  }

  function pythonModel(name) {
    const schema = schemas[name];
    if (schema.oneOf) {
      return `${name} = ${schema.oneOf.map((item) => schemaReference(item.$ref)).join(' | ')}`;
    }
    if (schema.type === 'array') {
      return `class ${name}(RootModel[${pythonType(schema)}]):\n    pass`;
    }
    if (schema.type !== 'object') throw new Error(`Unsupported Python model ${name}`);
    const required = new Set(schema.required ?? []);
    const fields = Object.entries(schema.properties ?? {}).map(([field, property]) =>
      pythonField(field, property, required.has(field)));
    return `class ${name}(ZenohModel):\n${fields.length ? fields.join('\n') : '    pass'}`;
  }

  function backendTypes() {
    const models = namesInDependencyOrder.map(pythonModel).join('\n\n\n');
    return `"""Generated from \`\`backend/zenoh_asyncapi.yaml\`\`. Do not edit manually.

Regenerate with \`\`npm --prefix tools run generate\`\`.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, RootModel


class ZenohModel(BaseModel):
    model_config = ConfigDict(extra="allow")


${models}
`;
  }

  function backendExports() {
    const names = [...namesInDependencyOrder].sort();
    return `"""Generated AsyncAPI models for the Zenoh wire messages."""\n\nfrom src.zenoh.generated.types import (\n${names.map((name) => `    ${name},`).join('\n')}\n)\n\n__all__ = [\n${names.map((name) => `    "${name}",`).join('\n')}\n]\n`;
  }

  return { backendTypes, backendExports };
}

import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const asyncApi = readFileSync(resolve(scriptDirectory, '../zenoh_asyncapi.yaml'), 'utf8');
const pythonPath = resolve(scriptDirectory, '../src/zenoh/generated/types.py');
const initPath = resolve(scriptDirectory, '../src/zenoh/generated/__init__.py');
const typescriptPath = resolve(scriptDirectory, '../../app/src/generated/zenoh.ts');
const schemaNames = ['CutoutUploadNotification', 'MowerCutoutDelivery'];

function schemaBlock(name) {
  const schemas = asyncApi.split('  schemas:\n')[1];
  const match = schemas?.match(
    new RegExp(`^    ${name}:\\n(?<body>[\\s\\S]*?)(?=^    [A-Z][A-Za-z0-9]*:|(?![\\s\\S]))`, 'm')
  );
  if (!match?.groups?.body) throw new Error(`Missing AsyncAPI schema: ${name}`);
  return match.groups.body;
}

function schema(name) {
  const block = schemaBlock(name);
  const required = new Set((block.match(/^      required: \[([^\]]*)\]/m)?.[1] ?? '')
    .split(',').map((field) => field.trim()).filter(Boolean));
  const properties = [...block.matchAll(
    /^        (?<name>[a-zA-Z_][a-zA-Z0-9_]*):(?<inline>.*)\n(?<nested>(?:^          .*\n?)*)/gm
  )].map(({ groups }) => ({ name: groups.name, definition: `${groups.inline}\n${groups.nested}` }));
  return { name, required, properties };
}

function scalarType(definition, language) {
  const enums = definition.match(/enum: \[([^\]]+)\]/)?.[1]
    .split(',').map((value) => value.trim().replaceAll("'", '').replaceAll('"', ''));
  if (enums) {
    return language === 'python'
      ? `Literal[${enums.map((value) => JSON.stringify(value)).join(', ')}]`
      : enums.map((value) => JSON.stringify(value)).join(' | ');
  }
  if (/type: array/.test(definition)) return language === 'python' ? 'list[str]' : 'string[]';
  if (/type: boolean/.test(definition)) return language === 'python' ? 'bool' : 'boolean';
  if (/type: integer/.test(definition)) return language === 'python' ? 'int' : 'number';
  if (/type: number/.test(definition)) return language === 'python' ? 'float' : 'number';
  if (/type: string/.test(definition)) return language === 'python' ? 'str' : 'string';
  throw new Error(`Unsupported cutout schema property: ${definition.trim()}`);
}

function pythonClass({ name, required, properties }) {
  const fields = properties.map(({ name: field, definition }) => {
    const type = scalarType(definition, 'python');
    return required.has(field) ? `    ${field}: ${type}` : `    ${field}: ${type} | None = None`;
  });
  return `class ${name}(BaseModel):\n    model_config = ConfigDict(extra="forbid")\n\n${fields.join('\n')}\n`;
}

function typescriptInterface({ name, required, properties }) {
  const fields = properties.map(({ name: field, definition }) =>
    `  ${field}${required.has(field) ? '' : '?'}: ${scalarType(definition, 'typescript')};`
  );
  return `export interface ${name} {\n${fields.join('\n')}\n}\n`;
}

function replaceBetween(source, first, after, replacement) {
  const start = source.indexOf(first);
  const end = source.indexOf(after, start);
  if (start < 0 || end < 0) throw new Error(`Could not replace generated block beginning ${first}`);
  return `${source.slice(0, start)}${replacement}\n${source.slice(end)}`;
}

const schemas = schemaNames.map(schema);
const pythonTypes = `${schemas.map(pythonClass).join('\n')}\n`;
let python = readFileSync(pythonPath, 'utf8');
python = replaceBetween(python, 'class CutoutUploadNotification', 'class ProblemDetails', pythonTypes);
python = python
  .replace('    | MowerCutoutDownloadUrlRequest\n', '')
  .replace('    | MowerCutoutDownloadUrlResponse\n', '')
  .replace('    | MowerCutoutDelivery\n', '')
  .replace('    | CutoutUploadNotification\n', '    | CutoutUploadNotification\n    | MowerCutoutDelivery\n');
writeFileSync(pythonPath, python);

let init = readFileSync(initPath, 'utf8')
  .replace('    MowerCutoutDownloadUrlRequest,\n', '')
  .replace('    MowerCutoutDownloadUrlResponse,\n', '')
  .replace('    MowerCutoutDelivery,\n', '')
  .replace('    CutoutUploadUrlResponse,\n', '    CutoutUploadUrlResponse,\n    MowerCutoutDelivery,\n')
  .replace('    "MowerCutoutDownloadUrlRequest",\n', '')
  .replace('    "MowerCutoutDownloadUrlResponse",\n', '')
  .replace('    "MowerCutoutDelivery",\n', '')
  .replace('    "CutoutUploadUrlResponse",\n', '    "CutoutUploadUrlResponse",\n    "MowerCutoutDelivery",\n');
writeFileSync(initPath, init);

const typescriptTypes = `${schemas.map(typescriptInterface).join('\n')}\n`;
let typescript = readFileSync(typescriptPath, 'utf8');
typescript = replaceBetween(typescript, 'export interface CutoutUploadNotification', 'export interface ProblemDetails', typescriptTypes);
writeFileSync(typescriptPath, typescript);

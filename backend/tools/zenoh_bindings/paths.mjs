export function renderPaths(channels) {
  const routeDefinitions = Object.entries(channels).map(([name, channel]) => {
    if (typeof channel.address !== 'string') throw new Error(`Channel ${name} has no address`);
    return {
      name,
      address: channel.address,
      parameters: [...channel.address.matchAll(/\{([A-Za-z_][A-Za-z0-9_]*)\}/g)]
        .map((match) => match[1]),
    };
  });
  if (routeDefinitions.length === 0) throw new Error('No AsyncAPI channels found');

  function upperSnake(value) {
    return value.replace(/([a-z0-9])([A-Z])/g, '$1_$2').toUpperCase();
  }

  function snake(value) {
    return value.replace(/([a-z0-9])([A-Z])/g, '$1_$2').toLowerCase();
  }

  function camel(value) {
    return value.replace(/_([a-z])/g, (_, character) => character.toUpperCase());
  }

  function typescriptPath({ name, address, parameters }) {
    const constant = `${upperSnake(name)}_ADDRESS`;
    const args = parameters.map((parameter) => `${camel(parameter)}: string`).join(', ');
    const expression = parameters.length === 0 ? constant
      : `(\n    ${constant}\n${parameters.map((parameter) =>
        `      .replace('{${parameter}}', ${camel(parameter)})`).join('\n')}\n  )`;
    return `export const ${constant} = ${JSON.stringify(address)} as const;\n\nexport function ${name}Path(${args}): string {\n  return ${expression};\n}`;
  }

  function pythonPath({ name, address, parameters }) {
    const constant = `${upperSnake(name)}_ADDRESS`;
    const args = parameters.map((parameter) => `${parameter}: str`).join(', ');
    const declaration = `${constant} = ${JSON.stringify(address)}`;
    const formattedDeclaration = declaration.length > 88
      ? `${constant} = (\n    ${JSON.stringify(address)}\n)`
      : declaration;
    let expression = constant;
    if (parameters.length === 1) {
      expression += `.replace("{${parameters[0]}}", ${parameters[0]})`;
    } else if (parameters.length === 2) {
      expression = `${constant}.replace("{${parameters[0]}}", ${parameters[0]}).replace(\n        "{${parameters[1]}}", ${parameters[1]}\n    )`;
    } else if (parameters.length > 2) {
      expression = `(\n        ${constant}\n${parameters.map((parameter) =>
        `        .replace("{${parameter}}", ${parameter})`).join('\n')}\n    )`;
    }
    return `${formattedDeclaration}\n\n\ndef ${snake(name)}_path(${args}) -> str:\n    return ${expression}`;
  }

  function rustPath({ name, address, parameters }) {
    const constant = `${upperSnake(name)}_ADDRESS`;
    const functionName = `${snake(name)}_path`;
    const args = parameters.map((parameter) => `${parameter}: &str`).join(', ');
    const declaration = `pub const ${constant}: &str = ${JSON.stringify(address)};`;
    const formattedDeclaration = declaration.length > 100
      ? `pub const ${constant}: &str =\n    ${JSON.stringify(address)};`
      : declaration;
    if (parameters.length === 0) {
      return `${formattedDeclaration}\n\npub fn ${functionName}() -> String {\n    ${constant}.to_owned()\n}`;
    }
    return `${formattedDeclaration}\n\npub fn ${functionName}(${args}) -> String {\n    let mut path = ${constant}.to_owned();\n${parameters.map((parameter) =>
      `    path = path.replace("{${parameter}}", ${parameter});`).join('\n')}\n    path\n}`;
  }

  return {
    app: `/** Generated from backend/zenoh_asyncapi.yaml. Do not edit manually. */\n\n${routeDefinitions.map(typescriptPath).join('\n\n')}\n`,
    backend: `"""Generated from \`\`backend/zenoh_asyncapi.yaml\`\`. Do not edit manually."""\n\n${routeDefinitions.map(pythonPath).join('\n\n\n')}\n`,
    rust: `//! Generated from \`backend/zenoh_asyncapi.yaml\`. Do not edit manually.\n//!\n//! Regenerate with \`npm --prefix tools run generate\`.\n\n${routeDefinitions.map(rustPath).join('\n\n')}\n`,
  };
}

/**
 * Native-safe replacement for Zenoh TS's WASM key-expression helper.
 *
 * The Zenoh package's WASM wrapper is browser-oriented and is evaluated during
 * route discovery. Expo treats `.wasm` imports as assets on Android, so that
 * wrapper fails before the app can render. The app only sends fixed remote API
 * key expressions, so these equivalent string operations avoid loading WASM.
 */

function assertKeyExpression(value: string): void {
  if (!value || value.includes('\0')) {
    throw new Error(`Invalid Zenoh key expression: ${JSON.stringify(value)}`);
  }
}

export function new_key_expr(value: string): void {
  assertKeyExpression(value);
}

export function join(left: string, right: string): string {
  assertKeyExpression(left);
  assertKeyExpression(right);
  return `${left.replace(/\/+$/, '')}/${right.replace(/^\/+/, '')}`;
}

export function concat(left: string, right: string): string {
  assertKeyExpression(left);
  assertKeyExpression(right);
  return `${left}${right}`;
}

export function includes(left: string, right: string): boolean {
  assertKeyExpression(left);
  assertKeyExpression(right);
  return left === right || right.startsWith(`${left}/`);
}

export function intersects(left: string, right: string): boolean {
  assertKeyExpression(left);
  assertKeyExpression(right);
  return left === right || left.startsWith(`${right}/`) || right.startsWith(`${left}/`);
}

export function autocanonize(value: string): string {
  assertKeyExpression(value);
  return value.replace(/\/{2,}/g, '/').replace(/^\/+|\/+$/g, '');
}

/**
 * React Native implementation of the small LEB128 API used by Zenoh.
 *
 * @thi.ng/leb128 is WASM-backed. React Native can run WebAssembly in some
 * environments, but the package's embedded WASM module is not available in
 * the Android bundle, so its public functions throw at query serialization
 * time. Zenoh only needs these six integer encoding helpers.
 */

const MAX_BYTES = 10;

function toUnsigned64(value: bigint | number): bigint {
  return BigInt.asUintN(64, BigInt(value));
}

function toSigned64(value: bigint | number): bigint {
  return BigInt.asIntN(64, BigInt(value));
}

export function encodeULEB128(value: bigint | number): Uint8Array {
  let remaining = toUnsigned64(value);
  const bytes: number[] = [];

  do {
    let byte = Number(remaining & 0x7fn);
    remaining >>= 7n;
    if (remaining !== 0n) {
      byte |= 0x80;
    }
    bytes.push(byte);
  } while (remaining !== 0n && bytes.length < MAX_BYTES);

  return Uint8Array.from(bytes);
}

export function encodeSLEB128(value: bigint | number): Uint8Array {
  let remaining = toSigned64(value);
  const bytes: number[] = [];
  let done = false;

  while (!done && bytes.length < MAX_BYTES) {
    let byte = Number(remaining & 0x7fn);
    remaining >>= 7n;
    done =
      (remaining === 0n && (byte & 0x40) === 0) ||
      (remaining === -1n && (byte & 0x40) !== 0);
    if (!done) {
      byte |= 0x80;
    }
    bytes.push(byte);
  }

  return Uint8Array.from(bytes);
}

function writeEncoded(
  destination: Uint8Array,
  value: bigint | number,
  position: number,
  encoded: Uint8Array,
): number {
  if (!Number.isInteger(position) || position < 0 || position + encoded.length > destination.length) {
    throw new RangeError('LEB128 output does not fit in the destination');
  }

  destination.set(encoded, position);
  return encoded.length;
}

export function encodeULEB128Into(
  destination: Uint8Array,
  value: bigint | number,
  position = 0,
): number {
  return writeEncoded(destination, value, position, encodeULEB128(value));
}

export function encodeSLEB128Into(
  destination: Uint8Array,
  value: bigint | number,
  position = 0,
): number {
  return writeEncoded(destination, value, position, encodeSLEB128(value));
}

function decode(
  source: Uint8Array,
  position: number,
  signed: boolean,
): [bigint, number] {
  if (!Number.isInteger(position) || position < 0 || position >= source.length) {
    throw new RangeError('LEB128 input position is outside the source');
  }

  let value = 0n;
  let shift = 0n;
  let bytesRead = 0;
  let lastByte = 0;

  while (position + bytesRead < source.length && bytesRead < MAX_BYTES) {
    lastByte = source[position + bytesRead];
    value |= BigInt(lastByte & 0x7f) << shift;
    bytesRead += 1;

    if ((lastByte & 0x80) === 0) {
      if (signed && (lastByte & 0x40) !== 0 && shift + 7n < 64n) {
        value |= (-1n) << (shift + 7n);
      }
      return [signed ? BigInt.asIntN(64, value) : BigInt.asUintN(64, value), bytesRead];
    }

    shift += 7n;
  }

  throw new RangeError(`Invalid or truncated ${signed ? 'S' : 'U'}LEB128 value`);
}

export function decodeULEB128(source: Uint8Array, position = 0): [bigint, number] {
  return decode(source, position, false);
}

export function decodeSLEB128(source: Uint8Array, position = 0): [bigint, number] {
  return decode(source, position, true);
}

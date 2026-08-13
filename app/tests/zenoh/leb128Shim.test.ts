import { describe, expect, it } from '@jest/globals';
import {
  decodeSLEB128,
  decodeULEB128,
  encodeSLEB128,
  encodeSLEB128Into,
  encodeULEB128,
  encodeULEB128Into,
} from '@/config/leb128Shim';

describe('native Zenoh LEB128 shim', () => {
  it('encodes and decodes unsigned values', () => {
    expect(Array.from(encodeULEB128(624485))).toEqual([0xe5, 0x8e, 0x26]);
    expect(decodeULEB128(Uint8Array.from([0xe5, 0x8e, 0x26]))).toEqual([624485n, 3]);
  });

  it('encodes and decodes signed values', () => {
    expect(Array.from(encodeSLEB128(-624485))).toEqual([0x9b, 0xf1, 0x59]);
    expect(decodeSLEB128(Uint8Array.from([0x9b, 0xf1, 0x59]))).toEqual([-624485n, 3]);
  });

  it('writes encoded values into an existing buffer', () => {
    const destination = new Uint8Array(8);
    expect(encodeULEB128Into(destination, 624485, 1)).toBe(3);
    expect(Array.from(destination)).toEqual([0, 0xe5, 0x8e, 0x26, 0, 0, 0, 0]);

    expect(encodeSLEB128Into(destination, -624485)).toBe(3);
    expect(Array.from(destination.slice(0, 3))).toEqual([0x9b, 0xf1, 0x59]);
  });
});

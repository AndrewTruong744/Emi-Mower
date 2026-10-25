import { jest } from '@jest/globals';

export type { NativeSession, Sample, Cleanup } from '../../src/config/nativeZenoh';
export const open = jest.fn<(...args: any[]) => any>();

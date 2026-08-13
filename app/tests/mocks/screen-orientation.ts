export enum OrientationLock {
  PORTRAIT_UP = 1,
  LANDSCAPE = 5,
}

export const lockAsync = jest.fn(async () => undefined);
import { jest } from '@jest/globals';

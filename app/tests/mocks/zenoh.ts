import { jest } from '@jest/globals';

export class Config {
  constructor(public locator: string, public messageResponseTimeoutMs?: number) {}
}

export class ReplyError {
  constructor(private readonly message: string) {}

  payload() {
    return { toString: () => this.message };
  }
}

export const Encoding = { APPLICATION_JSON: 'application/json' };
export const Duration = {
  milliseconds: {
    of: (value: number) => ({ type: 'MILLISECONDS', valueType: 'TYPED_DURATION', value, unit: 'ms' }),
  },
};
export const open = jest.fn<(...args: any[]) => any>();

import { jest, describe, expect, it, beforeEach } from '@jest/globals';
import { Config, Encoding, ReplyError, open } from '@eclipse-zenoh/zenoh-ts';
import { useBoundStore } from '@/store/useBoundStore';
import { closeZenoh, connectZenoh, getZenohLocator, zenohQuery } from '@/zenoh/client';

const mockedOpen = open as jest.Mock<(...args: any[]) => any>;

function reply(payload: unknown) {
  return {
    result: () => ({
      payload: () => ({ toString: () => JSON.stringify(payload) }),
    }),
  };
}

describe('Zenoh client', () => {
  beforeEach(async () => {
    await closeZenoh();
    useBoundStore.getState().clearError();
    mockedOpen.mockReset();
  });

  it('connects once and sends typed JSON queries', async () => {
    const session = {
      get: jest.fn<(...args: any[]) => any>().mockImplementation(() =>
        (async function* () {
          yield reply({ ok: true });
        })()
      ),
      close: jest.fn<(...args: any[]) => any>().mockResolvedValue(undefined),
    };
    mockedOpen.mockResolvedValue(session);
    expect(getZenohLocator()).toContain('ws://');
    await expect(zenohQuery('user/login', { id_token: 'token' })).resolves.toEqual({ ok: true });
    await expect(zenohQuery('user/login', { id_token: 'token-2' })).resolves.toEqual({ ok: true });
    expect(mockedOpen).toHaveBeenCalledTimes(1);
    expect(session.get).toHaveBeenCalledWith('user/login', {
      encoding: Encoding.APPLICATION_JSON,
      payload: JSON.stringify({ id_token: 'token-2' }),
      timeout: expect.objectContaining({ value: 5_000, unit: 'ms' }),
    });
    expect(mockedOpen.mock.calls[0][0]).toBeInstanceOf(Config);
  });

  it('closes the active WebSocket session', async () => {
    const session = {
      get: jest.fn(),
      close: jest.fn<(...args: any[]) => any>().mockResolvedValue(undefined),
    };
    mockedOpen.mockResolvedValue(session);

    await connectZenoh();
    await closeZenoh();

    expect(session.close).toHaveBeenCalledTimes(1);
  });

  it('maps Zenoh errors and response edge cases', async () => {
    const errorSession = {
      get: jest.fn<(...args: any[]) => any>().mockResolvedValue(
        (async function* () {
          yield {
            result: () =>
              new (ReplyError as unknown as new (message: string) => ReplyError)('backend unavailable'),
          };
        })()
      ),
      close: jest.fn<(...args: any[]) => any>().mockResolvedValue(undefined),
    };
    mockedOpen.mockResolvedValue(errorSession);
    await expect(zenohQuery('user/login', {})).rejects.toThrow('backend unavailable');

    await closeZenoh();
    mockedOpen.mockRejectedValueOnce(new Error('connection failed'));
    await expect(connectZenoh()).rejects.toThrow('connection failed');

    const emptySession = {
      get: jest.fn<(...args: any[]) => any>().mockResolvedValue(undefined),
      close: jest.fn<(...args: any[]) => any>().mockResolvedValue(undefined),
    };
    mockedOpen.mockResolvedValueOnce(emptySession);
    await expect(zenohQuery('user/login', {})).rejects.toThrow(
      'Zenoh returned no receiver for user/login'
    );

    const blankSession = {
      get: jest.fn<(...args: any[]) => any>().mockResolvedValue(
        (async function* () {
          yield { result: () => ({ payload: () => ({ toString: () => '' }) }) };
        })()
      ),
      close: jest.fn<(...args: any[]) => any>().mockResolvedValue(undefined),
    };
    await closeZenoh();
    mockedOpen.mockResolvedValueOnce(blankSession);
    await expect(zenohQuery('user/login', {})).rejects.toThrow(
      'Zenoh returned an empty response for user/login'
    );

    const noReplySession = {
      get: jest.fn<(...args: any[]) => any>().mockResolvedValue(
        (async function* () {
          return;
        })()
      ),
      close: jest.fn<(...args: any[]) => any>().mockResolvedValue(undefined),
    };
    await closeZenoh();
    mockedOpen.mockResolvedValueOnce(noReplySession);
    await expect(zenohQuery('user/login', {})).rejects.toThrow(
      'Zenoh returned no response for user/login'
    );
    expect(useBoundStore.getState().error).toMatchObject({
      title: 'Zenoh request failed',
      message: 'Zenoh returned no response for user/login',
      source: 'zenoh',
    });
  });
});

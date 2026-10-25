import { jest, describe, expect, it, beforeEach, afterEach } from '@jest/globals';
import { open } from '@/config/nativeZenoh';
import {
  closeZenoh,
  connectZenoh,
  maintainZenohAuthorization,
  zenohPut,
  zenohSubscribe,
  zenohSubscribeLiveliness,
  zenohQuery,
} from '@/config/zenohClient';
import { OperationCancelled } from '@/errors/operationCancelled';
import { useBoundStore } from '@/store/useBoundStore';

const mockedOpen = open as jest.Mock<(...args: any[]) => any>;
const deferred = <T>() => {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
};
const settle = async () => {
  for (let i = 0; i < 30; i++) await Promise.resolve();
};
function nativeSession() {
  return {
    query: jest.fn<(...args: any[]) => Promise<string>>().mockResolvedValue('{"ok":true}'),
    put: jest.fn<(...args: any[]) => Promise<void>>().mockResolvedValue(),
    subscribe: jest
      .fn<(...args: any[]) => Promise<() => Promise<void>>>()
      .mockImplementation(async () => jest.fn<() => Promise<void>>().mockResolvedValue()),
    subscribeLiveliness: jest
      .fn<(...args: any[]) => Promise<() => Promise<void>>>()
      .mockImplementation(async () => jest.fn<() => Promise<void>>().mockResolvedValue()),
    restoreSubscriptions: jest.fn<() => Promise<void>>().mockResolvedValue(),
    close: jest.fn<() => Promise<void>>().mockResolvedValue(),
    onTransport: undefined as undefined | ((connected: boolean) => void),
  };
}

describe('Zenoh app lifecycle', () => {
  beforeEach(async () => {
    await closeZenoh();
    mockedOpen.mockReset();
    useBoundStore.getState().enableZenoh();
    useBoundStore.getState().clearErrors();
  });
  afterEach(async () => {
    await closeZenoh();
    jest.useRealTimers();
  });

  it('opens once and parses one JSON payload per query', async () => {
    const session = nativeSession();
    mockedOpen.mockResolvedValue(session);
    await expect(zenohQuery('user/login', { id_token: 'token' })).resolves.toEqual({ ok: true });
    await expect(zenohQuery('user/login', { id_token: 'token-2' })).resolves.toEqual({ ok: true });
    expect(mockedOpen).toHaveBeenCalledTimes(1);
    expect(mockedOpen).toHaveBeenCalledWith(expect.stringMatching(/^(tcp|tls)\//));
    expect(session.query).toHaveBeenLastCalledWith('user/login', '{"id_token":"token-2"}', 5000);
    expect(await connectZenoh()).toBe(session);
  });

  it('keeps overlapping replies and errors independent', async () => {
    const session = nativeSession();
    const slow = deferred<string>();
    const failed = deferred<string>();
    session.query
      .mockReturnValueOnce(slow.promise)
      .mockReturnValueOnce(failed.promise)
      .mockResolvedValueOnce('{"fast":true}');
    mockedOpen.mockResolvedValue(session);
    const first = zenohQuery('slow', {});
    const failure = expect(zenohQuery('failed', {})).rejects.toThrow('Timeout');
    await expect(zenohQuery('fast', {})).resolves.toEqual({ fast: true });
    failed.reject(new Error('Timeout'));
    await failure;
    slow.resolve('{"slow":true}');
    await expect(first).resolves.toEqual({ slow: true });
  });

  it('owns command authorization and expiry without adding native auth state', async () => {
    jest.useFakeTimers();
    const session = nativeSession();
    mockedOpen.mockResolvedValue(session);
    await expect(zenohPut('mower/A/joystick', {})).rejects.toThrow('not authorized');
    await maintainZenohAuthorization(300, jest.fn<() => Promise<void>>().mockResolvedValue());
    await zenohPut('mower/A/joystick', { x: 0.5, y: -0.25 });
    expect(session.put).toHaveBeenCalledWith('mower/A/joystick', '{"x":0.5,"y":-0.25}');
    jest.setSystemTime(Date.now() + 301000);
    await expect(zenohPut('mower/A/joystick', {})).rejects.toThrow('not authorized');
  });

  it('reauthorizes before asking Rust to replay subscriptions on the same session', async () => {
    const session = nativeSession();
    mockedOpen.mockResolvedValue(session);
    const login = deferred<void>();
    const restore = deferred<void>();
    const refresh = jest.fn(async () => {
      await login.promise;
      await maintainZenohAuthorization(300, refresh);
    });
    session.restoreSubscriptions.mockReturnValue(restore.promise);
    await maintainZenohAuthorization(300, refresh);
    session.onTransport!(false);
    await expect(zenohPut('mower/A/joystick', {})).rejects.toThrow('not authorized');
    session.onTransport!(true);
    await settle();
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(session.restoreSubscriptions).not.toHaveBeenCalled();
    login.resolve();
    await settle();
    expect(session.restoreSubscriptions).toHaveBeenCalledTimes(1);
    await expect(zenohPut('mower/A/joystick', {})).rejects.toThrow('not authorized');
    restore.resolve();
    await settle();
    await zenohPut('mower/A/joystick', {});
    expect(mockedOpen).toHaveBeenCalledTimes(1);
    expect(session.subscribe).not.toHaveBeenCalled();
  });

  it('coalesces recovery and retries authorization if the transport changes during login', async () => {
    const session = nativeSession();
    mockedOpen.mockResolvedValue(session);
    const oldLogin = deferred<void>();
    const refresh = jest
      .fn<() => Promise<void>>()
      .mockImplementationOnce(() => oldLogin.promise)
      .mockImplementation(async () => maintainZenohAuthorization(300, refresh));
    await maintainZenohAuthorization(300, refresh);
    session.onTransport!(false);
    session.onTransport!(true);
    session.onTransport!(false);
    session.onTransport!(true);
    expect(refresh).toHaveBeenCalledTimes(1);
    oldLogin.reject(new Error('old transport lost'));
    await settle();
    expect(refresh).toHaveBeenCalledTimes(2);
    expect(session.restoreSubscriptions).toHaveBeenCalledTimes(1);
    await zenohPut('mower/A/joystick', {});
  });

  it('keeps commands blocked when reconnect authorization or replay fails', async () => {
    const session = nativeSession();
    mockedOpen.mockResolvedValue(session);
    const refresh = jest
      .fn<() => Promise<void>>()
      .mockRejectedValueOnce(new Error('login failed'))
      .mockImplementation(async () => maintainZenohAuthorization(300, refresh));
    await maintainZenohAuthorization(300, refresh);
    session.onTransport!(false);
    session.onTransport!(true);
    await settle();
    expect(session.restoreSubscriptions).not.toHaveBeenCalled();
    await expect(zenohPut('mower/A/joystick', {})).rejects.toThrow('not authorized');
    session.restoreSubscriptions.mockRejectedValueOnce(new Error('replay failed'));
    session.onTransport!(false);
    session.onTransport!(true);
    await settle();
    await expect(zenohPut('mower/A/joystick', {})).rejects.toThrow('not authorized');
  });

  it('restarts authorization if the connection drops during native subscription replay', async () => {
    const session = nativeSession();
    mockedOpen.mockResolvedValue(session);
    const replay = deferred<void>();
    session.restoreSubscriptions.mockReturnValueOnce(replay.promise);
    const refresh = jest.fn(async () => maintainZenohAuthorization(300, refresh));
    await maintainZenohAuthorization(300, refresh);
    session.onTransport!(false);
    session.onTransport!(true);
    await settle();
    expect(session.restoreSubscriptions).toHaveBeenCalledTimes(1);
    session.onTransport!(false);
    session.onTransport!(true);
    replay.reject(new Error('transport lost during replay'));
    await settle();
    expect(refresh).toHaveBeenCalledTimes(2);
    expect(session.restoreSubscriptions).toHaveBeenCalledTimes(2);
    await zenohPut('mower/A/joystick', {});
  });

  it('renews at 80 percent of the authorization lifetime and closes on renewal failure', async () => {
    jest.useFakeTimers();
    const session = nativeSession();
    mockedOpen.mockResolvedValue(session);
    const refresh = jest.fn<() => Promise<void>>().mockRejectedValue(new Error('expired login'));
    await maintainZenohAuthorization(10, refresh);
    await jest.advanceTimersByTimeAsync(7999);
    expect(refresh).not.toHaveBeenCalled();
    await jest.advanceTimersByTimeAsync(1);
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(session.close).toHaveBeenCalledTimes(1);
  });

  it('maps plain telemetry and liveliness events and cleans callbacks before closing', async () => {
    const session = nativeSession();
    mockedOpen.mockResolvedValue(session);
    const onPayload = jest.fn();
    const onChange = jest.fn();
    const onClose = jest.fn();
    await zenohSubscribe('mower/*/telemetry', onPayload, onClose);
    await zenohSubscribeLiveliness('mower/*/liveliness', onChange);
    expect(session.subscribe.mock.calls[0]).toEqual(['mower/*/telemetry', expect.any(Function)]);
    expect(session.subscribeLiveliness.mock.calls[0]).toEqual([
      'mower/*/liveliness',
      expect.any(Function),
    ]);
    const telemetry = session.subscribe.mock.calls[0][1];
    const liveliness = session.subscribeLiveliness.mock.calls[0][1];
    telemetry({ key: 'mower/A/telemetry', payload: '草🌱', put: true });
    liveliness({ key: 'mower/A/liveliness', payload: '', put: true });
    liveliness({ key: 'mower/A/liveliness', payload: '', put: false });
    expect(onPayload).toHaveBeenCalledWith('草🌱');
    expect(onChange.mock.calls).toEqual([
      ['mower/A/liveliness', true],
      ['mower/A/liveliness', false],
    ]);
    await closeZenoh();
    expect(onClose).toHaveBeenCalledTimes(1);
    telemetry({ payload: 'stale' });
    expect(onPayload).toHaveBeenCalledTimes(1);
    expect(session.close).toHaveBeenCalledTimes(1);
  });

  it('waits for subscription cleanup and tolerates cleanup failures', async () => {
    const session = nativeSession();
    mockedOpen.mockResolvedValue(session);
    const undeclared = deferred<void>();
    const unsubscribe = jest.fn(() => undeclared.promise);
    session.subscribe.mockResolvedValue(unsubscribe);
    session.close.mockRejectedValue(new Error('closed'));
    await zenohSubscribe('mower/*/telemetry', jest.fn(), () => {
      throw new Error('local cleanup');
    });
    const closing = closeZenoh();
    await settle();
    expect(unsubscribe).toHaveBeenCalledTimes(1);
    expect(session.close).not.toHaveBeenCalled();
    undeclared.reject(new Error('already closed'));
    await closing;
    expect(session.close).toHaveBeenCalledTimes(1);
  });

  it('rejects disabled and stale-account operations without reporting errors', async () => {
    useBoundStore.getState().disableZenoh();
    await expect(zenohPut('mower/A/joystick', {})).rejects.toBeInstanceOf(OperationCancelled);
    expect(mockedOpen).not.toHaveBeenCalled();
    useBoundStore.getState().enableZenoh();
    const session = nativeSession();
    const reply = deferred<string>();
    session.query.mockReturnValue(reply.promise);
    mockedOpen.mockResolvedValue(session);
    const pending = zenohQuery('old', {});
    const cancelled = expect(pending).rejects.toBeInstanceOf(OperationCancelled);
    await settle();
    useBoundStore.getState().startZenohSession();
    reply.resolve('{"old":true}');
    await cancelled;
    expect(useBoundStore.getState().errorQueue).toEqual([]);
  });

  it('cleans up a subscription that finishes while its session is closing', async () => {
    const session = nativeSession();
    mockedOpen.mockResolvedValue(session);
    const declared = deferred<() => Promise<void>>();
    session.subscribe.mockReturnValueOnce(declared.promise);
    const onClose = jest.fn();
    const pending = zenohSubscribe('mower/A/telemetry', jest.fn(), onClose);
    const cancelled = expect(pending).rejects.toBeInstanceOf(OperationCancelled);
    await settle();
    await closeZenoh();
    const unsubscribe = jest.fn<() => Promise<void>>().mockResolvedValue();
    declared.resolve(unsubscribe);
    await cancelled;
    expect(unsubscribe).toHaveBeenCalledTimes(1);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('closes an open that completes after an account switch', async () => {
    const opened = deferred<ReturnType<typeof nativeSession>>();
    const session = nativeSession();
    mockedOpen.mockReturnValueOnce(opened.promise);
    const pending = connectZenoh();
    const cancelled = expect(pending).rejects.toBeInstanceOf(OperationCancelled);
    useBoundStore.getState().startZenohSession();
    opened.resolve(session);
    await cancelled;
    expect(session.close).toHaveBeenCalledTimes(1);
  });

  it('serializes replacement sessions behind the previous identity close', async () => {
    const previous = nativeSession();
    const current = nativeSession();
    const closed = deferred<void>();
    previous.close.mockReturnValue(closed.promise);
    mockedOpen.mockResolvedValueOnce(previous).mockResolvedValueOnce(current);
    await connectZenoh();
    useBoundStore.getState().startZenohSession();
    const first = connectZenoh();
    const second = connectZenoh();
    await settle();
    expect(previous.close).toHaveBeenCalledTimes(1);
    expect(mockedOpen).toHaveBeenCalledTimes(1);
    closed.resolve();
    expect(await first).toBe(current);
    expect(await second).toBe(current);
    expect(mockedOpen).toHaveBeenCalledTimes(2);
  });

  it('does not restore subscriptions after logout during reauthorization', async () => {
    const session = nativeSession();
    const login = deferred<void>();
    mockedOpen.mockResolvedValue(session);
    await maintainZenohAuthorization(300, () => login.promise);
    const transport = session.onTransport!;
    transport(false);
    transport(true);
    await closeZenoh();
    login.resolve();
    await settle();
    transport(true);
    expect(session.restoreSubscriptions).not.toHaveBeenCalled();
    expect(session.close).toHaveBeenCalledTimes(1);
  });

  it('reports query, publication and subscription errors and allows retrying an initial open', async () => {
    mockedOpen.mockRejectedValueOnce(new Error('connection failed'));
    await expect(connectZenoh()).rejects.toThrow('connection failed');
    const session = nativeSession();
    mockedOpen.mockResolvedValue(session);
    session.query
      .mockResolvedValueOnce('')
      .mockResolvedValueOnce('{')
      .mockRejectedValueOnce(new Error('backend unavailable'));
    await expect(zenohQuery('blank', {})).rejects.toThrow('empty response');
    await expect(zenohQuery('bad', {})).rejects.toThrow();
    await expect(zenohQuery('error', {})).rejects.toThrow('backend unavailable');
    await maintainZenohAuthorization(300, async () => {});
    session.put.mockRejectedValueOnce(new Error('put failed'));
    await expect(zenohPut('mower/A/joystick', {})).rejects.toThrow('put failed');
    session.subscribe.mockRejectedValueOnce(new Error('subscribe failed'));
    await expect(zenohSubscribe('mower/*/telemetry', jest.fn())).rejects.toThrow(
      'subscribe failed'
    );
    expect(useBoundStore.getState().errorQueue.map((e) => e.code)).toEqual(
      expect.arrayContaining([
        'zenoh.request_failed',
        'zenoh.command_failed',
        'zenoh.subscription_failed',
      ])
    );
  });
});

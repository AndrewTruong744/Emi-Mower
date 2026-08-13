import { beforeEach, describe, expect, it, jest } from '@jest/globals';
import { getFirebaseIdToken, loginUserAndStore, userLogin } from '@/zenoh/UserLogin';
import { mockFirebaseAuth, mockFirebaseUser } from '../mocks/firebase';
import { closeZenoh } from '@/config/zenohClient';
import { open } from '@eclipse-zenoh/zenoh-ts';

const mockedOpen = open as jest.Mock<(...args: any[]) => any>;

function loginReply() {
  return {
    result: () => ({
      payload: () => ({
        toString: () =>
          JSON.stringify({
            user_id: 'user-1',
            token: 'zenoh-token',
            expires_in: 300,
            user_data: { id: 'user-1', email: 'u@example.com', name: 'U', mowers: ['mower-1'] },
          }),
      }),
    }),
  };
}

describe('UserLogin', () => {
  beforeEach(async () => {
    await closeZenoh();
    mockedOpen.mockReset();
  });

  it('calls the login route and stores returned user data', async () => {
    const session = {
      get: jest.fn<(...args: any[]) => any>().mockImplementation(() =>
        (async function* () {
          yield loginReply();
        })()
      ),
      close: jest.fn<(...args: any[]) => any>().mockResolvedValue(undefined),
    };
    mockedOpen.mockResolvedValue(session);
    const setUser = jest.fn();
    const setMowers = jest.fn();

    await expect(userLogin('firebase-token')).resolves.toMatchObject({ user_id: 'user-1' });
    await loginUserAndStore('firebase-token', setUser, setMowers);
    expect(session.get).toHaveBeenCalledWith(
      'user/login',
      expect.objectContaining({ payload: expect.any(String) })
    );
    expect(setUser).toHaveBeenCalledWith({
      user_id: 'user-1',
      email: 'u@example.com',
      displayName: 'U',
    });
    expect(setMowers).toHaveBeenCalledWith(['mower-1']);
    expect(mockedOpen).toHaveBeenCalledTimes(2);
    expect(mockedOpen.mock.calls[1][0].locator).toContain('user-1:zenoh-token@');
    await loginUserAndStore('firebase-token', setUser);
  });

  it('validates Firebase login inputs and retrieves Firebase tokens', async () => {
    await expect(userLogin('')).rejects.toThrow('A Firebase ID token is required to log in');
    mockFirebaseAuth.currentUser = null;
    await expect(getFirebaseIdToken()).rejects.toThrow('No authenticated Firebase user found');
    mockFirebaseAuth.currentUser = mockFirebaseUser;
    await expect(getFirebaseIdToken()).resolves.toBe('firebase-token');
  });

  it('shares an in-flight login between the Firebase listener and login screen', async () => {
    let releaseReply!: () => void;
    const replyReady = new Promise<void>((resolve) => {
      releaseReply = resolve;
    });
    const session = {
      get: jest.fn<(...args: any[]) => any>().mockImplementation(() =>
        (async function* () {
          await replyReady;
          yield loginReply();
        })()
      ),
      close: jest.fn<(...args: any[]) => any>().mockResolvedValue(undefined),
    };
    mockedOpen.mockResolvedValue(session);
    const firstSetUser = jest.fn();
    const secondSetUser = jest.fn();

    const firstLogin = loginUserAndStore('firebase-token', firstSetUser);
    const secondLogin = loginUserAndStore('firebase-token', secondSetUser);
    releaseReply();
    await expect(Promise.all([firstLogin, secondLogin])).resolves.toHaveLength(2);
    expect(session.get).toHaveBeenCalledTimes(1);
    expect(firstSetUser).toHaveBeenCalledTimes(1);
    expect(secondSetUser).not.toHaveBeenCalled();
  });
});

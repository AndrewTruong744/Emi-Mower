import { beforeEach, describe, expect, it, jest } from '@jest/globals';
import { loginUser } from '@/zenoh/UserLogin';
import { getFirebaseIdToken } from '@/config/firebase';
import { mockFirebaseAuth, mockFirebaseUser } from '../mocks/firebase';
import { closeZenoh } from '@/config/zenohClient';
import { open } from '@eclipse-zenoh/zenoh-ts';
import { useBoundStore } from '@/store/useBoundStore';

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
    useBoundStore.getState().enableZenoh();
  });

  it('calls the login route and establishes the returned user Zenoh session', async () => {
    const session = {
      get: jest.fn<(...args: any[]) => any>().mockImplementation(() =>
        (async function* () {
          yield loginReply();
        })()
      ),
      close: jest.fn<(...args: any[]) => any>().mockResolvedValue(undefined),
    };
    mockedOpen.mockResolvedValue(session);
    await expect(loginUser()).resolves.toMatchObject({
      id: 'user-1',
      email: 'u@example.com',
      name: 'U',
      mowers: ['mower-1'],
    });
    expect(session.get).toHaveBeenCalledWith(
      'user/login',
      expect.objectContaining({ payload: expect.any(String) })
    );
    expect(mockedOpen).toHaveBeenCalledTimes(2);
    expect(mockedOpen.mock.calls[1][0].locator).toContain('user-1:zenoh-token@');
  });

  it('validates Firebase login inputs and retrieves Firebase tokens', async () => {
    mockFirebaseAuth.currentUser = null;
    await expect(loginUser()).rejects.toThrow('No authenticated Firebase user found');
    await expect(getFirebaseIdToken()).rejects.toThrow('No authenticated Firebase user found');
    mockFirebaseAuth.currentUser = mockFirebaseUser;
    await expect(getFirebaseIdToken()).resolves.toBe('firebase-token');
  });

});

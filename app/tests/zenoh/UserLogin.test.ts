import { beforeEach, describe, expect, it, jest } from '@jest/globals';
import { loginUser } from '@/zenoh/UserLogin';
import { getFirebaseIdToken } from '@/config/firebase';
import { mockFirebaseAuth, mockFirebaseUser } from '../mocks/firebase';
import { closeZenoh } from '@/config/zenohClient';
import { open } from '@/config/nativeZenoh';
import { useBoundStore } from '@/store/useBoundStore';

const mockedOpen = open as jest.Mock<(...args: any[]) => any>;

function loginReply() {
  return JSON.stringify({
    user_id: 'user-1',
    authorized: true,
    expires_in: 300,
    user_data: { id: 'user-1', email: 'u@example.com', name: 'U', mowers: ['mower-1'] },
  });
}

describe('UserLogin', () => {
  beforeEach(async () => {
    await closeZenoh();
    mockedOpen.mockReset();
    useBoundStore.getState().enableZenoh();
  });

  it('calls the login route and establishes the returned user Zenoh session', async () => {
    const session = {
      query: jest.fn<(...args: any[]) => any>().mockResolvedValue(loginReply()),
      close: jest.fn<(...args: any[]) => any>().mockResolvedValue(undefined),
    };
    mockedOpen.mockResolvedValue(session);
    await expect(loginUser()).resolves.toMatchObject({
      id: 'user-1',
      email: 'u@example.com',
      name: 'U',
      mowers: ['mower-1'],
    });
    expect(session.query).toHaveBeenCalledWith(
      'user/login',
      JSON.stringify({ id_token: 'firebase-token' }),
      5000
    );
    expect(mockedOpen).toHaveBeenCalledTimes(1);
    expect(session.close).not.toHaveBeenCalled();
  });

  it('validates Firebase login inputs and retrieves Firebase tokens', async () => {
    mockFirebaseAuth.currentUser = null;
    await expect(loginUser()).rejects.toThrow('No authenticated Firebase user found');
    await expect(getFirebaseIdToken()).rejects.toThrow('No authenticated Firebase user found');
    mockFirebaseAuth.currentUser = mockFirebaseUser;
    await expect(getFirebaseIdToken()).resolves.toBe('firebase-token');
  });

  it('does not reuse a pending login when Firebase identity changes', async () => {
    let signalStarted!: () => void;
    let finishOldQuery!: (value: any) => void;
    const started = new Promise<void>((resolve) => {
      signalStarted = resolve;
    });
    const pending = new Promise<any>((resolve) => {
      finishOldQuery = resolve;
    });
    const old = {
      query: jest.fn(() => {
        signalStarted();
        return pending;
      }),
      close: jest.fn<() => Promise<void>>().mockResolvedValue(),
    };
    const replacement = {
      query: jest.fn(async () => loginReply()),
      close: jest.fn<() => Promise<void>>().mockResolvedValue(),
    };
    mockedOpen.mockResolvedValueOnce(old).mockResolvedValueOnce(replacement);
    const previous = loginUser().catch((error) => error);
    await started;
    useBoundStore.getState().startZenohSession();
    await expect(loginUser()).resolves.toMatchObject({ id: 'user-1' });
    finishOldQuery(loginReply());
    expect((await previous).name).toBe('OperationCancelled');
    expect(mockedOpen).toHaveBeenCalledTimes(2);
  });
});

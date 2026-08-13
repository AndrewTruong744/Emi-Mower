import { firebaseAuth } from '@/config/firebase';
import type { UserLoginResponse } from '@/generated/zenoh';
import { assertAuthSessionCurrent, getAuthSessionVersion } from '@/auth/session';
import { connectZenoh, zenohQuery } from '@/config/zenohClient';

export const USER_LOGIN_KEY = 'user/login';
export const UPDATE_USER_EMAIL_KEY = 'user/update_email';
export const UPDATE_USER_NAME_KEY = 'user/update_name';

type SetUser = (user: {
  user_id: string;
  email: string;
  displayName: string;
}) => void;
type SetMowers = (mowers: string[]) => void;
type StoredLogin = UserLoginResponse['user_data'];

let inFlightLogin:
  | { authSessionVersion: number; promise: Promise<StoredLogin> }
  | null = null;

export async function userLogin(idToken: string): Promise<UserLoginResponse> {
  if (!idToken) {
    throw new Error('A Firebase ID token is required to log in');
  }

  return zenohQuery<UserLoginResponse>(USER_LOGIN_KEY, { id_token: idToken });
}

export async function getFirebaseIdToken(forceRefresh = false): Promise<string> {
  const user = firebaseAuth.currentUser;
  if (!user) {
    throw new Error('No authenticated Firebase user found');
  }

  return user.getIdToken(forceRefresh);
}

export async function loginUserAndStore(
  idToken: string,
  setUser: SetUser,
  setMowers?: SetMowers
): Promise<StoredLogin> {
  const authSessionVersion = getAuthSessionVersion();
  if (inFlightLogin?.authSessionVersion === authSessionVersion) {
    return inFlightLogin.promise;
  }

  const promise = (async (): Promise<StoredLogin> => {
    const response = await userLogin(idToken);
    assertAuthSessionCurrent(authSessionVersion);
    setUser({
      user_id: response.user_data.id,
      email: response.user_data.email,
      displayName: response.user_data.name,
    });
    const mowers = Array.isArray(response.user_data.mowers)
      ? response.user_data.mowers.filter((mower): mower is string => typeof mower === 'string')
      : [];
    setMowers?.(mowers);

    // user/login is intentionally reachable by the guest session. Replace it
    // immediately with the user-scoped session so mower routes use the ACL
    // provisioned for this username and one-time Zenoh password.
    await connectZenoh(response.user_id, response.token, () =>
      assertAuthSessionCurrent(authSessionVersion)
    );
    assertAuthSessionCurrent(authSessionVersion);
    return response.user_data;
  })();

  inFlightLogin = { authSessionVersion, promise };
  try {
    return await promise;
  } finally {
    if (inFlightLogin?.promise === promise) {
      inFlightLogin = null;
    }
  }
}

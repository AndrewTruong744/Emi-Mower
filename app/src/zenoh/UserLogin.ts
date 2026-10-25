import { getFirebaseIdToken } from '@/config/firebase';
import { useBoundStore } from '@/store/useBoundStore';
import type { UserLoginRequest, UserLoginResponse } from '@/generated/zenoh';
import { userLoginPath } from '@/generated/zenohPaths';
import { zenohQuery, maintainZenohAuthorization } from '@/config/zenohClient';

/** Authenticate the current Firebase user and establish its scoped Zenoh session. */
async function authenticateUser(): Promise<UserLoginResponse['user_data']> {
  const idToken = await getFirebaseIdToken();
  const request: UserLoginRequest = { id_token: idToken };
  const response = await zenohQuery<UserLoginResponse>(userLoginPath(), request);
  if (!response.authorized) throw new Error('Router did not authorize the current connection');
  await maintainZenohAuthorization(response.expires_in, loginUser);
  return {
    ...response.user_data,
    mowers: Array.isArray(response.user_data.mowers)
      ? response.user_data.mowers.filter((mower): mower is string => typeof mower === 'string')
      : [],
  };
}

let pendingLogin:
  { generation: number; promise: Promise<UserLoginResponse['user_data']> } | undefined;
/** Coalesce within one identity; a replacement Google account gets its own login. */
export function loginUser(): Promise<UserLoginResponse['user_data']> {
  const generation = useBoundStore.getState().authGeneration;
  if (pendingLogin?.generation === generation) return pendingLogin.promise;
  const promise = authenticateUser().finally(() => {
    if (pendingLogin?.promise === promise) pendingLogin = undefined;
  });
  pendingLogin = { generation, promise };
  return promise;
}

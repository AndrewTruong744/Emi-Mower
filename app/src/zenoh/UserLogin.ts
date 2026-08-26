import { getFirebaseIdToken } from '@/config/firebase';
import type { UserLoginResponse } from '@/generated/zenoh';
import { userLoginPath } from '@/generated/zenohPaths';
import { connectZenoh, zenohQuery } from '@/config/zenohClient';

/** Authenticate the current Firebase user and establish its scoped Zenoh session. */
export async function loginUser(): Promise<UserLoginResponse['user_data']> {
  const idToken = await getFirebaseIdToken();
  const response = await zenohQuery<UserLoginResponse>(userLoginPath(), { id_token: idToken });
  // user/login is intentionally reachable by the guest session. Replace it
  // immediately with the user-scoped session so mower routes use the ACL
  // provisioned for this username and one-time Zenoh password.
  await connectZenoh(response.user_id, response.token);
  return {
    ...response.user_data,
    mowers: Array.isArray(response.user_data.mowers)
      ? response.user_data.mowers.filter((mower): mower is string => typeof mower === 'string')
      : [],
  };
}

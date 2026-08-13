import { useMutation } from '@tanstack/react-query';
import { UpdateUserNameResponse } from '@/generated/zenoh';
import { getFirebaseIdToken, UPDATE_USER_NAME_KEY } from '@/zenoh/UserLogin';
import { zenohQuery } from '@/config/zenohClient';

interface PatchUsernameParams {
  userId?: string;
  newUserName: string;
}

export const usePatchUsername = () => {
  return useMutation({
    mutationFn: async ({ newUserName }: PatchUsernameParams) => {
      const idToken = await getFirebaseIdToken(true);
      return zenohQuery<UpdateUserNameResponse>(UPDATE_USER_NAME_KEY, {
        id_token: idToken,
        new_user_name: newUserName,
      });
    },
  });
};

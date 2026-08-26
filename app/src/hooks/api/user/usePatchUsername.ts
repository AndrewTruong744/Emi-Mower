import { useMutation } from '@tanstack/react-query';
import { UpdateUserNameResponse } from '@/generated/zenoh';
import { updateUserNamePath } from '@/generated/zenohPaths';
import { getFirebaseIdToken } from '@/config/firebase';
import { zenohQuery } from '@/config/zenohClient';

interface PatchUsernameParams {
  userId?: string;
  newUserName: string;
}

export const usePatchUsername = () => {
  return useMutation({
    mutationFn: async ({ newUserName }: PatchUsernameParams) => {
      const idToken = await getFirebaseIdToken(true);
      return zenohQuery<UpdateUserNameResponse>(updateUserNamePath(), {
        id_token: idToken,
        new_user_name: newUserName,
      });
    },
    retry: false,
    gcTime: 0,
  });
};

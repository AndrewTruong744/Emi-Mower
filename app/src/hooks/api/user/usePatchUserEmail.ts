import { useMutation } from '@tanstack/react-query';
import { updateEmail } from '@react-native-firebase/auth';
import { firebaseAuth, getFirebaseIdToken } from '@/config/firebase';
import type { UpdateUserEmailRequest, UpdateUserEmailResponse } from '@/generated/zenoh';
import { updateUserEmailPath } from '@/generated/zenohPaths';
import { zenohQuery } from '@/config/zenohClient';

interface PatchUserEmailParams {
  newIdToken: string;
  newEmail: string;
}

export const usePatchUserEmail = () => {
  return useMutation({
    mutationFn: async ({ newIdToken, newEmail }: PatchUserEmailParams) => {
      const firebaseUser = firebaseAuth.currentUser;
      if (!firebaseUser) {
        throw new Error('No authenticated Firebase user found');
      }
      if (!newEmail) {
        throw new Error('A new email address is required');
      }

      await updateEmail(firebaseUser, newEmail);
      const idToken = await getFirebaseIdToken(true);
      const request: UpdateUserEmailRequest = {
        id_token: idToken,
        new_id_token: newIdToken,
      };
      return zenohQuery<UpdateUserEmailResponse>(updateUserEmailPath(), request);
    },
    retry: false,
    gcTime: 0,
  });
};

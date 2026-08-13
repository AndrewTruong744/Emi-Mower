import { useMutation } from '@tanstack/react-query';
import { updateEmail } from '@react-native-firebase/auth';
import { firebaseAuth } from '@/config/firebase';
import { UpdateUserEmailResponse } from '@/generated/zenoh';
import { getFirebaseIdToken, UPDATE_USER_EMAIL_KEY } from '@/zenoh/UserLogin';
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
      return zenohQuery<UpdateUserEmailResponse>(UPDATE_USER_EMAIL_KEY, {
        id_token: idToken,
        new_id_token: newIdToken,
      });
    },
  });
};

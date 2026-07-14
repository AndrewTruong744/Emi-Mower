import { useMutation } from '@tanstack/react-query';
import { patchUserEmail } from '@/api/user';

interface PatchUserEmailParams {
  userId: string;
  newIdToken: string;
}

export const usePatchUserEmail = () => {
  return useMutation({
    mutationFn: ({ userId, newIdToken }: PatchUserEmailParams) =>
      patchUserEmail(userId, newIdToken),
  });
};

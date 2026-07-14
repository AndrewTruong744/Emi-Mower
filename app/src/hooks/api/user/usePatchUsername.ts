import { useMutation } from '@tanstack/react-query';
import { patchUsername } from '@/api/user';

interface PatchUsernameParams {
  userId: string;
  newUserName: string;
}

export const usePatchUsername = () => {
  return useMutation({
    mutationFn: ({ userId, newUserName }: PatchUsernameParams) =>
      patchUsername(userId, newUserName),
  });
};

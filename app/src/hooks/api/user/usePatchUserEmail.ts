import { useMutation } from '@tanstack/react-query';
import type { UpdateUserEmailRequest, UpdateUserEmailResponse } from '@/generated/zenoh';
import { updateUserEmailPath } from '@/generated/zenohPaths';
import { zenohQuery } from '@/config/zenohClient';

interface PatchUserEmailParams {
  originalIdToken: string;
  newIdToken: string;
}

export const usePatchUserEmail = () =>
  useMutation({
    mutationFn: async ({ originalIdToken, newIdToken }: PatchUserEmailParams) => {
      if (!originalIdToken || !newIdToken)
        throw new Error('Both Google accounts must be authenticated.');
      const request: UpdateUserEmailRequest = {
        id_token: originalIdToken,
        new_id_token: newIdToken,
      };
      return zenohQuery<UpdateUserEmailResponse>(updateUserEmailPath(), request);
    },
    retry: false,
    gcTime: 0,
  });

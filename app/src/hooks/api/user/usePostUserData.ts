import { useMutation } from '@tanstack/react-query';
import { postUserData } from '@/api/user';

export const usePostUserData = () => {
  return useMutation({
    mutationFn: (userId: string) => postUserData(userId),
  });
};

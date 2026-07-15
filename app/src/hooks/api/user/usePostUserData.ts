import { useMutation } from '@tanstack/react-query';
import { postUserData } from '@/api/user';

export const usePostUserData = () => {
  return useMutation({
    mutationFn: (userId: string) => {
      console.log('usePostUserData mutationFn executing for userId:', userId);
      return postUserData(userId);
    },
  });
};

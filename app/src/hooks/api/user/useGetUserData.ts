import { useQuery } from '@tanstack/react-query';
import { getUserData } from '@/api/user';

export const useGetUserData = (userId: string | null) => {
  console.log('useGetUserData hook called with userId:', userId, 'enabled:', !!userId);
  return useQuery({
    queryKey: ['userData', userId],
    queryFn: () => {
      console.log('useGetUserData queryFn executing for userId:', userId);
      return getUserData(userId!);
    },
    enabled: !!userId,
    retry: false,
  });
};

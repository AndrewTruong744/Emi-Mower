import { useQuery } from '@tanstack/react-query';
import { getUserData } from '@/api/user';

export const useGetUserData = (userId: string | null) => {
  return useQuery({
    queryKey: ['userData', userId],
    queryFn: () => getUserData(userId!),
    enabled: !!userId,
    retry: false,
  });
};

import { useEffect } from 'react';
import { useRouter, useSegments } from 'expo-router';
import type { AuthStatus } from '@/store/types';

/** Keep navigation in the route group appropriate for the auth lifecycle. */
export function useAuthRouteRedirect(authStatus: AuthStatus): void {
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (
      authStatus === 'initializing' ||
      authStatus === 'authenticating' ||
      authStatus === 'signingOut'
    ) {
      return;
    }

    const inAuthGroup = segments[0] === '(auth)';
    if (authStatus !== 'authenticated') {
      if (!inAuthGroup) router.replace('/(auth)/login' as any);
      return;
    }

    if (inAuthGroup) {
      router.replace('/(tabs)/home' as any);
    }
  }, [authStatus, segments, router]);
}

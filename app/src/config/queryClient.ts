import { QueryClient } from '@tanstack/react-query';

/** Shared client for request lifecycle state and any future server-read queries. */
export const queryClient = new QueryClient({
  defaultOptions: {
    mutations: {
      retry: false,
      gcTime: 0,
    },
    queries: {
      retry: false,
    },
  },
});

/** Prevent data or request state from one authenticated session reaching another. */
export function clearAuthenticatedQueryCache(): void {
  queryClient.clear();
}

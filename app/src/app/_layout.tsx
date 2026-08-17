import { DarkTheme, DefaultTheme, ThemeProvider } from '@react-navigation/native';
import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import 'react-native-reanimated';
import { SafeAreaView, SafeAreaProvider } from 'react-native-safe-area-context';
import { StyleSheet, View, useColorScheme as useNativeColorScheme } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { PaperProvider, ActivityIndicator } from 'react-native-paper';
import { APP_SAFE_AREA_EDGES } from '@/constants/layout';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { useBoundStore } from '@/store/useBoundStore';
import { firebaseAuth } from '@/config/firebase';
import { onAuthStateChanged } from '@react-native-firebase/auth';
import { loginUserAndStore } from '@/zenoh/UserLogin';
import {
  getAuthSessionVersion,
  invalidateAuthSession,
  isAuthOperationCancelled,
  isAuthSessionCurrent,
} from '@/auth/session';
import { cancelZenohOperations, closeZenoh, isZenohOperationCancelled } from '@/config/zenohClient';
import { useMowerTelemetrySubscription } from '@/hooks/api/mower/useMowerTelemetrySubscription';

// Create a single client instance outside the component scope to keep it stable
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2, // Auto-retry failed requests twice before displaying error
      staleTime: 1000 * 60 * 5, // Consider data fresh for 5 minutes
      refetchOnWindowFocus: true, // Refetch when user returns to the app
      networkMode: 'always',
    },
    mutations: {
      networkMode: 'always',
    },
  },
});

export const unstable_settings = {
  anchor: '(tabs)',
};

function RootLayoutNav() {
  useMowerTelemetrySubscription();
  const systemColorScheme = useNativeColorScheme();
  const themePreference = useBoundStore((state) => state.themePreference);
  const colorScheme =
    themePreference === 'system' ? (systemColorScheme ?? 'light') : themePreference;
  const segments = useSegments();
  const router = useRouter();
  const idToken = useBoundStore((state) => state.idToken);
  const setAuthToken = useBoundStore((state) => state.setAuthToken);
  const setUser = useBoundStore((state) => state.setUser);
  const setMowers = useBoundStore((state) => state.setMowers);
  const clearAuth = useBoundStore((state) => state.clearAuth);
  const clearUser = useBoundStore((state) => state.clearUser);
  const clearMowers = useBoundStore((state) => state.clearMowers);
  const resetStore = useBoundStore((state) => state.resetStore);
  const reportError = useBoundStore((state) => state.reportError);

  const [isInitializing, setIsInitializing] = useState(true);

  // Sync Firebase auth state with Zustand store
  useEffect(() => {
    let unsubscribe: (() => void) | undefined;
    try {
      unsubscribe = onAuthStateChanged(firebaseAuth, async (firebaseUser) => {
        if (!firebaseUser) {
          // Firebase can emit the sign-out event independently of the logout
          // button. Invalidate any login callback that is still in flight.
          invalidateAuthSession();
          cancelZenohOperations();
          await closeZenoh();
          resetStore();
          setIsInitializing(false);
          return;
        }

        const authSessionVersion = getAuthSessionVersion();
        try {
          const token = await firebaseUser.getIdToken();
          if (!isAuthSessionCurrent(authSessionVersion)) return;
          setAuthToken(token);
          await loginUserAndStore(token, setUser, setMowers);
          if (!isAuthSessionCurrent(authSessionVersion)) return;
        } catch (error) {
          if (
            !isAuthSessionCurrent(authSessionVersion) ||
            isAuthOperationCancelled(error) ||
            isZenohOperationCancelled(error)
          ) {
            return;
          }
          console.error('Error fetching Firebase ID token:', error);
          reportError(error, { source: 'auth', title: 'Authentication failed' });
          clearAuth();
          clearUser();
          clearMowers();
        }
        if (isAuthSessionCurrent(authSessionVersion)) setIsInitializing(false);
      });
    } catch (error) {
      console.error('Firebase Auth is not initialized or failed to start:', error);
      setIsInitializing(false);
    }

    return () => {
      if (unsubscribe) {
        unsubscribe();
      }
    };
  }, [
    setAuthToken,
    setUser,
    setMowers,
    clearAuth,
    clearUser,
    clearMowers,
    resetStore,
    reportError,
  ]);

  // Protected routes handler
  useEffect(() => {
    if (isInitializing) return;

    const segs = segments as string[];
    const inAuthGroup = segs[0] === '(auth)';

    if (!idToken) {
      // If not logged in and not in the auth group, send to login
      if (!inAuthGroup) {
        router.replace('/(auth)/login' as any);
      }
    } else {
      // If logged in and in the auth group, send to tabs home
      if (inAuthGroup || segs.length === 0) {
        router.replace('/(tabs)/home' as any);
      }
    }
  }, [idToken, segments, isInitializing, router]);

  if (isInitializing) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#4CAF50" />
      </View>
    );
  }

  return (
    <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
      <Stack>
        <Stack.Screen name="(auth)" options={{ headerShown: false }} />
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      </Stack>
    </ThemeProvider>
  );
}

export default function RootLayout() {
  return (
    <PaperProvider>
      <SafeAreaProvider>
        <SafeAreaView style={styles.container} edges={APP_SAFE_AREA_EDGES}>
          <QueryClientProvider client={queryClient}>
            <GestureHandlerRootView>
              <RootLayoutNav />
            </GestureHandlerRootView>
          </QueryClientProvider>
          <StatusBar style="auto" />
        </SafeAreaView>
      </SafeAreaProvider>
    </PaperProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: 'transparent',
  },
  loadingContainer: {
    flex: 1,
    backgroundColor: '#121212',
    justifyContent: 'center',
    alignItems: 'center',
  },
});

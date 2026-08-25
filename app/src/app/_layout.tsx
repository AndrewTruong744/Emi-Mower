import { DarkTheme, DefaultTheme, ThemeProvider } from '@react-navigation/native';
import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import 'react-native-reanimated';
import { SafeAreaView, SafeAreaProvider } from 'react-native-safe-area-context';
import { StyleSheet, View, useColorScheme as useNativeColorScheme } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { PaperProvider, ActivityIndicator } from 'react-native-paper';
import { QueryClientProvider } from '@tanstack/react-query';
import { APP_SAFE_AREA_EDGES } from '@/constants/layout';

import { useEffect } from 'react';
import { useBoundStore } from '@/store/useBoundStore';
import { firebaseAuth } from '@/config/firebase';
import { onAuthStateChanged } from '@react-native-firebase/auth';
import { loginUserAndStore } from '@/zenoh/UserLogin';
import { closeZenoh } from '@/config/zenohClient';
import { initializeMowerTelemetrySubscription } from '@/zenoh/mowerTelemetrySubscription';
import { GlobalErrorHost } from '@/errors/GlobalErrorHost';
import { isOperationCancelled } from '@/errors/operationCancelled';
import { reportAppError } from '@/errors/reporter';
import { clearAuthenticatedQueryCache, queryClient } from '@/config/queryClient';

export const unstable_settings = {
  anchor: '(tabs)',
};

function isCurrentAuthAttempt(userId: string, generation: number): boolean {
  const { zenohEnabled, authGeneration } = useBoundStore.getState();
  return firebaseAuth.currentUser?.uid === userId && zenohEnabled && authGeneration === generation;
}

function RootLayoutNav() {
  const systemColorScheme = useNativeColorScheme();
  const themePreference = useBoundStore((state) => state.themePreference);
  const colorScheme =
    themePreference === 'system' ? (systemColorScheme ?? 'light') : themePreference;
  const segments = useSegments();
  const router = useRouter();
  const authStatus = useBoundStore((state) => state.authStatus);
  const setAuthToken = useBoundStore((state) => state.setAuthToken);
  const setUser = useBoundStore((state) => state.setUser);
  const setMowers = useBoundStore((state) => state.setMowers);
  const setAuthStatus = useBoundStore((state) => state.setAuthStatus);
  const startZenohSession = useBoundStore((state) => state.startZenohSession);
  const resetStore = useBoundStore((state) => state.resetStore);

  // Firebase owns identity; an authenticated route requires the matching Zenoh
  // session to be established before this listener marks the app authenticated.
  useEffect(() => {
    let unsubscribe: (() => void) | undefined;
    setAuthStatus('initializing');
    try {
      unsubscribe = onAuthStateChanged(firebaseAuth, async (firebaseUser) => {
        if (!firebaseUser) {
          clearAuthenticatedQueryCache();

          // Explicit logout owns this barrier so login is not exposed until
          // every subscriber and the previous session have been torn down.
          if (useBoundStore.getState().authStatus === 'signingOut') return;

          setAuthStatus('signingOut');
          await closeZenoh();
          resetStore();
          return;
        }

        // A restored or different Firebase identity must never receive the
        // previous session's server data or mutation state.
        clearAuthenticatedQueryCache();
        startZenohSession();
        const authGeneration = useBoundStore.getState().authGeneration;
        setAuthStatus('authenticating');
        try {
          const token = await firebaseUser.getIdToken();
          if (!isCurrentAuthAttempt(firebaseUser.uid, authGeneration)) return;
          await loginUserAndStore(token, setUser, setMowers);
          if (!isCurrentAuthAttempt(firebaseUser.uid, authGeneration)) return;
          await initializeMowerTelemetrySubscription(authGeneration);
          if (!isCurrentAuthAttempt(firebaseUser.uid, authGeneration)) return;
          setAuthToken(token);
          setAuthStatus('authenticated');
        } catch (error) {
          if (
            !isCurrentAuthAttempt(firebaseUser.uid, authGeneration) ||
            isOperationCancelled(error)
          ) {
            return;
          }
          console.error('Error fetching Firebase ID token:', error);
          await closeZenoh();
          resetStore();
          reportAppError('auth.sign_in_failed', error);
        }
      });
    } catch (error) {
      console.error('Firebase Auth is not initialized or failed to start:', error);
      reportAppError('auth.session_failed', error);
      setAuthStatus('signedOut');
    }

    return () => {
      if (unsubscribe) {
        unsubscribe();
      }
    };
  }, [setAuthToken, setUser, setMowers, setAuthStatus, startZenohSession, resetStore]);

  // Protected routes handler
  useEffect(() => {
    if (
      authStatus === 'initializing' ||
      authStatus === 'authenticating' ||
      authStatus === 'signingOut'
    ) {
      return;
    }

    const segs = segments as string[];
    const inAuthGroup = segs[0] === '(auth)';

    if (authStatus !== 'authenticated') {
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
  }, [authStatus, segments, router]);

  if (
    authStatus === 'initializing' ||
    authStatus === 'authenticating' ||
    authStatus === 'signingOut'
  ) {
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
      <QueryClientProvider client={queryClient}>
        <SafeAreaProvider>
          <SafeAreaView style={styles.container} edges={APP_SAFE_AREA_EDGES}>
            <GestureHandlerRootView>
              <RootLayoutNav />
              <GlobalErrorHost />
            </GestureHandlerRootView>
            <StatusBar style="auto" />
          </SafeAreaView>
        </SafeAreaProvider>
      </QueryClientProvider>
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

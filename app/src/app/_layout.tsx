import { DarkTheme, DefaultTheme, ThemeProvider } from '@react-navigation/native';
import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import 'react-native-reanimated';
import { SafeAreaView, SafeAreaProvider } from 'react-native-safe-area-context';
import { StyleSheet, View } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { PaperProvider, ActivityIndicator } from 'react-native-paper';
import '../../global.css';

import { useColorScheme } from '@/hooks/use-color-scheme';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { useBoundStore } from '@/store/useBoundStore';
import { auth } from '@/config/firebase';

// Create a single client instance outside the component scope to keep it stable
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2, // Auto-retry failed requests twice before displaying error
      staleTime: 1000 * 60 * 5, // Consider data fresh for 5 minutes
      refetchOnWindowFocus: true, // Refetch when user returns to the app
    },
  },
});

export const unstable_settings = {
  anchor: '(tabs)',
};

function RootLayoutNav() {
  const colorScheme = useColorScheme();
  const segments = useSegments();
  const router = useRouter();
  const idToken = useBoundStore((state) => state.idToken);
  const setAuthTokens = useBoundStore((state) => state.setAuthTokens);
  const setUser = useBoundStore((state) => state.setUser);
  const clearAuth = useBoundStore((state) => state.clearAuth);
  const clearUser = useBoundStore((state) => state.clearUser);

  const [isInitializing, setIsInitializing] = useState(true);

  // Sync Firebase auth state with Zustand store
  useEffect(() => {
    let unsubscribe: (() => void) | undefined;
    try {
      unsubscribe = auth().onAuthStateChanged(async (firebaseUser) => {
        if (firebaseUser) {
          try {
            const token = await firebaseUser.getIdToken();
            setAuthTokens(token, 'firebase-handled');
            setUser({
              user_id: firebaseUser.uid,
              email: firebaseUser.email,
              displayName: firebaseUser.displayName,
            });
          } catch (error) {
            console.error('Error fetching Firebase ID token:', error);
            clearAuth();
            clearUser();
          }
        } else {
          clearAuth();
          clearUser();
        }
        setIsInitializing(false);
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
  }, [setAuthTokens, setUser, clearAuth, clearUser]);

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
        router.replace('/(tabs)' as any);
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
        <Stack.Screen name="modal" options={{ presentation: 'modal', title: 'Modal' }} />
      </Stack>
    </ThemeProvider>
  );
}

export default function RootLayout() {
  return (
    <PaperProvider>
      <SafeAreaProvider>
        <SafeAreaView style={styles.container} edges={['top', 'bottom', 'left', 'right']}>
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
    backgroundColor: 'black', // The color that will fill the status bar area
  },
  loadingContainer: {
    flex: 1,
    backgroundColor: '#121212',
    justifyContent: 'center',
    alignItems: 'center',
  },
});

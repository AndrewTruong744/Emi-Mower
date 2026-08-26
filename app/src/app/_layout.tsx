import { DarkTheme, DefaultTheme, ThemeProvider } from '@react-navigation/native';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import 'react-native-reanimated';
import { SafeAreaView, SafeAreaProvider } from 'react-native-safe-area-context';
import { StyleSheet, View, useColorScheme as useNativeColorScheme } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { PaperProvider, ActivityIndicator } from 'react-native-paper';
import { QueryClientProvider } from '@tanstack/react-query';
import { APP_SAFE_AREA_EDGES } from '@/constants/layout';

import { useBoundStore } from '@/store/useBoundStore';
import { useAuthSessionBootstrap } from '@/hooks/auth/useAuthSessionBootstrap';
import { useAuthRouteRedirect } from '@/hooks/auth/useAuthRouteRedirect';
import { GlobalErrorHost } from '@/errors/GlobalErrorHost';
import { queryClient } from '@/config/queryClient';

function RootLayoutNav() {
  const systemColorScheme = useNativeColorScheme();
  const themePreference = useBoundStore((state) => state.themePreference);
  const colorScheme =
    themePreference === 'system' ? (systemColorScheme ?? 'light') : themePreference;
  const authStatus = useBoundStore((state) => state.authStatus);
  useAuthSessionBootstrap();
  useAuthRouteRedirect(authStatus);

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

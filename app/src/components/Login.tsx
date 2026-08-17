import React from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { ActivityIndicator, Avatar, Button, Modal, Portal, Surface, Text } from 'react-native-paper';
import { useLogin } from '@/hooks/useLogin';
import { useBoundStore } from '@/store/useBoundStore';

export default function Login() {
  const { handleGoogleLogin, isLoading } = useLogin();
  const error = useBoundStore((state) => state.error);
  const clearError = useBoundStore((state) => state.clearError);

  return (
    <View style={loginStyles.container}>
      <ScrollView contentContainerStyle={loginStyles.scrollContent}>
        <View style={loginStyles.header}>
          <Text variant="headlineMedium" style={loginStyles.title}>
            Emi Mower
          </Text>
          <Text variant="bodyLarge" style={loginStyles.subtitle}>
            Your connected mower fleet, all in one place.
          </Text>
        </View>

        <Surface elevation={1} style={loginStyles.card}>
          <View style={loginStyles.logoContainer}>
            <Avatar.Icon size={72} icon="robot" style={loginStyles.logoIcon} color="#FFFFFF" />
            <Text variant="titleLarge" style={loginStyles.cardTitle}>
              Welcome back
            </Text>
            <Text variant="bodyMedium" style={loginStyles.cardDescription}>
              Sign in to monitor your fleet and operate your mower.
            </Text>
          </View>

          {isLoading ? (
            <ActivityIndicator animating color="#2563eb" size="large" style={loginStyles.loader} />
          ) : (
            <Button
              mode="contained"
              icon="google"
              onPress={handleGoogleLogin}
              style={loginStyles.button}
              labelStyle={loginStyles.buttonLabel}
            >
              Sign in with Google
            </Button>
          )}
        </Surface>
      </ScrollView>

      <Portal>
        <Modal
          visible={Boolean(error)}
          onDismiss={clearError}
          contentContainerStyle={loginStyles.errorModal}
        >
          <Surface elevation={3} style={loginStyles.errorSurface}>
            <Text variant="titleLarge" style={loginStyles.errorModalTitle}>
              {error?.title ?? 'Error'}
            </Text>
            <Text style={loginStyles.errorModalMessage}>
              {error?.message ?? 'Something went wrong. Please try again.'}
            </Text>
            <Button mode="contained" onPress={clearError}>
              Dismiss
            </Button>
          </Surface>
        </Modal>
      </Portal>
    </View>
  );
}

const loginStyles = StyleSheet.create({
  container: { flex: 1 },
  card: {
    alignItems: 'center',
    borderRadius: 16,
    padding: 24,
  },
  cardDescription: { marginTop: 6, opacity: 0.7, textAlign: 'center' },
  cardTitle: { fontWeight: '700', marginTop: 16 },
  errorSurface: { borderRadius: 16, padding: 24 },
  errorModal: { margin: 20 },
  errorModalMessage: { marginBottom: 24, opacity: 0.72 },
  errorModalTitle: { fontWeight: '700', marginBottom: 12 },
  header: { marginBottom: 20 },
  loader: { marginVertical: 10 },
  logoContainer: {
    alignItems: 'center',
    marginBottom: 24,
  },
  logoIcon: {
    backgroundColor: '#2563eb',
  },
  scrollContent: { flexGrow: 1, justifyContent: 'center', padding: 20, paddingBottom: 36 },
  subtitle: {
    marginTop: 4,
    opacity: 0.7,
  },
  title: { fontWeight: '700' },
  button: {
    backgroundColor: '#2563eb',
    borderRadius: 8,
    paddingVertical: 4,
    width: '100%',
  },
  buttonLabel: {
    fontSize: 15,
    fontWeight: '700',
  },
});

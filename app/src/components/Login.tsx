import React from 'react';
import { StyleSheet, View } from 'react-native';
import { ActivityIndicator, Avatar, Button, Modal, Portal, Text } from 'react-native-paper';
import { useLogin } from '@/hooks/useLogin';
import { useBoundStore } from '@/store/useBoundStore';

export default function Login() {
  const { handleGoogleLogin, isLoading } = useLogin();
  const error = useBoundStore((state) => state.error);
  const clearError = useBoundStore((state) => state.clearError);

  return (
    <View style={loginStyles.container}>
      <View style={loginStyles.card}>
        <View style={loginStyles.logoContainer}>
          <Avatar.Icon size={80} icon="robot" style={loginStyles.logoIcon} color="#FFFFFF" />
          <Text style={loginStyles.title}>Emi Mower</Text>
          <Text style={loginStyles.subtitle}>
            Manage and operate your lawn mower fleet autonomously
          </Text>
        </View>

        {isLoading ? (
          <ActivityIndicator
            animating={true}
            color="#4CAF50"
            size="large"
            style={loginStyles.loader}
          />
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
      </View>

      <Portal>
        <Modal
          visible={Boolean(error)}
          onDismiss={clearError}
          contentContainerStyle={loginStyles.errorModal}
        >
          <Text variant="titleLarge" style={loginStyles.errorModalTitle}>
            {error?.title ?? 'Error'}
          </Text>
          <Text style={loginStyles.errorModalMessage}>
            {error?.message ?? 'Something went wrong. Please try again.'}
          </Text>
          <Button mode="contained" onPress={clearError}>
            Dismiss
          </Button>
        </Modal>
      </Portal>
    </View>
  );
}

const loginStyles = StyleSheet.create({
  container: {
    backgroundColor: '#121212',
    flex: 1,
    justifyContent: 'center',
    padding: 24,
  },
  card: {
    alignItems: 'center',
    backgroundColor: '#1E1E1E',
    borderRadius: 16,
    elevation: 8,
    padding: 32,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
  },
  logoContainer: {
    alignItems: 'center',
    marginBottom: 40,
  },
  logoIcon: {
    alignItems: 'center',
    backgroundColor: '#4CAF50',
    borderRadius: 40,
    elevation: 5,
    height: 80,
    justifyContent: 'center',
    marginBottom: 16,
    shadowColor: '#4CAF50',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.5,
    shadowRadius: 10,
    width: 80,
  },
  title: {
    color: '#FFFFFF',
    fontSize: 28,
    fontWeight: 'bold',
    letterSpacing: 0.5,
    textAlign: 'center',
  },
  subtitle: {
    color: '#B0B0B0',
    fontSize: 16,
    lineHeight: 22,
    marginTop: 8,
    textAlign: 'center',
  },
  button: {
    backgroundColor: '#FFFFFF',
    borderRadius: 28,
    elevation: 3,
    paddingVertical: 6,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    width: '100%',
  },
  buttonLabel: {
    color: '#000000',
    fontSize: 16,
    fontWeight: 'bold',
  },
  loader: {
    marginTop: 20,
  },
  errorModal: {
    backgroundColor: '#1E1E1E',
    borderRadius: 16,
    margin: 24,
    padding: 24,
  },
  errorModalTitle: {
    color: '#FFFFFF',
    marginBottom: 12,
  },
  errorModalMessage: {
    color: '#FFFFFF',
    marginBottom: 24,
  },
});

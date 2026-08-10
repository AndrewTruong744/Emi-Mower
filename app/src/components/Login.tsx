import React from 'react';
import { View } from 'react-native';
import { ActivityIndicator, Avatar, Button, Modal, Portal, Text } from 'react-native-paper';
import { useLogin } from '@/hooks/useLogin';
import { useBoundStore } from '@/store/useBoundStore';
import { loginStyles } from '@/styles/loginStyles';

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

import React from 'react';
import { View } from 'react-native';
import { Text, Button, ActivityIndicator, Snackbar, Avatar } from 'react-native-paper';
import { useLogin } from '@/hooks/useLogin';
import { loginStyles } from '@/styles/loginStyles';

export default function LoginScreen() {
  const { handleGoogleLogin, isLoading, errorVisible, errorMessage, dismissError } = useLogin();

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

      <Snackbar
        visible={errorVisible}
        onDismiss={dismissError}
        duration={5000}
        style={loginStyles.snackbar}
        action={{
          label: 'Dismiss',
          onPress: dismissError,
          textColor: '#FFFFFF',
        }}
      >
        {errorMessage || ''}
      </Snackbar>
    </View>
  );
}

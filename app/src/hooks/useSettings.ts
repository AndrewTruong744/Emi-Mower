import { Alert } from 'react-native';
import { useShallow } from 'zustand/react/shallow';
import { useBoundStore } from '@/store/useBoundStore';
import { usePatchUsername } from './api/user/usePatchUsername';
import { usePatchUserEmail } from './api/user/usePatchUserEmail';
import { useChangeEmail } from './useChangeEmail';
import { useLogout } from './useLogout';

export const useSettings = () => {
  const { user_id, email, displayName, setUser, setAuthTokens } = useBoundStore(
    useShallow((state) => ({
      user_id: state.user_id,
      email: state.email,
      displayName: state.displayName,
      setUser: state.setUser,
      setAuthTokens: state.setAuthTokens,
    }))
  );

  const patchUsernameMutation = usePatchUsername();
  const patchUserEmailMutation = usePatchUserEmail();
  const { triggerChangeEmail, isLoading: isEmailAuthLoading } = useChangeEmail();
  const { logout, isLoading: isLogoutLoading } = useLogout();

  const handleUpdateUsername = async (newUserName: string) => {
    if (!user_id) {
      Alert.alert('Error', 'No authenticated user found');
      return;
    }
    try {
      const response = await patchUsernameMutation.mutateAsync({
        userId: user_id,
        newUserName,
      });
      if (response.new_user_name) {
        setUser({
          user_id,
          email,
          displayName: response.new_user_name,
        });
        Alert.alert('Success', 'Username updated successfully');
      }
    } catch (err: any) {
      Alert.alert('Update Failed', err.message || 'Failed to update username');
      throw err;
    }
  };

  const handleChangeEmail = async () => {
    if (!user_id) {
      Alert.alert('Error', 'No authenticated user found');
      return;
    }
    try {
      // Get temporary new tokens from Google
      const tempTokens = await triggerChangeEmail();

      // Patch user email passing the new ID token
      const response = await patchUserEmailMutation.mutateAsync({
        userId: user_id,
        newIdToken: tempTokens.idToken,
      });

      if (response.new_email) {
        // Update Zustand store on success
        setAuthTokens(tempTokens.idToken, tempTokens.refreshToken);
        setUser({
          user_id,
          email: response.new_email,
          displayName,
        });
        Alert.alert('Success', 'Email updated successfully');
      } else {
        throw new Error('Email update did not return the new email address.');
      }
    } catch (err: any) {
      Alert.alert('Email Update Failed', err.message || 'Failed to update email');
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
    } catch (err: any) {
      Alert.alert('Logout Failed', err.message || 'Failed to logout');
    }
  };

  return {
    user: {
      user_id,
      email,
      displayName,
    },
    updateUsername: handleUpdateUsername,
    changeEmail: handleChangeEmail,
    logout: handleLogout,
    isUpdatingUsername: patchUsernameMutation.isPending,
    isUpdatingEmail: patchUserEmailMutation.isPending || isEmailAuthLoading,
    isLoggingOut: isLogoutLoading,
  };
};

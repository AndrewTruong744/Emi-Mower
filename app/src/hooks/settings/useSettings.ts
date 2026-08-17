import { Alert } from 'react-native';
import { useShallow } from 'zustand/react/shallow';
import { firebaseAuth } from '@/config/firebase';
import { useBoundStore } from '@/store/useBoundStore';
import { usePatchUsername } from '../api/user/usePatchUsername';
import { usePatchUserEmail } from '../api/user/usePatchUserEmail';
import { useChangeEmail } from '../useChangeEmail';
import { useLogout } from '../useLogout';

export const useSettings = () => {
  const { user_id, email, displayName, setUser, setAuthToken } = useBoundStore(
    useShallow((state) => ({
      user_id: state.user_id,
      email: state.email,
      displayName: state.displayName,
      setUser: state.setUser,
      setAuthToken: state.setAuthToken,
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
        setUser({ user_id, email, displayName: response.new_user_name });
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
      const tempTokens = await triggerChangeEmail();
      const response = await patchUserEmailMutation.mutateAsync({
        newIdToken: tempTokens.idToken,
        newEmail: tempTokens.email || '',
      });

      if (!response.new_email) {
        throw new Error('Email update did not return the new email address.');
      }

      const refreshedIdToken = await firebaseAuth.currentUser?.getIdToken(true);
      setAuthToken(refreshedIdToken || tempTokens.idToken);
      setUser({ user_id, email: response.new_email, displayName });
      Alert.alert('Success', 'Email updated successfully');
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
    user: { user_id, email, displayName },
    updateUsername: handleUpdateUsername,
    changeEmail: handleChangeEmail,
    logout: handleLogout,
    isUpdatingUsername: patchUsernameMutation.isPending,
    isUpdatingEmail: patchUserEmailMutation.isPending || isEmailAuthLoading,
    isLoggingOut: isLogoutLoading,
  };
};

import { Alert } from 'react-native';
import { useShallow } from 'zustand/react/shallow';
import { useBoundStore } from '@/store/useBoundStore';
import { usePatchUsername } from '../api/user/usePatchUsername';
import { usePatchUserEmail } from '../api/user/usePatchUserEmail';
import { useChangeEmail } from '../useChangeEmail';
import { useLogout } from '../useLogout';
import { reportAppError } from '@/errors/reporter';

export const useSettings = () => {
  const { user_id, email, displayName, setUser } = useBoundStore(
    useShallow((state) => ({
      user_id: state.user_id,
      email: state.email,
      displayName: state.displayName,
      setUser: state.setUser,
    }))
  );

  const patchUsernameMutation = usePatchUsername();
  const patchUserEmailMutation = usePatchUserEmail();
  const { triggerChangeEmail, isLoading: isEmailAuthLoading } = useChangeEmail();
  const { logout, isLoading: isLogoutLoading } = useLogout();

  const handleUpdateUsername = async (newUserName: string) => {
    if (!user_id) {
      reportAppError('auth.session_failed', new Error('No authenticated user found'));
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
      reportAppError('zenoh.request_failed', err);
    }
  };

  const handleChangeEmail = async () => {
    if (!user_id) {
      reportAppError('auth.session_failed', new Error('No authenticated user found'));
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

      setUser({ user_id, email: response.new_email, displayName });
      Alert.alert('Success', 'Email updated successfully');
    } catch (err: any) {
      reportAppError('zenoh.request_failed', err);
    }
  };

  const handleLogout = () => logout();

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

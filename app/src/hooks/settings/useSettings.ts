import { useRef, useState } from 'react';
import { Alert } from 'react-native';
import { useShallow } from 'zustand/react/shallow';
import { useBoundStore } from '@/store/useBoundStore';
import { usePatchUsername } from '../api/user/usePatchUsername';
import { usePatchUserEmail } from '../api/user/usePatchUserEmail';
import { useChangeEmail } from '../useChangeEmail';
import { useLogout } from '../useLogout';
import { reportAppError } from '@/errors/reporter';

export const useSettings = () => {
  const switchingRef = useRef(false);
  const [switching, setSwitching] = useState(false);
  const [nameUpdateFeedback, setNameUpdateFeedback] = useState<{
    type: 'success' | 'error';
    message: string;
  } | null>(null);
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
    setNameUpdateFeedback(null);
    if (!user_id) {
      setNameUpdateFeedback({ type: 'error', message: 'Sign in before updating your name.' });
      reportAppError('auth.session_failed', new Error('No authenticated user found'));
      return;
    }
    const generation = useBoundStore.getState().authGeneration;
    try {
      const response = await patchUsernameMutation.mutateAsync({
        userId: user_id,
        newUserName,
      });
      if (!response.new_user_name) throw new Error('The server did not confirm your new name.');
      const current = useBoundStore.getState();
      if (current.authGeneration !== generation || current.user_id !== user_id) return;
      setUser({ user_id, email: current.email, displayName: response.new_user_name });
      setNameUpdateFeedback({ type: 'success', message: 'Name updated successfully.' });
    } catch (err) {
      setNameUpdateFeedback({
        type: 'error',
        message: 'Name could not be updated. Please try again.',
      });
      reportAppError('zenoh.request_failed', err);
    }
  };

  const handleChangeEmail = async () => {
    if (!user_id) {
      reportAppError('auth.session_failed', new Error('No authenticated user found'));
      return;
    }
    if (switchingRef.current) return;
    switchingRef.current = true;
    setSwitching(true);
    const generation = useBoundStore.getState().authGeneration;
    let proof: Awaited<ReturnType<typeof triggerChangeEmail>> | undefined;
    try {
      proof = await triggerChangeEmail();
      if (useBoundStore.getState().authGeneration !== generation)
        throw new Error('Your signed-in account changed. Try again.');
      const response = await patchUserEmailMutation.mutateAsync({
        originalIdToken: proof.originalIdToken,
        newIdToken: proof.idToken,
      });
      if (!response.new_email || response.user_id !== proof.userId)
        throw new Error('Account switch returned an unexpected identity.');
      // Only switch Firebase after the backend has committed ownership and
      // revoked the old identity. Its auth-state listener logs the new UID into Zenoh.
      try {
        await proof.complete();
      } catch {
        throw new Error(
          'Your mowers were transferred. Sign in with the selected Google account to finish.'
        );
      }
      Alert.alert(
        'Success',
        'Google account switched. Your mowers are available with the new login.'
      );
    } catch (err) {
      reportAppError('zenoh.request_failed', err);
    } finally {
      await proof?.cleanup();
      switchingRef.current = false;
      setSwitching(false);
    }
  };

  const handleLogout = () => logout();

  return {
    user: { user_id, email, displayName },
    updateUsername: handleUpdateUsername,
    changeEmail: handleChangeEmail,
    logout: handleLogout,
    isUpdatingUsername: patchUsernameMutation.isPending,
    nameUpdateFeedback,
    isUpdatingEmail: switching || patchUserEmailMutation.isPending || isEmailAuthLoading,
    isLoggingOut: isLogoutLoading,
  };
};

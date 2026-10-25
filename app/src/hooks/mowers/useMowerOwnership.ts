import { useCallback, useRef, useState } from 'react';
import { firebaseAuth, getFirebaseIdToken } from '@/config/firebase';
import { zenohQuery } from '@/config/zenohClient';
import type {
  AddMowerToUserRequest,
  AddMowerToUserResponse,
  RemoveMowerFromUserRequest,
  RemoveMowerFromUserResponse,
  TransferMowerRequest,
  TransferMowerResponse,
} from '@/generated/zenoh';
import {
  addMowerToUserPath,
  removeMowerFromUserPath,
  transferMowerPath,
} from '@/generated/zenohPaths';
import { useBoundStore } from '@/store/useBoundStore';
import { loginUser } from '@/zenoh/UserLogin';
import { initializeMowerTelemetrySubscription } from '@/zenoh/mowerTelemetry';
import { initializeMowerLivelinessSubscription } from '@/zenoh/mowerLiveliness';
import { reportAppError } from '@/errors/reporter';

export type OwnershipResult = { success: boolean; error?: string; message?: string };
type Action = 'add' | 'remove' | 'transfer' | 'refresh';
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function errorMessage(error: unknown): string {
  if (!(error instanceof Error)) return 'Unable to update your fleet. Please try again.';
  // Zenoh error payloads use the backend's ProblemDetails contract.
  try {
    const problem = JSON.parse(error.message);
    if (typeof problem.detail === 'string') return problem.detail;
  } catch {
    /* Ordinary transport and authentication errors are already text. */
  }
  return error.message;
}

/** Ownership is confirmed by the backend before changing the displayed fleet. */
export function useMowerOwnership() {
  const pending = useRef(false);
  const [isPending, setIsPending] = useState(false);
  const run = useCallback(
    async (action: Action, rawMowerId = '', rawRecipient = ''): Promise<OwnershipResult> => {
      if (pending.current)
        return { success: false, error: 'A fleet update is already in progress.' };
      const mowerId = rawMowerId.trim().toLowerCase();
      const recipient = rawRecipient.trim();
      const initial = useBoundStore.getState();
      const { user_id: userId, authGeneration: generation } = initial;
      if (!userId || firebaseAuth.currentUser?.uid !== userId)
        return { success: false, error: 'Sign in before updating your fleet.' };
      if (action !== 'refresh' && !uuidPattern.test(mowerId))
        return { success: false, error: 'Enter a valid mower UUID.' };
      if (action === 'add' && initial.mowers.includes(mowerId))
        return { success: false, error: 'That mower is already in your fleet.' };
      if (action === 'transfer' && (!recipient || recipient.length > 128 || recipient === userId))
        return { success: false, error: 'Enter a different existing user’s User ID (UID).' };
      if ((action === 'remove' || action === 'transfer') && !initial.mowers.includes(mowerId))
        return { success: false, error: 'Select a mower from your fleet.' };
      const assertCurrent = () => {
        const current = useBoundStore.getState();
        if (
          current.authGeneration !== generation ||
          current.user_id !== userId ||
          firebaseAuth.currentUser?.uid !== userId
        )
          throw new Error('Your signed-in account changed. Refresh your fleet and try again.');
        return current;
      };
      pending.current = true;
      setIsPending(true);
      try {
        if (action === 'refresh') {
          const data = await loginUser();
          const current = assertCurrent();
          if (data.id !== userId) throw new Error('Fleet refresh returned an unexpected account.');
          current.setMowers(data.mowers);
        } else {
          const idToken = await getFirebaseIdToken(true);
          assertCurrent();
          const response =
            action === 'add'
              ? await zenohQuery<AddMowerToUserResponse>(addMowerToUserPath(), {
                  id_token: idToken,
                  mower_id: mowerId,
                } satisfies AddMowerToUserRequest)
              : action === 'remove'
                ? await zenohQuery<RemoveMowerFromUserResponse>(removeMowerFromUserPath(), {
                    id_token: idToken,
                    mower_id: mowerId,
                  } satisfies RemoveMowerFromUserRequest)
                : await zenohQuery<TransferMowerResponse>(transferMowerPath(), {
                    id_token: idToken,
                    mower_id: mowerId,
                    new_owner_id: recipient,
                  } satisfies TransferMowerRequest);
          const current = assertCurrent();
          if (
            response.user_id !== userId ||
            response.mower_id !== mowerId ||
            (action === 'transfer' &&
              (response as TransferMowerResponse).new_owner_id !== recipient)
          )
            throw new Error(
              'The server did not confirm the requested ownership change. Refresh your fleet.'
            );
          if (action === 'add') current.addMower(mowerId);
          else current.setMowers(current.mowers.filter((id) => id !== mowerId));
        }
        // These declarations are idempotent for the current auth generation.
        // A newly added first mower needs subscriptions even without reconnecting.
        try {
          await Promise.all([
            initializeMowerTelemetrySubscription(generation),
            initializeMowerLivelinessSubscription(generation),
          ]);
        } catch (error) {
          reportAppError('zenoh.subscription_failed', error);
        }
        assertCurrent();
        return {
          success: true,
          message:
            action === 'add'
              ? 'Mower added to your account.'
              : action === 'remove'
                ? 'Mower removed from your account.'
                : action === 'transfer'
                  ? 'Mower transferred. The recipient can refresh their fleet to see it.'
                  : 'Fleet refreshed.',
        };
      } catch (error) {
        return { success: false, error: errorMessage(error) };
      } finally {
        pending.current = false;
        setIsPending(false);
      }
    },
    []
  );
  return {
    isPending,
    addMower: useCallback((id: string) => run('add', id), [run]),
    removeMower: useCallback((id: string) => run('remove', id), [run]),
    transferMower: useCallback(
      (id: string, recipient: string) => run('transfer', id, recipient),
      [run]
    ),
    refreshFleet: useCallback(() => run('refresh'), [run]),
  };
}

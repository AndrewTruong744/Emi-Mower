import { useMutation } from '@tanstack/react-query';
import { getFirebaseIdToken } from '@/config/firebase';
import { zenohPut } from '@/config/zenohClient';
import { cutoutUploadedPath } from '@/generated/zenohPaths';
import { reportAppError } from '@/errors/reporter';

export interface CutoutUploadNotificationParams {
  cutoutId: string;
  success: boolean;
  failureReason?: string;
}

/** Tells the backend to verify (or discard) a signed GCS upload. */
export function useCutoutUploadNotification() {
  return useMutation({
    mutationFn: async ({ cutoutId, success, failureReason }: CutoutUploadNotificationParams) => {
      const idToken = await getFirebaseIdToken();
      await zenohPut(cutoutUploadedPath(), {
        id_token: idToken,
        cutout_id: cutoutId,
        success,
        ...(failureReason ? { failure_reason: failureReason } : {}),
      });
    },
    retry: false,
    onError: (error) => reportAppError('map.cutout_notification_failed', error),
  });
}

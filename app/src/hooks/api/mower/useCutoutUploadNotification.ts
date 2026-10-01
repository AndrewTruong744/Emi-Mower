import { useMutation } from '@tanstack/react-query';
import { getFirebaseIdToken } from '@/config/firebase';
import { zenohPut } from '@/config/zenohClient';
import type { CutoutUploadNotification } from '@/generated/zenoh';
import { cutoutUploadedPath } from '@/generated/zenohPaths';
import { reportAppError } from '@/errors/reporter';

export interface CutoutUploadNotificationParams {
  cutoutId: string;
  objectKey: string;
  contentType: 'image/png' | 'image/jpeg' | 'image/webp';
  success: boolean;
  failureReason?: string;
}

/** Tells the backend to verify (or discard) a signed GCS upload. */
export function useCutoutUploadNotification() {
  return useMutation({
    mutationFn: async ({ cutoutId, objectKey, contentType, success, failureReason }: CutoutUploadNotificationParams) => {
      const idToken = await getFirebaseIdToken();
      const notification: CutoutUploadNotification = {
        id_token: idToken,
        cutout_id: cutoutId,
        object_key: objectKey,
        content_type: contentType,
        success,
        ...(failureReason ? { failure_reason: failureReason } : {}),
      };
      await zenohPut(cutoutUploadedPath(), notification);
    },
    retry: false,
    onError: (error) => reportAppError('map.cutout_notification_failed', error),
  });
}

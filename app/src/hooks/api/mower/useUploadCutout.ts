import { useMutation } from '@tanstack/react-query';
import { getFirebaseIdToken } from '@/config/firebase';
import { zenohQuery } from '@/config/zenohClient';
import { cutoutUploadUrlPath } from '@/generated/zenohPaths';
import type { CutoutUploadUrlResponse } from '@/generated/zenoh';
import { reportAppError } from '@/errors/reporter';
import { InputValidationError } from '@/errors/types';
import { useCutoutUploadNotification } from './useCutoutUploadNotification';

export interface UploadCutoutParams {
  imageUri: string;
  mowerIds: string[];
  contentType?: 'image/png' | 'image/jpeg' | 'image/webp';
}

function inferContentType(uri: string): 'image/png' | 'image/jpeg' | 'image/webp' {
  const path = uri.toLowerCase();
  if (path.endsWith('.jpg') || path.endsWith('.jpeg')) return 'image/jpeg';
  if (path.endsWith('.webp')) return 'image/webp';
  return 'image/png';
}

/** Gets a signed PUT URL, uploads the image directly to GCS, then notifies backend verification. */
export function useUploadCutout() {
  const notification = useCutoutUploadNotification();
  return useMutation({
    mutationFn: async ({ imageUri, mowerIds, contentType }: UploadCutoutParams) => {
      const recipients = [...new Set(mowerIds.map((id) => id.trim()).filter(Boolean))];
      if (!imageUri) throw new InputValidationError('A cutout image is required');
      if (recipients.length === 0) throw new InputValidationError('Select at least one mower');

      const resolvedContentType = contentType ?? inferContentType(imageUri);
      const idToken = await getFirebaseIdToken();
      const upload = await zenohQuery<CutoutUploadUrlResponse>(cutoutUploadUrlPath(), {
        id_token: idToken,
        mower_ids: recipients,
        content_type: resolvedContentType,
      });
      try {
        const image = await fetch(imageUri);
        if (!image.ok) throw new Error(`Could not read cutout image (${image.status})`);
        const uploadResponse = await fetch(upload.upload_url, {
          method: 'PUT',
          headers: { 'Content-Type': upload.content_type },
          body: await image.blob(),
        });
        if (!uploadResponse.ok) throw new Error(`Cutout upload failed (${uploadResponse.status})`);
      } catch (error) {
        await notification.mutateAsync({
          cutoutId: upload.cutout_id,
          success: false,
          failureReason: error instanceof Error ? error.message : 'Upload failed',
        }).catch(() => undefined);
        throw error;
      }
      await notification.mutateAsync({ cutoutId: upload.cutout_id, success: true });
      return upload;
    },
    retry: false,
    onError: (error) => reportAppError('map.cutout_upload_failed', error),
  });
}

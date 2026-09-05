import { beforeEach, describe, expect, it, jest } from '@jest/globals';
import { act, renderHook, waitFor } from '@testing-library/react-native';
import { createWrapper, mockedZenohPut, mockedZenohQuery, resetHookState } from './testUtils';
import { useUploadCutout } from '@/hooks/api/mower/useUploadCutout';

describe('useUploadCutout', () => {
  beforeEach(() => {
    resetHookState();
    mockedZenohQuery.mockResolvedValue({
      cutout_id: 'cutout-1', upload_url: 'https://storage.test/upload',
      expires_in: 900, object_key: 'users/user/cutouts/cutout-1.png', content_type: 'image/png',
    });
    mockedZenohPut.mockResolvedValue(undefined);
  });

  it('queries a signed URL, uploads image bytes, and publishes completion', async () => {
    const fetchMock = jest.spyOn(global, 'fetch')
      .mockResolvedValueOnce({ ok: true, blob: async () => new Blob(['image']) } as Response)
      .mockResolvedValueOnce({ ok: true } as Response);
    const { result } = renderHook(() => useUploadCutout(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.mutateAsync({ imageUri: 'file:///boundary.png', mowerIds: ['mower-1'] });
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedZenohQuery).toHaveBeenCalledWith('user/cutouts/upload-url', {
      id_token: 'firebase-token', mower_ids: ['mower-1'], content_type: 'image/png',
    });
    expect(fetchMock).toHaveBeenNthCalledWith(2, 'https://storage.test/upload', expect.objectContaining({ method: 'PUT' }));
    expect(mockedZenohPut).toHaveBeenCalledWith('user/cutouts/uploaded', {
      id_token: 'firebase-token', cutout_id: 'cutout-1', success: true,
    });
    fetchMock.mockRestore();
  });

  it('notifies the backend when direct upload fails', async () => {
    const fetchMock = jest.spyOn(global, 'fetch')
      .mockResolvedValueOnce({ ok: true, blob: async () => new Blob(['image']) } as Response)
      .mockResolvedValueOnce({ ok: false, status: 403 } as Response);
    const { result } = renderHook(() => useUploadCutout(), { wrapper: createWrapper() });

    await act(async () => {
      await expect(result.current.mutateAsync({ imageUri: 'file:///boundary.png', mowerIds: ['mower-1'] }))
        .rejects.toThrow('Cutout upload failed');
    });
    expect(mockedZenohPut).toHaveBeenCalledWith('user/cutouts/uploaded', expect.objectContaining({
      cutout_id: 'cutout-1', success: false,
    }));
    fetchMock.mockRestore();
  });
});

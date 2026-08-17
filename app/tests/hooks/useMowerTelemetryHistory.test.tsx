import { beforeEach, describe, expect, it } from '@jest/globals';
import { act, renderHook, waitFor } from '@testing-library/react-native';
import { createWrapper, mockedZenohQuery, resetHookState } from './testUtils';
import { useMowerTelemetryHistory } from '@/hooks/api/mower/useMowerTelemetryHistory';

describe('useMowerTelemetryHistory', () => {
  beforeEach(resetHookState);

  it('uses the opaque cursor returned by the previous history page', async () => {
    mockedZenohQuery.mockResolvedValue({
      telemetry_type: 'accel_x', limit: 60, total: 180, has_more: true, next_cursor: 'cursor-2', points: [],
    });
    const { result } = renderHook(
      () => useMowerTelemetryHistory({ mowerId: 'mower-1', telemetryType: 'accel_x', cursor: 'cursor-1' }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedZenohQuery).toHaveBeenCalledWith('mower/mower-1/telemetry/accel_x/old', {
      id_token: 'firebase-token', cursor: 'cursor-1',
    });
  });

  it('does not request history until it has a mower and metric', async () => {
    const { result } = renderHook(
      () => useMowerTelemetryHistory({ mowerId: '', telemetryType: '', cursor: null }),
      { wrapper: createWrapper() }
    );

    await act(async () => undefined);
    expect(result.current.fetchStatus).toBe('idle');
    expect(mockedZenohQuery).not.toHaveBeenCalled();
  });
});

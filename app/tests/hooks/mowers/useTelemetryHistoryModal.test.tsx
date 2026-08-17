import { describe, expect, it, jest } from '@jest/globals';
import { act, renderHook, waitFor } from '@testing-library/react-native';
import { useMowerTelemetryHistory } from '@/hooks/api/mower/useMowerTelemetryHistory';
import { useTelemetryHistoryModal } from '@/hooks/mowers/useTelemetryHistoryModal';

jest.mock('@/hooks/api/mower/useMowerTelemetryHistory', () => ({
  useMowerTelemetryHistory: jest.fn(),
}));

const mockUseMowerTelemetryHistory = useMowerTelemetryHistory as jest.Mock<(...args: any[]) => any>;
const chart = { title: 'Cutting motor speed', telemetryType: 'cutting_motor_speed', value: '2,800 RPM', values: [10, 20], color: '#059669' };

describe('useTelemetryHistoryModal', () => {
  it('uses cursor pages for older data and guards both ends of navigation', async () => {
    let response: { data: any; isFetching: boolean } = { data: undefined, isFetching: false };
    mockUseMowerTelemetryHistory.mockImplementation(() => response);
    const { result, rerender } = renderHook(() => useTelemetryHistoryModal({ chart, mowerId: 'mower-1' }));

    expect(result.current.page).toBe(0);
    expect(result.current.canViewNewer).toBe(false);
    act(() => result.current.viewOlder());
    expect(mockUseMowerTelemetryHistory).toHaveBeenLastCalledWith(expect.objectContaining({ cursor: null, enabled: true }));

    response = {
      data: {
        telemetry_type: 'cutting_motor_speed', limit: 60, total: 61,
        has_more: false, next_cursor: null,
        points: [{ timestamp: '2026-08-16T12:00:00Z', value: 3 }, { timestamp: '2026-08-16T12:00:01Z', value: 4 }],
      },
      isFetching: false,
    };
    rerender({});

    await waitFor(() => expect(result.current.page).toBe(1));
    expect(result.current.pages[1]).toEqual([4, 3]);
    expect(result.current.canViewOlder).toBe(false);
    act(() => result.current.viewOlder());
    expect(result.current.page).toBe(1);
    act(() => result.current.viewNewer());
    expect(result.current.page).toBe(0);
  });
});

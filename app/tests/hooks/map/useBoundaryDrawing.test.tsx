import { describe, expect, it } from '@jest/globals';
import { act, renderHook } from '@testing-library/react-native';
import { useBoundaryDrawing } from '@/hooks/map/useBoundaryDrawing';

describe('useBoundaryDrawing', () => {
  it('keeps adding points until the boundary is explicitly cleared', () => {
    const { result } = renderHook(() => useBoundaryDrawing());
    const first = { x: -74.006, y: 40.7128 };

    act(() => {
      result.current.addPoint(first);
      result.current.addPoint({ x: -74.0058, y: 40.7128 });
      result.current.addPoint({ x: -74.0058, y: 40.713 });
    });
    act(() => result.current.addPoint({ x: -74.00601, y: 40.71281 }));
    expect(result.current.points).toHaveLength(4);

    act(() => result.current.undo());
    expect(result.current.points).toEqual([
      first,
      { x: -74.0058, y: 40.7128 },
      { x: -74.0058, y: 40.713 },
    ]);

    act(() => result.current.clear());
    expect(result.current.points).toEqual([]);
  });
});

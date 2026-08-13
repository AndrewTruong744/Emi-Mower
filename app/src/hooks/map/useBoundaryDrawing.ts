import { useCallback, useState } from 'react';
import { MowerMapPosition } from '@/store/types';

export function useBoundaryDrawing() {
  const [points, setPoints] = useState<MowerMapPosition[]>([]);

  const addPoint = useCallback((point: MowerMapPosition) => {
    setPoints((currentPoints) => [...currentPoints, point]);
  }, []);

  const clear = useCallback(() => {
    setPoints([]);
  }, []);

  return { addPoint, clear, points };
}

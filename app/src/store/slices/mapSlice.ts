import { StateCreator } from 'zustand';
import { BoundStoreState, MapSlice, MowerMapPosition } from '../types';

export const createMapSlice: StateCreator<BoundStoreState, [], [], MapSlice> = (set) => ({
  isSessionActive: false,
  isSessionPaused: false,
  cuttingBoundary: [],
  areaImageUri: null,
  startMowingSession: (boundary: MowerMapPosition[], areaImageUri: string) =>
    set({
      isSessionActive: true,
      isSessionPaused: false,
      cuttingBoundary: boundary,
      areaImageUri,
    }),
  setSessionPaused: (isSessionPaused) => set({ isSessionPaused }),
  cancelMowingSession: () =>
    set({
      isSessionActive: false,
      isSessionPaused: false,
      cuttingBoundary: [],
      areaImageUri: null,
    }),
});

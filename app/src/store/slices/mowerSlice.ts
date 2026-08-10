import { StateCreator } from 'zustand';
import { BoundStoreState, MowerSlice } from '../types';

export const createMowerSlice: StateCreator<BoundStoreState, [], [], MowerSlice> = (set) => ({
  mowers: [],
  setMowers: (mowers) => set({ mowers }),
  clearMowers: () => set({ mowers: [] }),
});

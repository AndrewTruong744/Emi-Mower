import { StateCreator } from 'zustand';
import { AuthSlice, BoundStoreState } from '../types';

export const createAuthSlice: StateCreator<BoundStoreState, [], [], AuthSlice> = (set) => ({
  idToken: null,
  setAuthToken: (idToken) => set({ idToken }),
  clearAuth: () => set({ idToken: null }),
});

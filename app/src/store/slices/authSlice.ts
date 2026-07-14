import { StateCreator } from 'zustand';
import { AuthSlice, BoundStoreState } from '../types';

export const createAuthSlice: StateCreator<BoundStoreState, [], [], AuthSlice> = (set) => ({
  idToken: null,
  refreshToken: null,
  setAuthTokens: (idToken, refreshToken) => set({ idToken, refreshToken }),
  clearAuth: () => set({ idToken: null, refreshToken: null }),
});

import { StateCreator } from 'zustand';
import { AuthSlice, BoundStoreState } from '../types';

export const createAuthSlice: StateCreator<BoundStoreState, [], [], AuthSlice> = (set) => ({
  idToken: null,
  authStatus: 'initializing',
  zenohEnabled: false,
  authGeneration: 0,
  setAuthToken: (idToken) => set({ idToken }),
  clearAuth: () => set({ idToken: null, authStatus: 'signedOut' }),
  setAuthStatus: (authStatus) => set({ authStatus }),
  enableZenoh: () =>
    set((state) =>
      state.zenohEnabled
        ? state
        : { zenohEnabled: true, authGeneration: state.authGeneration + 1 }
    ),
  startZenohSession: () =>
    set((state) => ({ zenohEnabled: true, authGeneration: state.authGeneration + 1 })),
  disableZenoh: () =>
    set((state) => ({ zenohEnabled: false, authGeneration: state.authGeneration + 1 })),
});

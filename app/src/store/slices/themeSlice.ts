import { StateCreator } from 'zustand';
import { BoundStoreState, ThemeSlice } from '../types';

export const createThemeSlice: StateCreator<BoundStoreState, [], [], ThemeSlice> = (set) => ({
  themePreference: 'system',
  setThemePreference: (themePreference) => set({ themePreference }),
  toggleThemePreference: () =>
    set((state) => ({
      themePreference: state.themePreference === 'dark' ? 'light' : 'dark',
    })),
});

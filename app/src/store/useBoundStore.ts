import { create } from 'zustand';
import { BoundStoreState } from './types';
import { createAuthSlice } from './slices/authSlice';
import { createUserSlice } from './slices/userSlice';
import { createMowerSlice } from './slices/mowerSlice';
import { createThemeSlice } from './slices/themeSlice';
import { createErrorSlice } from './slices/errorSlice';

export const useBoundStore = create<BoundStoreState>()((...a) => ({
  ...createAuthSlice(...a),
  ...createUserSlice(...a),
  ...createMowerSlice(...a),
  ...createThemeSlice(...a),
  ...createErrorSlice(...a),
  resetStore: () =>
    a[0]({
      idToken: null,
      user_id: null,
      email: null,
      displayName: null,
      mowers: [],
      themePreference: 'system',
      error: null,
    }),
}));

import { create } from 'zustand';
import { BoundStoreState } from './types';
import { createAuthSlice } from './slices/authSlice';
import { createUserSlice } from './slices/userSlice';
import { createMowerSlice } from './slices/mowerSlice';
import { createMapSlice } from './slices/mapSlice';
import { createThemeSlice } from './slices/themeSlice';
import { createErrorSlice } from './slices/errorSlice';

export const useBoundStore = create<BoundStoreState>()((...a) => ({
  ...createAuthSlice(...a),
  ...createUserSlice(...a),
  ...createMowerSlice(...a),
  ...createMapSlice(...a),
  ...createThemeSlice(...a),
  ...createErrorSlice(...a),
  resetStore: () =>
    a[0]((state) => ({
      authStatus: 'signedOut',
      zenohEnabled: false,
      authGeneration: state.authGeneration + 1,
      user_id: null,
      email: null,
      displayName: null,
      mowers: [],
      mowerDetails: {},
      mowerPositions: {},
      selectedMowerUuid: null,
      isSessionActive: false,
      isSessionPaused: false,
      cuttingBoundary: [],
      areaImageUri: null,
      themePreference: 'system',
      errorQueue: [],
    })),
}));

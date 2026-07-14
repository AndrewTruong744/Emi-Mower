import { create } from 'zustand';
import { BoundStoreState } from './types';
import { createAuthSlice } from './slices/authSlice';
import { createUserSlice } from './slices/userSlice';

export const useBoundStore = create<BoundStoreState>()((...a) => ({
  ...createAuthSlice(...a),
  ...createUserSlice(...a),
}));

import { StateCreator } from 'zustand';
import { UserSlice, BoundStoreState } from '../types';

export const createUserSlice: StateCreator<BoundStoreState, [], [], UserSlice> = (set) => ({
  user_id: null,
  email: null,
  displayName: null,
  setUser: (user) =>
    set({
      user_id: user.user_id,
      email: user.email,
      displayName: user.displayName,
    }),
  clearUser: () => set({ user_id: null, email: null, displayName: null }),
});

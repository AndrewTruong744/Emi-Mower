import { StateCreator } from 'zustand';
import { BoundStoreState, ErrorSlice } from '../types';

function getErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  if (typeof error === 'string' && error) {
    return error;
  }

  return 'Something went wrong. Please try again.';
}

export const createErrorSlice: StateCreator<BoundStoreState, [], [], ErrorSlice> = (set) => ({
  error: null,
  reportError: (error, options) => {
    const message = getErrorMessage(error);
    set({
      error: {
        id: `${Date.now()}-${Math.random()}`,
        title: options?.title ?? 'Error',
        message,
        source: options?.source ?? 'unknown',
      },
    });
  },
  clearError: () => set({ error: null }),
});

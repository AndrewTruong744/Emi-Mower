import { StateCreator } from 'zustand';
import { BoundStoreState, ErrorSlice } from '../types';
import type { AppError, ErrorPriority } from '@/errors/types';

const DEDUPE_WINDOW_MS = 10_000;
const MAX_QUEUED_ERRORS = 5;

const priorityValue: Record<ErrorPriority, number> = {
  low: 0,
  normal: 1,
  high: 2,
  critical: 3,
};

function sortErrors(errors: AppError[]): AppError[] {
  return [...errors].sort(
    (left, right) =>
      priorityValue[right.priority] - priorityValue[left.priority] || left.occurredAt - right.occurredAt
  );
}

export const createErrorSlice: StateCreator<BoundStoreState, [], [], ErrorSlice> = (set) => ({
  errorQueue: [],
  reportError: (error) =>
    set((state) => {
      if (error.presentation === 'silent') return state;

      const duplicateIndex = state.errorQueue.findIndex(
        (queued) =>
          queued.dedupeKey === error.dedupeKey && error.occurredAt - queued.occurredAt < DEDUPE_WINDOW_MS
      );
      if (duplicateIndex >= 0) {
        const queue = [...state.errorQueue];
        const duplicate = queue[duplicateIndex];
        queue[duplicateIndex] = {
          ...duplicate,
          count: duplicate.count + 1,
          occurredAt: error.occurredAt,
        };
        return { errorQueue: sortErrors(queue) };
      }

      return { errorQueue: sortErrors([...state.errorQueue, error]).slice(0, MAX_QUEUED_ERRORS) };
    }),
  dismissError: (id) =>
    set((state) => ({ errorQueue: state.errorQueue.filter((error) => error.id !== id) })),
  clearErrors: () => set({ errorQueue: [] }),
});

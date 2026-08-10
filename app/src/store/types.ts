export interface AuthState {
  idToken: string | null;
}

export interface AuthActions {
  setAuthToken: (idToken: string | null) => void;
  clearAuth: () => void;
}

export type AuthSlice = AuthState & AuthActions;

export interface UserState {
  user_id: string | null;
  email: string | null;
  displayName: string | null;
}

export interface UserActions {
  setUser: (user: {
    user_id: string | null;
    email: string | null;
    displayName: string | null;
  }) => void;
  clearUser: () => void;
}

export type UserSlice = UserState & UserActions;

export interface MowerState {
  mowers: string[];
}

export interface MowerActions {
  setMowers: (mowers: string[]) => void;
  clearMowers: () => void;
}

export type MowerSlice = MowerState & MowerActions;

export type ThemePreference = 'system' | 'light' | 'dark';

export interface ThemeState {
  themePreference: ThemePreference;
}

export interface ThemeActions {
  setThemePreference: (themePreference: ThemePreference) => void;
  toggleThemePreference: () => void;
}

export type ThemeSlice = ThemeState & ThemeActions;

export type AppErrorSource = 'auth' | 'zenoh' | 'network' | 'unknown';

export interface AppError {
  id: string;
  title: string;
  message: string;
  source: AppErrorSource;
}

export interface ErrorReportOptions {
  title?: string;
  source?: AppErrorSource;
}

export interface ErrorState {
  error: AppError | null;
}

export interface ErrorActions {
  reportError: (error: unknown, options?: ErrorReportOptions) => void;
  clearError: () => void;
}

export type ErrorSlice = ErrorState & ErrorActions;

export interface StoreActions {
  resetStore: () => void;
}

// Combined store state type
export type BoundStoreState =
  & AuthSlice
  & UserSlice
  & MowerSlice
  & ThemeSlice
  & ErrorSlice
  & StoreActions;

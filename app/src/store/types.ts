export interface AuthState {
  idToken: string | null;
  refreshToken: string | null;
}

export interface AuthActions {
  setAuthTokens: (idToken: string | null, refreshToken: string | null) => void;
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

// Combined store state type
export type BoundStoreState = AuthSlice & UserSlice;

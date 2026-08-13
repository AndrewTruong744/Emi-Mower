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

export type MowerOperatingState = 'on' | 'off' | 'stopped';
export type MowerHealth = 'healthy' | 'attention' | 'critical';

export interface MowerImuTelemetry {
  accelX: number;
  accelY: number;
  accelZ: number;
  gyroX: number;
  gyroY: number;
  gyroZ: number;
  magX: number;
  magY: number;
  magZ: number;
}

export interface MowerTelemetrySample {
  timestamp: number;
  latitude: number;
  longitude: number;
  batteryPercentage: number;
  leftMotorSpeed: number;
  leftMotorDirection: -1 | 0 | 1;
  rightMotorSpeed: number;
  rightMotorDirection: -1 | 0 | 1;
  cuttingMotorSpeed: number;
  slippageDetected: boolean;
  imuData: MowerImuTelemetry;
}

export interface MowerDetails {
  uuid: string;
  name: string;
  battery: number;
  state: MowerOperatingState;
  health: MowerHealth;
  telemetry: MowerTelemetrySample[];
}

/** MapLibre coordinates: x is longitude, y is latitude. */
export interface MowerMapPosition {
  x: number;
  y: number;
}

export interface MowerState {
  mowers: string[];
  mowerDetails: Record<string, MowerDetails>;
  mowerPositions: Record<string, MowerMapPosition>;
  selectedMowerUuid: string | null;
}

export interface MowerActions {
  setMowers: (mowers: string[]) => void;
  seedFakeMowers: () => void;
  addMower: (uuid: string, name?: string) => void;
  renameMower: (uuid: string, name: string) => void;
  selectMower: (uuid: string) => void;
  appendFakeTelemetry: (uuid: string) => void;
  placeMowersInBoundary: (boundary: MowerMapPosition[]) => void;
  advanceFakeMowerPositions: () => void;
  clearMowers: () => void;
}

export type MowerSlice = MowerState & MowerActions;

export interface MapState {
  isSessionActive: boolean;
  isSessionPaused: boolean;
  cuttingBoundary: MowerMapPosition[];
  areaImageUri: string | null;
}

export interface MapActions {
  startMowingSession: (boundary: MowerMapPosition[], areaImageUri: string) => void;
  setSessionPaused: (isPaused: boolean) => void;
  cancelMowingSession: () => void;
}

export type MapSlice = MapState & MapActions;

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
  & MapSlice
  & ThemeSlice
  & ErrorSlice
  & StoreActions;

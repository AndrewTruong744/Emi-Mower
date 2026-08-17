/** Generated from backend/zenoh_asyncapi.yaml. Do not edit manually. */

export interface UserLoginRequest {
  id_token: string;
}

export interface UserData {
  id: string;
  email: string;
  name: string;
  created_at?: string | null;
  mowers: string[];
  [key: string]: unknown;
}

export interface UserLoginResponse {
  user_id: string;
  token: string;
  expires_in: number;
  user_data: UserData;
}

export interface UpdateUserEmailRequest {
  id_token: string;
  new_id_token: string;
}

export interface UpdateUserEmailResponse {
  message: string;
  user_id: string;
  new_email: string;
}

export interface UpdateUserNameRequest {
  id_token: string;
  new_user_name: string;
}

export interface UpdateUserNameResponse {
  message: string;
  user_id: string;
  new_user_name: string;
}

export type LiveKitConsumeRequest = Record<string, never>;

export type LiveKitUploadRequest = Record<string, never>;

export interface LiveKitTokenResponse {
  token: string;
  url: string;
  expires_in: number;
}

export interface JoystickCommand {
  x: number;
  y: number;
}

export interface TelemetryHistoryRequest {
  id_token: string;
  cursor?: string | null;
}

export interface TelemetryHistoryPoint {
  timestamp: string;
  value: number;
}

export interface TelemetryHistoryResponse {
  telemetry_type: string;
  limit: number;
  total: number;
  has_more: boolean;
  next_cursor: string | null;
  points: TelemetryHistoryPoint[];
}

export interface ImuTelemetry {
  accel_x: number;
  accel_y: number;
  accel_z: number;
  gyro_x: number;
  gyro_y: number;
  gyro_z: number;
  mag_x: number;
  mag_y: number;
  mag_z: number;
}

export interface TelemetryRecord {
  mower_id: string;
  timestamp: string;
  latitude: number;
  longitude: number;
  battery_percentage: number;
  left_motor_speed?: number;
  left_motor_direction?: -1 | 0 | 1;
  right_motor_speed?: number;
  right_motor_direction?: -1 | 0 | 1;
  cutting_motor_speed?: number;
  slippage_detected?: boolean;
  rgb_image_url?: string | null;
  lidar_image_url?: string | null;
  imu_data?: ImuTelemetry | null;
}

export type TelemetryList = TelemetryRecord[];

export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance: string;
  code: string;
  timestamp: string;
  [key: string]: unknown;
}

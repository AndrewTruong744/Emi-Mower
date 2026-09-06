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

export interface EmergencyStopCommand {
  command_id: string;
  type: 'emergency_stop';
}

export interface SetPowerCommand {
  command_id: string;
  type: 'set_power';
  enabled: boolean;
}

export interface SetModeCommand {
  command_id: string;
  type: 'set_mode';
  mode: 'manual' | 'auto';
}

export type MowerCommandRequest = EmergencyStopCommand | SetPowerCommand | SetModeCommand;

export interface MowerCommandResponse {
  command_id: string;
  status: 'accepted' | 'rejected';
  reason?: string;
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
  imu_data?: ImuTelemetry | null;
}

export type TelemetryList = TelemetryRecord[];

export interface CutoutUploadUrlRequest {
  id_token: string;
  mower_ids: string[];
  content_type: 'image/png' | 'image/jpeg' | 'image/webp';
}

export interface CutoutUploadUrlResponse {
  cutout_id: string;
  upload_url: string;
  expires_in: number;
  object_key: string;
  content_type: string;
}

export interface CutoutUploadNotification {
  id_token: string;
  cutout_id: string;
  success: boolean;
  failure_reason?: string;
}

export type MowerCutoutDownloadUrlRequest = Record<string, never>;

export interface MowerCutoutDownloadUrlResponse {
  cutout_id: string;
  download_url: string;
  expires_in: number;
  content_type: string;
}

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

// Bootstrap renewal types generated from zenoh_asyncapi.yaml.
export type MowerCertificateRenewChallengeRequest = Record<string, never>;

export interface MowerCertificateRenewChallengeResponse {
  nonce: string;
  expires_in: number;
}

export interface MowerCertificateRenewCompleteRequest {
  nonce: string;
  csr_pem: string;
  tpm_signature: string;
}

export interface MowerCertificateRenewCompleteResponse {
  certificate_pem: string;
  ca_chain_pem: string;
  expires_at: string;
}

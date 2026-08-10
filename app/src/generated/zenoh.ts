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

/** Generated from backend/zenoh_asyncapi.yaml. Do not edit manually. */

export interface UserLoginRequest {
  id_token: string;
}

export interface UserData {
  id: string;
  email: string;
  name: string;
  created_at?: string | null;
  [key: string]: unknown;
}

export interface UserLoginResponse {
  user_id: string;
  token: string;
  expires_in: number;
  user_data: UserData;
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

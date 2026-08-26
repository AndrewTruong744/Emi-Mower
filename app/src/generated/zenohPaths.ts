/** Generated from backend/zenoh_asyncapi.yaml. Do not edit manually. */

export const USER_LOGIN_ADDRESS = "user/login" as const;

export function userLoginPath(): string {
  return USER_LOGIN_ADDRESS;
}

export const ADD_MOWER_TO_USER_ADDRESS = "user/add_mower" as const;

export function addMowerToUserPath(): string {
  return ADD_MOWER_TO_USER_ADDRESS;
}

export const UPDATE_USER_NAME_ADDRESS = "user/update_name" as const;

export function updateUserNamePath(): string {
  return UPDATE_USER_NAME_ADDRESS;
}

export const UPDATE_MOWER_NAME_ADDRESS = "mower/{mower_id}/update_name" as const;

export function updateMowerNamePath(mowerId: string): string {
  return (
    UPDATE_MOWER_NAME_ADDRESS
      .replace('{mower_id}', mowerId)
  );
}

export const UPDATE_USER_EMAIL_ADDRESS = "user/update_email" as const;

export function updateUserEmailPath(): string {
  return UPDATE_USER_EMAIL_ADDRESS;
}

export const LIVEKIT_CONSUME_ADDRESS = "mower/{mower_id}/livekit/consume" as const;

export function livekitConsumePath(mowerId: string): string {
  return (
    LIVEKIT_CONSUME_ADDRESS
      .replace('{mower_id}', mowerId)
  );
}

export const LIVEKIT_UPLOAD_ADDRESS = "mower/{mower_id}/livekit/upload" as const;

export function livekitUploadPath(mowerId: string): string {
  return (
    LIVEKIT_UPLOAD_ADDRESS
      .replace('{mower_id}', mowerId)
  );
}

export const MOWER_JOYSTICK_ADDRESS = "mower/{mower_id}/joystick" as const;

export function mowerJoystickPath(mowerId: string): string {
  return (
    MOWER_JOYSTICK_ADDRESS
      .replace('{mower_id}', mowerId)
  );
}

export const MOWER_COMMAND_ADDRESS = "mower/{mower_id}/command" as const;

export function mowerCommandPath(mowerId: string): string {
  return (
    MOWER_COMMAND_ADDRESS
      .replace('{mower_id}', mowerId)
  );
}

export const MOWER_TELEMETRY_HISTORY_ADDRESS = "mower/{mower_id}/telemetry/{telemetry_type}/old" as const;

export function mowerTelemetryHistoryPath(mowerId: string, telemetryType: string): string {
  return (
    MOWER_TELEMETRY_HISTORY_ADDRESS
      .replace('{mower_id}', mowerId)
      .replace('{telemetry_type}', telemetryType)
  );
}

export const MOWER_TELEMETRY_ADDRESS = "mower/{mower_id}/telemetry" as const;

export function mowerTelemetryPath(mowerId: string): string {
  return (
    MOWER_TELEMETRY_ADDRESS
      .replace('{mower_id}', mowerId)
  );
}

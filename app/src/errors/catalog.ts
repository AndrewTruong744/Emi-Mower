import type { ErrorCode, ErrorDefinition } from './types';

export const ERROR_CATALOG: Record<ErrorCode, ErrorDefinition> = {
  'auth.sign_in_failed': {
    title: 'Sign-in failed',
    presentation: 'modal',
    priority: 'high',
    retryable: true,
  },
  'auth.session_failed': {
    title: 'Authentication failed',
    presentation: 'modal',
    priority: 'high',
    retryable: true,
  },
  'auth.sign_out_failed': {
    title: 'Sign-out failed',
    presentation: 'toast',
    priority: 'normal',
    retryable: true,
  },
  'zenoh.request_failed': {
    title: 'Request failed',
    presentation: 'toast',
    priority: 'normal',
    retryable: true,
  },
  'zenoh.command_failed': {
    title: 'Command failed',
    presentation: 'toast',
    priority: 'high',
    retryable: true,
  },
  'zenoh.subscription_failed': {
    title: 'Telemetry unavailable',
    presentation: 'toast',
    priority: 'normal',
    retryable: true,
  },
  'control.command_failed': {
    title: 'Mower control unavailable',
    presentation: 'toast',
    priority: 'critical',
    retryable: true,
  },
  'livestream.connection_failed': {
    title: 'Livestream unavailable',
    presentation: 'toast',
    priority: 'normal',
    retryable: true,
  },
  'telemetry.delayed': {
    title: 'Telemetry delayed',
    presentation: 'toast',
    priority: 'low',
    retryable: false,
  },
  'telemetry.invalid_payload': {
    title: 'Invalid telemetry received',
    presentation: 'silent',
    priority: 'low',
    retryable: false,
  },
};

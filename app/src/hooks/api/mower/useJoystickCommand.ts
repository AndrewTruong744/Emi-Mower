import { useMutation } from '@tanstack/react-query';
import type { JoystickCommand } from '@/generated/zenoh';
import { mowerJoystickPath } from '@/generated/zenohPaths';
import { zenohPut } from '@/config/zenohClient';
import { reportAppError } from '@/errors/reporter';
import { InputValidationError, isInputValidationError } from '@/errors/types';

export interface JoystickCommandParams extends JoystickCommand {
  mowerId: string;
}

/** Publishes one normalized joystick vector to the selected mower. */
export function useJoystickCommand() {
  return useMutation({
    mutationFn: async ({ mowerId, x, y }: JoystickCommandParams) => {
      const normalizedMowerId = mowerId.trim();
      if (!normalizedMowerId)
        throw new InputValidationError('A mower must be selected to send joystick commands');
      if (!Number.isFinite(x) || !Number.isFinite(y) || Math.abs(x) > 1 || Math.abs(y) > 1) {
        throw new InputValidationError('Joystick coordinates must be normalized between -1 and 1');
      }

      await zenohPut(mowerJoystickPath(normalizedMowerId), { x, y });
    },
    retry: false,
    gcTime: 0,
    onError: (error, variables) => {
      if (!isInputValidationError(error)) {
        reportAppError('control.command_failed', error, {
          dedupeKey: `control.command_failed:${variables.mowerId.trim()}`,
        });
      }
    },
  });
}

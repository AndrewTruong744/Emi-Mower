import { useMutation } from '@tanstack/react-query';
import type { MowerCommandRequest, MowerCommandResponse } from '@/generated/zenoh';
import { mowerCommandPath } from '@/generated/zenohPaths';
import { zenohQuery } from '@/config/zenohClient';
import { reportAppError } from '@/errors/reporter';
import { InputValidationError, isInputValidationError } from '@/errors/types';

type WithoutCommandId<T> = T extends { command_id: string } ? Omit<T, 'command_id'> : never;

export type MowerCommand = WithoutCommandId<MowerCommandRequest>;

export interface MowerCommandParams {
  mowerId: string;
  command: MowerCommand;
  /** Supply the same ID when deliberately retrying a command. */
  commandId?: string;
}

function createCommandId(): string {
  return globalThis.crypto?.randomUUID?.() ?? `command-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

/** Sends one state-changing mower command and waits for the mower's acceptance reply. */
export function useMowerCommand() {
  return useMutation({
    mutationFn: async ({ mowerId, command, commandId }: MowerCommandParams) => {
      const normalizedMowerId = mowerId.trim();
      if (!normalizedMowerId) throw new InputValidationError('A mower must be selected to send commands');

      const request: MowerCommandRequest = { ...command, command_id: commandId ?? createCommandId() };
      const response = await zenohQuery<MowerCommandResponse>(mowerCommandPath(normalizedMowerId), request);
      if (response.status === 'rejected') {
        throw new Error(response.reason ?? `The mower rejected ${command.type}`);
      }
      return response;
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

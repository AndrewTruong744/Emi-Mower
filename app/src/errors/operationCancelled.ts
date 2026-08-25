/** Marks expected cancellation caused by a superseded auth or Zenoh lifecycle. */
export class OperationCancelled extends Error {
  constructor(message = 'Operation cancelled') {
    super(message);
    this.name = 'OperationCancelled';
  }
}

export function isOperationCancelled(error: unknown): boolean {
  return error instanceof OperationCancelled;
}

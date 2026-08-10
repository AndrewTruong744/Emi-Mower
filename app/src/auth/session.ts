let authSessionVersion = 0;

export class AuthOperationCancelled extends Error {
  constructor() {
    super('Authentication operation cancelled');
    this.name = 'AuthOperationCancelled';
  }
}

export function getAuthSessionVersion(): number {
  return authSessionVersion;
}

export function invalidateAuthSession(): void {
  authSessionVersion += 1;
}

export function isAuthSessionCurrent(version: number): boolean {
  return version === authSessionVersion;
}

export function assertAuthSessionCurrent(version: number): void {
  if (version !== authSessionVersion) {
    throw new AuthOperationCancelled();
  }
}

export function isAuthOperationCancelled(error: unknown): boolean {
  return error instanceof AuthOperationCancelled;
}

import * as zenoh from '@eclipse-zenoh/zenoh-ts';

export type ZenohModule = typeof import('@eclipse-zenoh/zenoh-ts');

export async function loadZenoh(): Promise<ZenohModule> {
  return zenoh;
}

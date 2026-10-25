import { requireNativeModule } from 'expo-modules-core';
export interface NativeSample {
  subscriptionId: string;
  key: string;
  payload: string;
  put: boolean;
}
interface EmiZenohNative {
  call(request: string): Promise<string>;
  addListener(event: 'sample', listener: (sample: NativeSample) => void): { remove(): void };
}
export default requireNativeModule<EmiZenohNative>('EmiZenoh');

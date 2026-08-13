import { useCallback } from 'react';
import { useFocusEffect } from 'expo-router';
import * as ScreenOrientation from 'expo-screen-orientation';

export function useLandscapeMap() {
  useFocusEffect(
    useCallback(() => {
      void ScreenOrientation.lockAsync(ScreenOrientation.OrientationLock.LANDSCAPE);

      return () => {
        void ScreenOrientation.lockAsync(ScreenOrientation.OrientationLock.PORTRAIT_UP);
      };
    }, [])
  );
}

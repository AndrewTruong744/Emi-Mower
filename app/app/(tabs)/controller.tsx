import { Image } from 'expo-image';
import { Platform, StyleSheet, useWindowDimensions, Text, View } from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { IconSymbol } from '@/components/ui/icon-symbol';
import { Fonts } from '@/constants/theme';
import * as ScreenOrientation from 'expo-screen-orientation'
import { useCallback } from 'react';
import { useFocusEffect } from 'expo-router';

export default function TabTwoScreen() {
  useFocusEffect(
    useCallback(() => {
      const lockLandscape = async () => {
        await ScreenOrientation.lockAsync(
          ScreenOrientation.OrientationLock.LANDSCAPE_RIGHT
        );
      };

      lockLandscape();

      return () => {
        const unlockOrientation = async () => {
          await ScreenOrientation.lockAsync(
            ScreenOrientation.OrientationLock.PORTRAIT_UP
          );
        };
        unlockOrientation();
      };
    }, [])
  );

  const styles = StyleSheet.create({
    main: {
      padding: 50
    },
  });

  return (
    <ThemedView style={{ flex: 1, padding: 50}}>
      <ThemedText>Hello!!!!</ThemedText>
    </ThemedView>
  )
}


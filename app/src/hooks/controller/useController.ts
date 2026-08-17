import { useCallback, useState } from 'react';
import { Alert } from 'react-native';
import { Gesture } from 'react-native-gesture-handler';
import { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { scheduleOnRN } from 'react-native-worklets';

export interface RobotConfig {
  power: boolean;
  autonomous: boolean;
  estop: boolean;
}

const JOYSTICK_RADIUS = 100;
const DEFAULT_CONFIG: RobotConfig = { power: false, autonomous: false, estop: false };

interface UseControllerOptions {
  disabled?: boolean;
  onMove?: (coordinates: { x: number; y: number }) => void;
}

/** Owns all controller configuration, joystick, and emergency-stop state. */
export function useController({ disabled = false, onMove }: UseControllerOptions = {}) {
  const [currentConfig, setCurrentConfig] = useState<RobotConfig>(DEFAULT_CONFIG);
  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);

  const updateCurrentConfig = (updates: Partial<RobotConfig>) => {
    setCurrentConfig((previous) => ({ ...previous, ...updates }));
  };

  const handleMove = useCallback(
    (normalizedComponents: { x: number; y: number }) => onMove?.(normalizedComponents),
    [onMove]
  );

  const handlePower = () => {
    if (!disabled) updateCurrentConfig({ power: !currentConfig.power });
  };
  const handleAutonomous = () => {
    if (!disabled) updateCurrentConfig({ autonomous: !currentConfig.autonomous });
  };
  const handleEStop = () => {
    if (disabled) return;
    if (!currentConfig.estop) {
      Alert.alert(
        'EMERGENCY STOP',
        'Robot hardware execution has been halted immediately.',
        [{ text: 'OK' }]
      );
      updateCurrentConfig({ estop: true, power: false });
      return;
    }
    updateCurrentConfig({ estop: false });
  };

  const gesture = Gesture.Pan()
    .onUpdate((event) => {
      if (disabled) return;
      const distance = Math.sqrt(event.translationX ** 2 + event.translationY ** 2);
      const angle = Math.atan2(event.translationY, event.translationX);
      const limitedDistance = Math.min(distance, JOYSTICK_RADIUS);
      translateX.value = Math.cos(angle) * limitedDistance;
      translateY.value = Math.sin(angle) * limitedDistance;
      scheduleOnRN(handleMove, {
        x: translateX.value / JOYSTICK_RADIUS,
        y: (translateY.value / JOYSTICK_RADIUS) * -1,
      });
    })
    .onEnd(() => {
      if (disabled) return;
      translateX.value = withSpring(0);
      translateY.value = withSpring(0);
      scheduleOnRN(handleMove, { x: 0, y: 0 });
    });

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: translateX.value }, { translateY: translateY.value }],
  }));

  return {
    animatedStyle,
    currentConfig,
    gesture,
    handleAutonomous,
    handleEStop,
    handlePower,
  };
}

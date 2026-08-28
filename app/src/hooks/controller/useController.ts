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

export type ControllerCommand =
  | { type: 'emergency_stop' }
  | { type: 'set_power'; enabled: boolean }
  | { type: 'set_mode'; mode: 'manual' | 'auto' };

const JOYSTICK_RADIUS = 100;
const DEFAULT_CONFIG: RobotConfig = { power: false, autonomous: false, estop: false };

interface UseControllerOptions {
  disabled?: boolean;
  onMove?: (coordinates: { x: number; y: number }) => void;
  onCommand?: (command: ControllerCommand) => Promise<unknown>;
}

/** Owns all controller configuration, joystick, and emergency-stop state. */
export function useController({
  disabled = false,
  onMove,
  onCommand,
}: UseControllerOptions = {}) {
  const [currentConfig, setCurrentConfig] = useState<RobotConfig>(DEFAULT_CONFIG);
  const joystickDisabled =
    disabled || !currentConfig.power || currentConfig.autonomous || currentConfig.estop;
  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);

  const updateCurrentConfig = (updates: Partial<RobotConfig>) => {
    setCurrentConfig((previous) => ({ ...previous, ...updates }));
  };

  const handleMove = useCallback(
    (normalizedComponents: { x: number; y: number }) => onMove?.(normalizedComponents),
    [onMove]
  );

  const submitCommand = async (command: ControllerCommand): Promise<boolean> => {
    try {
      await onCommand?.(command);
      return true;
    } catch {
      // The command mutation reports failures centrally; retain the confirmed UI state.
      return false;
    }
  };

  const handlePower = async () => {
    if (disabled) return;
    const power = !currentConfig.power;
    if (await submitCommand({ type: 'set_power', enabled: power })) updateCurrentConfig({ power });
  };
  const handleAutonomous = async () => {
    if (disabled) return;
    const autonomous = !currentConfig.autonomous;
    if (await submitCommand({ type: 'set_mode', mode: autonomous ? 'auto' : 'manual' })) {
      updateCurrentConfig({ autonomous });
    }
  };
  const handleEStop = async () => {
    if (disabled || currentConfig.estop) return;
    if (await submitCommand({ type: 'emergency_stop' })) {
      Alert.alert('EMERGENCY STOP', 'The mower accepted the emergency-stop command.', [{ text: 'OK' }]);
      updateCurrentConfig({ estop: true, power: false });
    }
  };

  const gesture = Gesture.Pan()
    .enabled(!joystickDisabled)
    .onUpdate((event) => {
      if (joystickDisabled) return;
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
      if (joystickDisabled) return;
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

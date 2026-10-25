import { useCallback, useEffect, useRef, useState } from 'react';
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
const AXIS_ZERO_BAND = 0.03;
// Keep this comfortably below the simulation bridge's 200 ms command timeout.
const JOYSTICK_PUBLISH_INTERVAL_MS = 50;
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
  const latestMove = useRef<{ x: number; y: number } | null>(null);
  const publishTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const onMoveRef = useRef(onMove);
  const joystickDisabledRef = useRef(joystickDisabled);
  onMoveRef.current = onMove;
  joystickDisabledRef.current = joystickDisabled;

  const updateCurrentConfig = (updates: Partial<RobotConfig>) => {
    setCurrentConfig((previous) => ({ ...previous, ...updates }));
  };

  const stopMovement = useCallback(() => {
    if (publishTimer.current !== null) {
      clearInterval(publishTimer.current);
      publishTimer.current = null;
    }
    if (latestMove.current !== null) {
      latestMove.current = null;
      onMoveRef.current?.({ x: 0, y: 0 });
    }
  }, []);

  const handleMove = useCallback((coordinates: { x: number; y: number }) => {
    if (coordinates.x === 0 && coordinates.y === 0) {
      stopMovement();
      return;
    }
    if (joystickDisabledRef.current) return;
    latestMove.current = coordinates;
    onMoveRef.current?.(coordinates);
    if (publishTimer.current === null) {
      publishTimer.current = setInterval(() => {
        if (latestMove.current) onMoveRef.current?.(latestMove.current);
      }, JOYSTICK_PUBLISH_INTERVAL_MS);
    }
  }, [stopMovement]);

  useEffect(() => {
    if (joystickDisabled) {
      stopMovement();
      translateX.value = withSpring(0);
      translateY.value = withSpring(0);
    }
    return stopMovement;
  }, [joystickDisabled, stopMovement, translateX, translateY]);

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
      const limitedDistance = Math.min(distance, JOYSTICK_RADIUS);
      const scale = distance === 0 ? 0 : limitedDistance / distance;
      translateX.value = event.translationX * scale;
      translateY.value = event.translationY * scale;
      const x = translateX.value / JOYSTICK_RADIUS;
      const y = -translateY.value / JOYSTICK_RADIUS;
      scheduleOnRN(handleMove, {
        x: Math.abs(x) <= AXIS_ZERO_BAND ? 0 : x,
        y: Math.abs(y) <= AXIS_ZERO_BAND ? 0 : y,
      });
    })
    .onFinalize(() => {
      translateX.value = withSpring(0);
      translateY.value = withSpring(0);
      scheduleOnRN(stopMovement);
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

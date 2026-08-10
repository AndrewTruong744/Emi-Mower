import { Alert } from 'react-native';
import { Gesture } from 'react-native-gesture-handler';
import { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { scheduleOnRN } from 'react-native-worklets';
import { useState } from 'react';

export interface RobotConfig {
  power: boolean;
  autonomous: boolean;
  estop: boolean;
}

const JOYSTICK_RADIUS = 100;

export function useControls() {
  const [selectedId, setSelectedId] = useState(1);
  const [menuVisible, setMenuVisible] = useState(false);
  const [configs, setConfigs] = useState<Record<number, RobotConfig>>({
    1: { power: false, autonomous: false, estop: false },
    2: { power: false, autonomous: false, estop: false },
    3: { power: false, autonomous: false, estop: false },
    4: { power: false, autonomous: false, estop: false },
  });

  const currentConfig = configs[selectedId];
  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);

  const updateCurrentConfig = (updates: Partial<RobotConfig>) => {
    setConfigs((previous) => ({
      ...previous,
      [selectedId]: {
        ...previous[selectedId],
        ...updates,
      },
    }));
  };

  const handleMove = (normalizedComponents: { x: number; y: number }) => {
    console.log(`Config ${selectedId} move:`, normalizedComponents);
  };

  const handlePower = () => updateCurrentConfig({ power: !currentConfig.power });
  const handleAutonomous = () => updateCurrentConfig({ autonomous: !currentConfig.autonomous });

  const handleEStop = () => {
    if (!currentConfig.estop) {
      console.log(`🚨 EMERGENCY STOP ACTIVATED FOR CONFIG ${selectedId} 🚨`);
      Alert.alert(
        'EMERGENCY STOP',
        `Robot hardware execution for Config ${selectedId} has been halted immediately.`,
        [{ text: 'OK' }]
      );
      updateCurrentConfig({ estop: true, power: false });
    } else {
      console.log(`Resetting emergency stop for Config ${selectedId}`);
      updateCurrentConfig({ estop: false });
    }
  };

  const gesture = Gesture.Pan()
    .onUpdate((event) => {
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
    menuVisible,
    selectConfig: (id: number) => {
      setSelectedId(id);
      setMenuVisible(false);
    },
    selectedId,
    setMenuVisible,
  };
}

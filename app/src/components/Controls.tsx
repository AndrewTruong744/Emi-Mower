import { StyleSheet, View, Alert, Platform } from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import Animated, { useSharedValue, useAnimatedStyle, withSpring } from 'react-native-reanimated';
import { scheduleOnRN } from 'react-native-worklets';
import React, { useState } from 'react';
import { Button, Switch, Text, Menu } from 'react-native-paper';

const JOYSTICK_SIZE = 200;
const RADIUS = JOYSTICK_SIZE / 2;

interface RobotConfig {
  power: boolean;
  autonomous: boolean;
  estop: boolean;
}

export default function Controls() {
  const [selectedId, setSelectedId] = useState<number>(1);
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

  function handleMove(normalizedComponents : {x: number, y: number}) {
    console.log(`Config ${selectedId} move:`, normalizedComponents);
  }

  const updateCurrentConfig = (updates: Partial<RobotConfig>) => {
    setConfigs((prev) => ({
      ...prev,
      [selectedId]: {
        ...prev[selectedId],
        ...updates,
      },
    }));
  };

  function handlePower() {
    updateCurrentConfig({ power: !currentConfig.power });
  }

  function handleAutonomous() {
    updateCurrentConfig({ autonomous: !currentConfig.autonomous });
  }

  function handleEStop() {
    if (!currentConfig.estop) {
      console.log(`🚨 EMERGENCY STOP ACTIVATED FOR CONFIG ${selectedId} 🚨`);
      if (Platform.OS === 'web') {
        alert(
          `EMERGENCY STOP\n\nRobot hardware execution for Config ${selectedId} has been halted immediately.`
        );
      } else {
        Alert.alert(
          "EMERGENCY STOP",
          `Robot hardware execution for Config ${selectedId} has been halted immediately.`,
          [{ text: "OK" }]
        );
      }
      updateCurrentConfig({ estop: true, power: false });
    } else {
      console.log(`Resetting emergency stop for Config ${selectedId}`);
      updateCurrentConfig({ estop: false });
    }
  }

  const gesture = Gesture.Pan()
    .onUpdate((event) => {
      const distance = Math.sqrt(event.translationX ** 2 + event.translationY ** 2);
      const angle = Math.atan2(event.translationY, event.translationX);

      const limitedDist = Math.min(distance, RADIUS);
      translateX.value = Math.cos(angle) * limitedDist;
      translateY.value = Math.sin(angle) * limitedDist;

      const normalizedData = {
        x: translateX.value / RADIUS,
        y: (translateY.value / RADIUS) * -1,
      };

      if (handleMove) {
        scheduleOnRN(handleMove, normalizedData);
      }
    })
    .onEnd(() => {
      translateX.value = withSpring(0);
      translateY.value = withSpring(0);
      if (handleMove) {
        scheduleOnRN(handleMove, { x: 0, y: 0 });
      }
    });

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: translateX.value }, { translateY: translateY.value }],
  }));

  return (   
    <View style={styles.controls}>
      <View style={styles.bar}>
        {/* CONFIG DROPDOWN */}
        <View>
          <Menu
            visible={menuVisible}
            onDismiss={() => setMenuVisible(false)}
            anchor={
              <Button 
                mode="outlined" 
                onPress={() => setMenuVisible(true)}
                style={styles.dropdownButton}
                labelStyle={styles.dropdownButtonLabel}
              >
                #{selectedId}
              </Button>
            }
          >
            <Menu.Item onPress={() => { setSelectedId(1); setMenuVisible(false); }} title="Config 1" />
            <Menu.Item onPress={() => { setSelectedId(2); setMenuVisible(false); }} title="Config 2" />
            <Menu.Item onPress={() => { setSelectedId(3); setMenuVisible(false); }} title="Config 3" />
            <Menu.Item onPress={() => { setSelectedId(4); setMenuVisible(false); }} title="Config 4" />
          </Menu>
        </View>

        {/* E-STOP BUTTON */}
        <Button 
          mode="contained"
          onPress={handleEStop}
          style={[styles.estopButton, currentConfig.estop ? styles.estopActive : styles.estopInactive]}
          labelStyle={styles.estopLabel}
        >
          {currentConfig.estop ? "STOPPED" : "E-STOP"}
        </Button>

        {/* POWER SYSTEM TOGGLE SWITCH */}
        <View style={styles.toggleContainer}>
          <Text style={styles.toggleLabel}>
            {currentConfig.power ? "SYS: ON" : "SYS: OFF"}
          </Text>
          <Switch
            value={currentConfig.power}
            onValueChange={handlePower}
            color="#22c55e"
          />
        </View>

        {/* AUTONOMOUS MODE TOGGLE SWITCH */}
        <View style={styles.toggleContainer}>
          <Text style={styles.toggleLabel}>
            {currentConfig.autonomous ? "AUTO" : "MAN"}
          </Text>
          <Switch
            value={currentConfig.autonomous}
            onValueChange={handleAutonomous}
            color="#3b82f6"
          />
        </View>
      </View>
      <View style={styles.base}>
        <GestureDetector gesture={gesture}>
          <Animated.View 
            style={[styles.knob, animatedStyle]} 
          />
        </GestureDetector>
      </View>
    </View> 
  );
}

const styles = StyleSheet.create({
  controls: {
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
  },
  bar: {
    flexDirection: 'row',
    width: '95%',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    padding: 8,
    borderRadius: 12,
    marginBottom: 20,
    gap: 8,
  },
  dropdownButton: {
    borderColor: 'rgba(255, 255, 255, 0.3)',
    borderRadius: 8,
    minWidth: 0,
  },
  dropdownButtonLabel: {
    color: '#fff',
    fontSize: 13,
    marginHorizontal: 2,
    fontWeight: 'bold',
  },
  estopButton: {
    borderWidth: 2,
    borderRadius: 8,
  },
  estopInactive: {
    backgroundColor: '#dc2626',
    borderColor: '#b91c1c',
  },
  estopActive: {
    backgroundColor: '#991b1b',
    borderColor: '#450a0a',
  },
  estopLabel: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 13,
    letterSpacing: 0.5,
    marginVertical: 6,
  },
  toggleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  toggleLabel: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 12,
  },
  base: {
    width: JOYSTICK_SIZE,
    height: JOYSTICK_SIZE,
    borderRadius: RADIUS,
    backgroundColor: '#c8c8c8',
    borderWidth: 2,
    borderColor: '#ccc',
    justifyContent: 'center',
    alignItems: 'center',
  },
  knob: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#6200ee',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
});

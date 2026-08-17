import React, { useCallback } from 'react';
import { StyleSheet, View } from 'react-native';
import { GestureDetector } from 'react-native-gesture-handler';
import Animated from 'react-native-reanimated';
import { Button, Switch, Text } from 'react-native-paper';
import { useController } from '@/hooks/controller/useController';
import { useJoystickCommand } from '@/hooks/api/mower/useJoystickCommand';

interface ControlsProps {
  mowerId: string | null;
}

export default function Controls({ mowerId }: ControlsProps) {
  const joystickCommand = useJoystickCommand();
  const selectedMowerId = mowerId?.trim() ?? '';
  const isDisabled = !selectedMowerId;
  const sendJoystickCommand = useCallback(
    ({ x, y }: { x: number; y: number }) => {
      if (selectedMowerId) joystickCommand.mutate({ mowerId: selectedMowerId, x, y });
    },
    [joystickCommand, selectedMowerId]
  );
  const {
    animatedStyle,
    currentConfig,
    gesture,
    handleAutonomous,
    handleEStop,
    handlePower,
  } = useController({ disabled: isDisabled, onMove: sendJoystickCommand });

  return (
    <View style={styles.controls}>
      <View style={[styles.bar, isDisabled && styles.disabled]}>
        <Button
          mode="contained"
          disabled={isDisabled}
          onPress={handleEStop}
          testID="controller-estop"
          style={[
            styles.estopButton,
            currentConfig.estop ? styles.estopActive : styles.estopInactive,
          ]}
          labelStyle={styles.estopLabel}
        >
          {currentConfig.estop ? 'STOPPED' : 'E-STOP'}
        </Button>

        <View style={styles.toggleContainer}>
          <Text style={styles.toggleLabel}>{currentConfig.power ? 'SYS: ON' : 'SYS: OFF'}</Text>
          <Switch disabled={isDisabled} value={currentConfig.power} onValueChange={handlePower} color="#22c55e" />
        </View>

        <View style={styles.toggleContainer}>
          <Text style={styles.toggleLabel}>{currentConfig.autonomous ? 'AUTO' : 'MAN'}</Text>
          <Switch
            disabled={isDisabled}
            value={currentConfig.autonomous}
            onValueChange={handleAutonomous}
            color="#3b82f6"
          />
        </View>
      </View>

      <View style={[styles.base, isDisabled && styles.disabled]}>
        <GestureDetector gesture={gesture}>
          <Animated.View style={[styles.knob, animatedStyle]} />
        </GestureDetector>
      </View>
    </View>
  );
}

const JOYSTICK_SIZE = 200;

const styles = StyleSheet.create({
  controls: {
    alignItems: 'center',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
  },
  disabled: { opacity: 0.45 },
  bar: {
    alignItems: 'center',
    backgroundColor: '#f1f5f9',
    borderRadius: 12,
    flexDirection: 'row',
    gap: 8,
    justifyContent: 'space-between',
    marginBottom: 20,
    padding: 8,
    width: '95%',
  },
  estopButton: {
    borderRadius: 8,
    borderWidth: 2,
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
    fontSize: 13,
    fontWeight: 'bold',
    letterSpacing: 0.5,
    marginVertical: 6,
  },
  toggleContainer: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 4,
  },
  toggleLabel: {
    color: '#334155',
    fontSize: 12,
    fontWeight: '600',
  },
  base: {
    alignItems: 'center',
    backgroundColor: '#e2e8f0',
    borderColor: '#cbd5e1',
    borderRadius: JOYSTICK_SIZE / 2,
    borderWidth: 2,
    height: JOYSTICK_SIZE,
    justifyContent: 'center',
    width: JOYSTICK_SIZE,
  },
  knob: {
    backgroundColor: '#6200ee',
    borderRadius: 30,
    elevation: 5,
    height: 60,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    width: 60,
  },
});

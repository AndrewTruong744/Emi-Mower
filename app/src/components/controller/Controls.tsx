import React from 'react';
import { StyleSheet, View } from 'react-native';
import { GestureDetector } from 'react-native-gesture-handler';
import Animated from 'react-native-reanimated';
import { Button, Menu, Switch, Text } from 'react-native-paper';
import { useControls } from '@/hooks/useControls';

export default function Controls() {
  const {
    animatedStyle,
    currentConfig,
    gesture,
    handleAutonomous,
    handleEStop,
    handlePower,
    menuVisible,
    selectConfig,
    selectedId,
    setMenuVisible,
  } = useControls();

  return (
    <View style={styles.controls}>
      <View style={styles.bar}>
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
          {[1, 2, 3, 4].map((id) => (
            <Menu.Item key={id} onPress={() => selectConfig(id)} title={`Config ${id}`} />
          ))}
        </Menu>

        <Button
          mode="contained"
          onPress={handleEStop}
          style={[styles.estopButton, currentConfig.estop ? styles.estopActive : styles.estopInactive]}
          labelStyle={styles.estopLabel}
        >
          {currentConfig.estop ? 'STOPPED' : 'E-STOP'}
        </Button>

        <View style={styles.toggleContainer}>
          <Text style={styles.toggleLabel}>{currentConfig.power ? 'SYS: ON' : 'SYS: OFF'}</Text>
          <Switch value={currentConfig.power} onValueChange={handlePower} color="#22c55e" />
        </View>

        <View style={styles.toggleContainer}>
          <Text style={styles.toggleLabel}>{currentConfig.autonomous ? 'AUTO' : 'MAN'}</Text>
          <Switch
            value={currentConfig.autonomous}
            onValueChange={handleAutonomous}
            color="#3b82f6"
          />
        </View>
      </View>

      <View style={styles.base}>
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
  bar: {
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    borderRadius: 12,
    flexDirection: 'row',
    gap: 8,
    justifyContent: 'space-between',
    marginBottom: 20,
    padding: 8,
    width: '95%',
  },
  dropdownButton: {
    borderColor: 'rgba(255, 255, 255, 0.3)',
    borderRadius: 8,
    minWidth: 0,
  },
  dropdownButtonLabel: {
    color: '#fff',
    fontSize: 13,
    fontWeight: 'bold',
    marginHorizontal: 2,
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
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
  },
  base: {
    alignItems: 'center',
    backgroundColor: '#c8c8c8',
    borderColor: '#ccc',
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

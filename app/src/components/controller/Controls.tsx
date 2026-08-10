import React from 'react';
import { View } from 'react-native';
import { GestureDetector } from 'react-native-gesture-handler';
import Animated from 'react-native-reanimated';
import { Button, Menu, Switch, Text } from 'react-native-paper';
import { useControls } from '@/hooks/useControls';
import { controlsStyles as styles } from '@/styles/controlsStyles';

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

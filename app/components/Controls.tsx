import { StyleSheet, View, Text, Pressable, Switch, Alert } from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import Animated, { useSharedValue, useAnimatedStyle, withSpring } from 'react-native-reanimated';
import { scheduleOnRN } from 'react-native-worklets';
import React, { useState } from 'react';

const JOYSTICK_SIZE = 200;
const KNOB_SIZE = 60;
const RADIUS = JOYSTICK_SIZE / 2;

export default function Controls() {
  const [power, setPower] = useState(false);

  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);

  function handleMove(normalizedComponents : {x: number, y: number}) {
    console.log(normalizedComponents);
  }

  function handlePower() {
    setPower(!power)
  }

  function handleEStop() {
    console.log("🚨 EMERGENCY STOP ACTIVATED 🚨");
    Alert.alert("EMERGENCY STOP", "Robot hardware execution has been halted immediately.");
  }

  const gesture = Gesture.Pan()
    .onUpdate((event) => {
      // Calculate distance from center
      const distance = Math.sqrt(event.translationX ** 2 + event.translationY ** 2);
      const angle = Math.atan2(event.translationY, event.translationX);

      // Limit the knob to the circle radius
      const limitedDist = Math.min(distance, RADIUS);
      translateX.value = Math.cos(angle) * limitedDist;
      translateY.value = Math.sin(angle) * limitedDist;

      // Calculate normalized coordinates (-1 to 1)
      const normalizedData = {
        x: translateX.value / RADIUS,
        y: (translateY.value / RADIUS) * -1, // Up is positive
      };

      // Send normalized coordinates (-1 to 1) back to your robot logic
      if (handleMove) {
        scheduleOnRN(handleMove, normalizedData);
      }
    })
    .onEnd(() => {
      // Spring back to center
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
        {/* E-STOP BUTTON */}
        <Pressable 
          onPress={handleEStop}
          style={({ pressed }) => [
            styles.estopButton,
            pressed && styles.estopButtonPressed
          ]}
        >
          <Text style={styles.estopText}>E-STOP</Text>
        </Pressable>

        {/* POWER SYSTEM TOGGLE SWITCH */}
        <View style={styles.toggleContainer}>
          <Text style={styles.toggleLabel}>{power ? "SYS: ON" : "SYS: OFF"}</Text>
          <Switch
            trackColor={{ false: '#767577', true: '#81b0ff' }}
            thumbColor={power ? '#22c55e' : '#f4f3f4'}
            ios_backgroundColor="#3e3e3e"
            onValueChange={setPower}
            value={power}
          />
        </View>
      </View>
      <View style={styles.base}>
        <GestureDetector gesture={gesture}>
          <Animated.View style={[styles.knob, animatedStyle]} />
        </GestureDetector>
      </View>
    </View> 
  )
}

const styles = StyleSheet.create({
  controls: {
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    gap: ''
  },
  bar: {
    flexDirection: 'row',
    width: '90%',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.15)',
    padding: 12,
    borderRadius: 12,
    marginBottom: 20,
  },
  estopButton: {
    backgroundColor: '#dc2626', // Industrial red
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#b91c1c',
  },
  estopButtonPressed: {
    backgroundColor: '#991b1b', // Darker red on physical press feedback
    transform: [{ scale: 0.98 }],
  },
  estopText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 16,
    letterSpacing: 1,
  },
  toggleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  toggleLabel: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
  },
  base: {
    width: JOYSTICK_SIZE,
    height: JOYSTICK_SIZE,
    borderRadius: RADIUS,
    backgroundColor: 'rgb(200,200,200)',
    borderWidth: 2,
    borderColor: '#ccc',
    justifyContent: 'center',
    alignItems: 'center',
  },
  knob: {
    width: KNOB_SIZE,
    height: KNOB_SIZE,
    borderRadius: KNOB_SIZE / 2,
    backgroundColor: '#6200ee',
    elevation: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
  },
});
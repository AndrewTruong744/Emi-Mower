import { Tabs } from 'expo-router';
import React from 'react';

import { IconSymbol } from '@/components/ui/icon-symbol';
import { Colors } from '@/constants/theme';
import { useBoundStore } from '@/store/useBoundStore';
import { useColorScheme as useNativeColorScheme } from 'react-native';

export default function TabLayout() {
  const systemColorScheme = useNativeColorScheme();
  const themePreference = useBoundStore((state) => state.themePreference);
  const colorScheme =
    themePreference === 'system' ? (systemColorScheme ?? 'light') : themePreference;

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: Colors[colorScheme ?? 'light'].tint,
        headerShown: false,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Home',
          tabBarIcon: ({ color }) => <IconSymbol size={28} name="house.fill" color={color} />,
        }}
      />
      <Tabs.Screen
        name="controller"
        options={{
          title: 'Controller',
          tabBarIcon: ({ color }) => (
            <IconSymbol size={28} name="gamecontroller.fill" color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          title: 'Settings',
          tabBarIcon: ({ color }) => <IconSymbol size={28} name="gearshape.fill" color={color} />,
        }}
      />
    </Tabs>
  );
}

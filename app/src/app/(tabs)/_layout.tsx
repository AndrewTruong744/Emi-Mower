import { Tabs } from 'expo-router';
import React from 'react';

import { IconSymbol } from '@/components/ui/icon-symbol';
import { ResponsiveTabBar } from '@/components/navigation/ResponsiveTabBar';
import { Colors } from '@/constants/theme';
import { useBoundStore } from '@/store/useBoundStore';
import { useColorScheme as useNativeColorScheme, useWindowDimensions } from 'react-native';

const LANDSCAPE_TAB_BAR_WIDTH = 72;
const LANDSCAPE_TAB_BAR_HEIGHT = '100%' as const;
const PORTRAIT_TAB_BAR_HEIGHT = 72;
const PORTRAIT_TAB_BAR_BOTTOM_PADDING = 8;

export function getTabBarOptions(isLandscape: boolean) {
  return {
    tabBarPosition: isLandscape ? ('right' as const) : ('bottom' as const),
    tabBarStyle: {
      ...(isLandscape
        ? {
            width: LANDSCAPE_TAB_BAR_WIDTH,
            height: LANDSCAPE_TAB_BAR_HEIGHT,
            alignSelf: 'stretch' as const,
          }
        : {
            height: PORTRAIT_TAB_BAR_HEIGHT,
            paddingTop: 0,
            paddingBottom: PORTRAIT_TAB_BAR_BOTTOM_PADDING,
          }),
      ...(isLandscape ? { padding: 0 } : {}),
      alignItems: 'center' as const,
      justifyContent: 'center' as const,
    },
    tabBarItemStyle: {
      flex: 1,
      padding: 0,
      alignItems: 'center' as const,
      justifyContent: 'center' as const,
    },
    tabBarIconStyle: { margin: 0 },
  };
}

export function getTabIconStyle(_isLandscape: boolean) {
  return { transform: [{ rotate: '0deg' }] };
}

export default function TabLayout() {
  const systemColorScheme = useNativeColorScheme();
  const { width, height } = useWindowDimensions();
  const isLandscape = width > height;
  const themePreference = useBoundStore((state) => state.themePreference);
  const colorScheme =
    themePreference === 'system' ? (systemColorScheme ?? 'light') : themePreference;
  const tabBarOptions = getTabBarOptions(isLandscape);
  const tabIconStyle = getTabIconStyle(isLandscape);

  return (
    <Tabs
      tabBar={(props) => <ResponsiveTabBar {...props} isLandscape={isLandscape} />}
      screenOptions={{
        tabBarActiveTintColor: Colors[colorScheme ?? 'light'].tint,
        headerShown: false,
        ...tabBarOptions,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Home',
          tabBarIcon: ({ color }) => (
            <IconSymbol size={28} name="house.fill" color={color} style={tabIconStyle} />
          ),
        }}
      />
      <Tabs.Screen
        name="controller"
        options={{
          title: 'Controller',
          tabBarIcon: ({ color }) => (
            <IconSymbol size={28} name="gamecontroller.fill" color={color} style={tabIconStyle} />
          ),
        }}
      />
      <Tabs.Screen
        name="mowers"
        options={{
          title: 'Mowers',
          tabBarIcon: ({ color }) => (
            <IconSymbol size={28} name="chart.bar.fill" color={color} style={tabIconStyle} />
          ),
        }}
      />
      <Tabs.Screen
        name="map"
        options={{
          title: 'Map',
          tabBarIcon: ({ color }) => (
            <IconSymbol size={28} name="map.fill" color={color} style={tabIconStyle} />
          ),
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          title: 'Settings',
          tabBarIcon: ({ color }) => (
            <IconSymbol size={28} name="gearshape.fill" color={color} style={tabIconStyle} />
          ),
        }}
      />
    </Tabs>
  );
}

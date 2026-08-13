import React from 'react';
import { describe, expect, it, jest } from '@jest/globals';
import { fireEvent, render } from '@testing-library/react-native';
import { StyleSheet, View } from 'react-native';
import { ResponsiveTabBar } from '@/components/navigation/ResponsiveTabBar';

function createProps() {
  const navigation = {
    emit: jest.fn(() => ({ defaultPrevented: false })),
    navigate: jest.fn(),
  };
  const state = {
    index: 0,
    key: 'tabs',
    routeNames: ['home', 'map'],
    routes: [
      { key: 'home-key', name: 'home' },
      { key: 'map-key', name: 'map' },
    ],
    stale: false,
    type: 'tab',
  };
  const descriptors = {
    'home-key': {
      options: {
        title: 'Home',
        tabBarButtonTestID: 'tab-home',
        tabBarIcon: () => <View testID="home-icon" />,
      },
    },
    'map-key': {
      options: {
        title: 'Map',
        tabBarButtonTestID: 'tab-map',
        tabBarIcon: () => <View testID="map-icon" />,
      },
    },
  };

  return {
    state,
    descriptors,
    navigation,
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  } as any;
}

describe('ResponsiveTabBar', () => {
  it('renders centered portrait-style items in the landscape side rail and navigates on press', () => {
    const props = createProps();
    const screen = render(<ResponsiveTabBar {...props} isLandscape />);

    expect(StyleSheet.flatten(screen.getByTestId('responsive-tab-bar').props.style)).toMatchObject({
      width: 72,
      height: '100%',
      alignSelf: 'stretch',
      padding: 0,
      alignItems: 'center',
      justifyContent: 'center',
    });
    expect(StyleSheet.flatten(screen.getByTestId('tab-home').props.style)).toMatchObject({
      flex: 1,
      padding: 0,
      alignItems: 'center',
      justifyContent: 'center',
    });
    expect(
      StyleSheet.flatten(screen.getByTestId('tab-content-home').props.style)
    ).not.toHaveProperty('transform');

    fireEvent.press(screen.getByTestId('tab-map'));
    expect(props.navigation.emit).toHaveBeenCalledWith({
      type: 'tabPress',
      target: 'map-key',
      canPreventDefault: true,
    });
    expect(props.navigation.navigate).toHaveBeenCalledWith('map', undefined);
  });
});

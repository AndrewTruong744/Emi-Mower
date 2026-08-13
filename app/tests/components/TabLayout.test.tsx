import { beforeEach, describe, expect, it, jest } from '@jest/globals';
import { getTabBarOptions, getTabIconStyle } from '@/app/(tabs)/_layout';
import {
  getResponsiveTabBarStyle,
  getResponsiveTabContentStyle,
  getResponsiveTabItemStyle,
  getResponsiveTabLabelStyle,
} from '@/components/navigation/ResponsiveTabBar';
import { StyleSheet } from 'react-native';

describe('TabLayout', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('keeps the tab bar at the bottom with centered, upright icons in portrait', () => {
    const tabOptions = getTabBarOptions(false);

    expect(tabOptions).toMatchObject({
      tabBarPosition: 'bottom',
      tabBarStyle: {
        height: 72,
        paddingTop: 0,
        paddingBottom: 8,
        alignItems: 'center',
        justifyContent: 'center',
      },
      tabBarItemStyle: {
        flex: 1,
        padding: 0,
        alignItems: 'center',
        justifyContent: 'center',
      },
      tabBarIconStyle: { margin: 0 },
    });
    expect(tabOptions).not.toHaveProperty('tabBarLabelPosition');
    expect(getTabIconStyle(false)).toEqual({ transform: [{ rotate: '0deg' }] });
    expect(getResponsiveTabLabelStyle()).toBeUndefined();
    expect(StyleSheet.flatten(getResponsiveTabBarStyle(false))).toMatchObject({
      height: 72,
      flexDirection: 'row',
      paddingTop: 0,
      paddingBottom: 8,
      alignItems: 'center',
      justifyContent: 'center',
    });
    expect(StyleSheet.flatten(getResponsiveTabItemStyle())).toMatchObject({
      flex: 1,
      padding: 0,
      alignItems: 'center',
      justifyContent: 'center',
    });
  });

  it('moves the tab bar to the right and rotates icons in landscape', () => {
    const tabOptions = getTabBarOptions(true);

    expect(tabOptions).toMatchObject({
      tabBarPosition: 'right',
      tabBarStyle: {
        width: 72,
        height: '100%',
        alignSelf: 'stretch',
        padding: 0,
        alignItems: 'center',
        justifyContent: 'center',
      },
    });
    expect(tabOptions).not.toHaveProperty('tabBarLabelPosition');
    expect(getTabIconStyle(true)).toEqual({ transform: [{ rotate: '0deg' }] });
    expect(StyleSheet.flatten(getResponsiveTabBarStyle(true))).toMatchObject({
      width: 72,
      height: '100%',
      alignSelf: 'stretch',
      padding: 0,
      alignItems: 'center',
      justifyContent: 'center',
    });
    expect(StyleSheet.flatten(getResponsiveTabContentStyle(true))).toMatchObject({
      alignItems: 'center',
      justifyContent: 'center',
    });
    expect(StyleSheet.flatten(getResponsiveTabContentStyle(true))).not.toHaveProperty('transform');
  });
});

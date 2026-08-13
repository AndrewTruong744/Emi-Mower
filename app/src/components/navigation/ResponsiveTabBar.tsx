import type { BottomTabBarProps } from '@react-navigation/bottom-tabs';
import { Pressable, StyleSheet, Text, View } from 'react-native';

const LANDSCAPE_TAB_BAR_WIDTH = 72;
const PORTRAIT_TAB_BAR_HEIGHT = 72;
const PORTRAIT_TAB_BAR_BOTTOM_PADDING = 8;

export function getResponsiveTabBarStyle(isLandscape: boolean) {
  return isLandscape ? styles.landscapeBar : styles.portraitBar;
}

export function getResponsiveTabContentStyle(_isLandscape: boolean) {
  return styles.content;
}

export function getResponsiveTabItemStyle() {
  return styles.item;
}

export function getResponsiveTabLabelStyle() {
  return undefined;
}

interface ResponsiveTabBarProps extends BottomTabBarProps {
  isLandscape: boolean;
}

export function ResponsiveTabBar({
  state,
  descriptors,
  navigation,
  isLandscape,
}: ResponsiveTabBarProps) {
  return (
    <View style={getResponsiveTabBarStyle(isLandscape)} testID="responsive-tab-bar">
      {state.routes.map((route, index) => {
        const { options } = descriptors[route.key];
        const isFocused = state.index === index;
        const color = isFocused
          ? (options.tabBarActiveTintColor ?? '#2563eb')
          : (options.tabBarInactiveTintColor ?? '#64748b');
        const label =
          typeof options.tabBarLabel === 'string'
            ? options.tabBarLabel
            : (options.title ?? route.name);
        const showLabel =
          options.tabBarLabelVisibilityMode !== 'unlabeled' && options.tabBarShowLabel !== false;

        const onPress = () => {
          const event = navigation.emit({
            type: 'tabPress',
            target: route.key,
            canPreventDefault: true,
          });
          if (!isFocused && !event.defaultPrevented) navigation.navigate(route.name, route.params);
        };

        return (
          <Pressable
            key={route.key}
            accessibilityRole="tab"
            accessibilityState={isFocused ? { selected: true } : {}}
            accessibilityLabel={options.tabBarAccessibilityLabel}
            testID={options.tabBarButtonTestID}
            onPress={onPress}
            onLongPress={() => navigation.emit({ type: 'tabLongPress', target: route.key })}
            style={getResponsiveTabItemStyle()}
          >
            <View
              style={getResponsiveTabContentStyle(isLandscape)}
              testID={`tab-content-${route.name}`}
            >
              {options.tabBarIcon?.({ focused: isFocused, color, size: 28 })}
              {showLabel && (
                <Text style={[styles.label, { color }, getResponsiveTabLabelStyle()]}>{label}</Text>
              )}
            </View>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  portraitBar: {
    height: PORTRAIT_TAB_BAR_HEIGHT,
    flexDirection: 'row',
    paddingTop: 0,
    paddingBottom: PORTRAIT_TAB_BAR_BOTTOM_PADDING,
    alignItems: 'center',
    justifyContent: 'center',
  },
  landscapeBar: {
    width: LANDSCAPE_TAB_BAR_WIDTH,
    height: '100%',
    alignSelf: 'stretch',
    padding: 0,
    alignItems: 'center',
    justifyContent: 'center',
  },
  item: {
    flex: 1,
    padding: 0,
    alignItems: 'center',
    justifyContent: 'center',
  },
  content: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  label: {
    marginTop: 2,
    fontSize: 10,
    textAlign: 'center',
  },
});

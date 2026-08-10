const React = require('react');
const { View } = require('react-native');

module.exports = {
  __esModule: true,
  default: {
    View: ({ children, ...props }) => React.createElement(View, props, children),
  },
  useSharedValue: (value) => ({ value }),
  useAnimatedStyle: (factory) => factory(),
  withSpring: (value) => value,
};

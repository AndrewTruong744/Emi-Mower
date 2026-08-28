const React = require('react');

const mockGesture = {
  updateCallback: null,
  endCallback: null,
  onUpdate(callback) {
    this.updateCallback = callback;
    return this;
  },
  enabled() {
    return this;
  },
  onEnd(callback) {
    this.endCallback = callback;
    return this;
  },
};

module.exports = {
  __mockGesture: mockGesture,
  Gesture: { Pan: () => mockGesture },
  GestureDetector: ({ children }) => React.createElement(React.Fragment, null, children),
  GestureHandlerRootView: ({ children }) => React.createElement(React.Fragment, null, children),
};

/**
 * react-native-svg Jest mock
 *
 * Location: apps/mobile/__mocks__/react-native-svg.js
 *
 * react-native-svg uses native components (requireNativeComponent) that crash
 * in the Jest/jsdom environment with:
 *   "Invariant Violation: __fbBatchedBridgeConfig is not set, cannot invoke native modules"
 *
 * This mock replaces all SVG components with plain React.View stubs so tests
 * that transitively import react-native-svg (e.g. via @pilot/ui icons) can run.
 */

const React = require("react");
const { View } = require("react-native");

const stub = (name) => {
  const Comp = ({ children, testID }) =>
    React.createElement(View, { testID }, children);
  Comp.displayName = name;
  return Comp;
};

module.exports = {
  __esModule: true,
  default: stub("Svg"),
  Svg: stub("Svg"),
  Circle: stub("Circle"),
  Ellipse: stub("Ellipse"),
  G: stub("G"),
  Text: stub("Text"),
  TSpan: stub("TSpan"),
  TextPath: stub("TextPath"),
  Path: stub("Path"),
  Polygon: stub("Polygon"),
  Polyline: stub("Polyline"),
  Line: stub("Line"),
  Rect: stub("Rect"),
  Use: stub("Use"),
  Image: stub("Image"),
  Symbol: stub("Symbol"),
  Defs: stub("Defs"),
  LinearGradient: stub("LinearGradient"),
  RadialGradient: stub("RadialGradient"),
  Stop: stub("Stop"),
  ClipPath: stub("ClipPath"),
  Pattern: stub("Pattern"),
  Mask: stub("Mask"),
};

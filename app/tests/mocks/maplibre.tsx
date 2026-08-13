import React from 'react';
import { View } from 'react-native';

function NativeMapMock({ children, ...props }: React.ComponentProps<typeof View>) {
  return <View {...props}>{children}</View>;
}

export const Map = NativeMapMock;
export const Camera = NativeMapMock;
export const RasterSource = NativeMapMock;
export const GeoJSONSource = NativeMapMock;
export const Layer = NativeMapMock;

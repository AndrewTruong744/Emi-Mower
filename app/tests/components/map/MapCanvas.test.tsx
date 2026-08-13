import React from 'react';
import { describe, expect, it, jest } from '@jest/globals';
import { fireEvent, render } from '@testing-library/react-native';
import { MapCanvas } from '@/components/map/MapCanvas';

describe('MapCanvas', () => {
  it('uses high-fidelity satellite imagery tiles', () => {
    const screen = render(
      <MapCanvas
        boundary={[]}
        isBoundaryClosed={false}
        isSessionActive={false}
        mowerMarkers={[]}
        onMapPress={jest.fn()}
      />
    );

    expect(screen.getByTestId('mower-map')).toBeTruthy();
    expect(screen.UNSAFE_getByProps({ id: 'satellite-imagery' }).props).toMatchObject({
      tiles: [
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      ],
      tileSize: 256,
      maxzoom: 23,
      attribution: '© Esri, Maxar, Earthstar Geographics, and the GIS User Community',
    });
    expect(screen.UNSAFE_getByProps({ id: 'satellite-imagery-layer' }).props.style).toEqual({
      rasterOpacity: 1,
    });
    expect(screen.UNSAFE_getByProps({ id: 'openstreetmap-layer' }).props.style).toEqual({
      rasterOpacity: 0,
    });
  });

  it('shows the street map but ignores presses until satellite imagery is selected', () => {
    const onMapPress = jest.fn();
    const screen = render(
      <MapCanvas
        baseMap="street"
        boundary={[]}
        isBoundaryClosed={false}
        isSessionActive={false}
        mowerMarkers={[]}
        onMapPress={onMapPress}
      />
    );

    expect(screen.UNSAFE_getByProps({ id: 'openstreetmap-layer' }).props.style).toEqual({
      rasterOpacity: 1,
    });
    expect(screen.UNSAFE_getByProps({ id: 'satellite-imagery-layer' }).props.style).toEqual({
      rasterOpacity: 0,
    });

    fireEvent.press(screen.getByTestId('mower-map'), {
      nativeEvent: { lngLat: [-74.006, 40.7128] },
    });
    expect(onMapPress).not.toHaveBeenCalled();
  });

  it('keeps map sources and layer IDs stable while boundary data changes', () => {
    const props = {
      isBoundaryClosed: false,
      isSessionActive: false,
      mowerMarkers: [],
      onMapPress: jest.fn(),
    };
    const screen = render(<MapCanvas {...props} boundary={[]} />);

    expect(screen.UNSAFE_getByProps({ id: 'cutting-boundary' }).props.data).toEqual({
      type: 'FeatureCollection',
      features: [],
    });

    screen.rerender(<MapCanvas {...props} boundary={[{ x: -74.006, y: 40.7128 }]} />);
    screen.rerender(
      <MapCanvas
        {...props}
        boundary={[
          { x: -74.006, y: 40.7128 },
          { x: -74.005, y: 40.7128 },
          { x: -74.005, y: 40.7138 },
        ]}
        isBoundaryClosed
      />
    );

    expect(screen.UNSAFE_getByProps({ id: 'cutting-boundary-fill' })).toBeTruthy();
    expect(screen.UNSAFE_getByProps({ id: 'cutting-boundary-line' })).toBeTruthy();
    expect(screen.UNSAFE_getByProps({ id: 'cutting-boundary-points' })).toBeTruthy();
    expect(screen.UNSAFE_getByProps({ id: 'mower-markers' })).toBeTruthy();
  });

  it('uses valid GeoJSON while the boundary has only one point', () => {
    const screen = render(
      <MapCanvas
        boundary={[{ x: -74.006, y: 40.7128 }]}
        isBoundaryClosed={false}
        isSessionActive={false}
        mowerMarkers={[]}
        onMapPress={jest.fn()}
      />
    );

    const source = screen.UNSAFE_getByProps({ id: 'cutting-boundary' });
    expect(source.props.data.geometry).toEqual({
      type: 'Point',
      coordinates: [-74.006, 40.7128],
    });
  });

  it('adds map points while drawing and ignores map presses during a session', () => {
    const onMapPress = jest.fn();
    const screen = render(
      <MapCanvas
        boundary={[]}
        isBoundaryClosed={false}
        isSessionActive={false}
        mowerMarkers={[]}
        onMapPress={onMapPress}
      />
    );

    fireEvent.press(screen.getByTestId('mower-map'), {
      nativeEvent: { lngLat: [-74.006, 40.7128] },
    });
    expect(onMapPress).toHaveBeenCalledWith({ x: -74.006, y: 40.7128 });

    screen.rerender(
      <MapCanvas
        boundary={[]}
        isBoundaryClosed={false}
        isSessionActive={true}
        mowerMarkers={[]}
        onMapPress={onMapPress}
      />
    );
    fireEvent.press(screen.getByTestId('mower-map'), {
      nativeEvent: { lngLat: [-74.005, 40.713] },
    });
    expect(onMapPress).toHaveBeenCalledTimes(1);
  });
});

import {
  Camera,
  GeoJSONSource,
  Layer,
  Map as MapLibreMap,
  RasterSource,
} from '@maplibre/maplibre-react-native';
import { StyleSheet, View } from 'react-native';
import { MowerMapPosition } from '@/store/types';

interface MowerMarker {
  id: string;
  name: string;
  x: number;
  y: number;
}

export type MapBaseLayer = 'satellite' | 'street';

interface MapCanvasProps {
  baseMap?: MapBaseLayer;
  boundary: MowerMapPosition[];
  isBoundaryClosed: boolean;
  isSessionActive: boolean;
  mowerMarkers: MowerMarker[];
  onMapPress: (point: MowerMapPosition) => void;
}

const MAP_STYLE = {
  version: 8,
  sources: {},
  layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#dbeafe' } }],
};

const SATELLITE_TILE_URL =
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
const SATELLITE_ATTRIBUTION = '© Esri, Maxar, Earthstar Geographics, and the GIS User Community';

const EMPTY_FEATURE_COLLECTION = {
  type: 'FeatureCollection',
  features: [],
};

export function MapCanvas({
  baseMap = 'satellite',
  boundary,
  isBoundaryClosed,
  isSessionActive,
  mowerMarkers,
  onMapPress,
}: MapCanvasProps) {
  const closedBoundary = isBoundaryClosed || isSessionActive;
  const canPlaceBoundaryPoints = baseMap === 'satellite';
  const boundaryData =
    boundary.length > 0 ? boundaryFeature(boundary, closedBoundary) : EMPTY_FEATURE_COLLECTION;
  const markerData = mowerMarkerFeatureCollection(mowerMarkers);

  return (
    <View style={styles.container} testID="map-canvas">
      <MapLibreMap
        mapStyle={MAP_STYLE as any}
        style={styles.map}
        dragPan={!isSessionActive}
        touchZoom={!isSessionActive}
        doubleTapZoom={!isSessionActive}
        doubleTapHoldZoom={!isSessionActive}
        touchRotate={!isSessionActive}
        touchPitch={!isSessionActive}
        onPress={(event) => {
          if (isSessionActive || !canPlaceBoundaryPoints) return;
          const [x, y] = event.nativeEvent.lngLat;
          onMapPress({ x, y });
        }}
        testID="mower-map"
      >
        <Camera initialViewState={{ center: [-74.006, 40.7128], zoom: 17 }} />
        <RasterSource
          key="openstreetmap-source"
          id="openstreetmap"
          tiles={['https://tile.openstreetmap.org/{z}/{x}/{y}.png']}
          tileSize={256}
          maxzoom={19}
          attribution="© OpenStreetMap contributors"
        >
          <Layer
            key="openstreetmap-layer"
            id="openstreetmap-layer"
            type="raster"
            style={{ rasterOpacity: baseMap === 'street' ? 1 : 0 }}
          />
        </RasterSource>
        <RasterSource
          key="satellite-imagery-source"
          id="satellite-imagery"
          tiles={[SATELLITE_TILE_URL]}
          tileSize={256}
          maxzoom={23}
          attribution={SATELLITE_ATTRIBUTION}
        >
          <Layer
            key="satellite-imagery-layer"
            id="satellite-imagery-layer"
            type="raster"
            style={{ rasterOpacity: baseMap === 'satellite' ? 1 : 0 }}
          />
        </RasterSource>

        <GeoJSONSource
          key="cutting-boundary-source"
          id="cutting-boundary"
          data={boundaryData as any}
        >
          <Layer
            key="cutting-boundary-fill"
            id="cutting-boundary-fill"
            type="fill"
            style={{ fillColor: '#22c55e', fillOpacity: 0.22 }}
          />
          <Layer
            key="cutting-boundary-line"
            id="cutting-boundary-line"
            type="line"
            style={{ lineColor: '#15803d', lineWidth: 4, lineJoin: 'round' }}
          />
          <Layer
            key="cutting-boundary-points"
            id="cutting-boundary-points"
            type="circle"
            style={{
              circleColor: '#15803d',
              circleRadius: 5,
              circleStrokeColor: '#ffffff',
              circleStrokeWidth: 2,
            }}
          />
        </GeoJSONSource>

        <GeoJSONSource key="mower-markers-source" id="mower-markers" data={markerData as any}>
          <Layer
            key="mower-marker-circles"
            id="mower-marker-circles"
            type="circle"
            style={{
              circleColor: '#1d4ed8',
              circleRadius: 7,
              circleStrokeColor: '#ffffff',
              circleStrokeWidth: 2,
            }}
          />
        </GeoJSONSource>
      </MapLibreMap>
    </View>
  );
}

function boundaryFeature(points: MowerMapPosition[], isClosed: boolean) {
  const coordinates = points.map((point) => [point.x, point.y]);
  if (isClosed && points.length >= 3) {
    return {
      type: 'Feature',
      properties: {},
      geometry: { type: 'Polygon', coordinates: [[...coordinates, coordinates[0]]] },
    };
  }

  // A LineString must contain at least two positions. Keep the first tap
  // visible as a valid Point until the user adds another boundary point.
  if (points.length === 1) {
    return {
      type: 'Feature',
      properties: {},
      geometry: { type: 'Point', coordinates: coordinates[0] },
    };
  }

  return {
    type: 'Feature',
    properties: {},
    geometry: { type: 'LineString', coordinates },
  };
}

function mowerMarkerFeatureCollection(markers: MowerMarker[]) {
  return {
    type: 'FeatureCollection',
    features: markers.map((marker) => ({
      type: 'Feature',
      id: marker.id,
      properties: { name: marker.name },
      geometry: { type: 'Point', coordinates: [marker.x, marker.y] },
    })),
  };
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  map: { flex: 1 },
});

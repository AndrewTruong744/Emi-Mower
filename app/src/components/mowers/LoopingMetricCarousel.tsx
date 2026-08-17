import { useCallback, useState } from 'react';
import {
  FlatList,
  StyleSheet,
  useWindowDimensions,
  View,
} from 'react-native';
import { MetricChart, MetricChartProps } from './MetricChart';

interface LoopingMetricCarouselProps {
  charts: MetricChartProps[];
  testID: string;
}

/**
 * A virtualized paged chart carousel. Rendering only the nearby page keeps a
 * mower selection light even when each chart contains a full telemetry window.
 */
export function LoopingMetricCarousel({ charts, testID }: LoopingMetricCarouselProps) {
  const { width: windowWidth } = useWindowDimensions();
  const [pageWidth, setPageWidth] = useState(Math.max(windowWidth - 40, 1));

  const onLayout = useCallback((width: number) => {
    setPageWidth((currentWidth) => (currentWidth === width ? currentWidth : width));
  }, []);

  const renderChart = useCallback(
    ({ item }: { item: MetricChartProps }) => (
      <View style={{ width: pageWidth }}>
        <MetricChart {...item} style={styles.chart} />
      </View>
    ),
    [pageWidth]
  );

  return (
    <View
      testID={testID}
      onLayout={(event) => onLayout(event.nativeEvent.layout.width)}
      style={styles.container}
    >
      <FlatList
        data={charts}
        renderItem={renderChart}
        keyExtractor={(chart) => chart.title}
        horizontal
        pagingEnabled
        decelerationRate="fast"
        showsHorizontalScrollIndicator={false}
        initialNumToRender={1}
        maxToRenderPerBatch={1}
        windowSize={2}
        removeClippedSubviews
        getItemLayout={(_, index) => ({ index, length: pageWidth, offset: pageWidth * index })}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  chart: { marginBottom: 0 },
  container: { marginBottom: 14, overflow: 'hidden' },
});

import { useEffect, useRef, useState } from 'react';
import {
  NativeScrollEvent,
  NativeSyntheticEvent,
  ScrollView,
  StyleSheet,
  useWindowDimensions,
  View,
} from 'react-native';
import { MetricChart, MetricChartProps } from './MetricChart';

interface LoopingMetricCarouselProps {
  charts: MetricChartProps[];
  testID: string;
}

/** A paged chart carousel that wraps from the final metric back to the first. */
export function LoopingMetricCarousel({ charts, testID }: LoopingMetricCarouselProps) {
  const scrollViewRef = useRef<ScrollView>(null);
  const { width: windowWidth } = useWindowDimensions();
  const [pageWidth, setPageWidth] = useState(Math.max(windowWidth - 40, 1));
  const loopedCharts = charts.length > 1 ? [charts.at(-1)!, ...charts, charts[0]] : charts;

  useEffect(() => {
    if (pageWidth && charts.length > 1) {
      requestAnimationFrame(() => scrollViewRef.current?.scrollTo({ x: pageWidth, animated: false }));
    }
  }, [charts.length, pageWidth]);

  const handleMomentumEnd = (event: NativeSyntheticEvent<NativeScrollEvent>) => {
    if (!pageWidth || charts.length < 2) return;

    const page = Math.round(event.nativeEvent.contentOffset.x / pageWidth);
    if (page === 0) {
      scrollViewRef.current?.scrollTo({ x: pageWidth * charts.length, animated: false });
    } else if (page === charts.length + 1) {
      scrollViewRef.current?.scrollTo({ x: pageWidth, animated: false });
    }
  };

  return (
    <View
      testID={testID}
      onLayout={(event) => setPageWidth(event.nativeEvent.layout.width)}
      style={styles.container}
    >
      <ScrollView
        ref={scrollViewRef}
        horizontal
        pagingEnabled
        decelerationRate="fast"
        showsHorizontalScrollIndicator={false}
        onMomentumScrollEnd={handleMomentumEnd}
      >
        {loopedCharts.map((chart, index) => (
          <View key={`${chart.title}-${index}`} style={{ width: pageWidth }}>
            <MetricChart {...chart} style={styles.chart} />
          </View>
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  chart: { marginBottom: 0 },
  container: { marginBottom: 14, overflow: 'hidden' },
});

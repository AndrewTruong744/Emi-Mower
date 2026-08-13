import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';
import { Surface, Text } from 'react-native-paper';

export interface MetricChartProps {
  title: string;
  value: string;
  values: number[];
  color: string;
  style?: StyleProp<ViewStyle>;
}

export function MetricChart({ title, value, values, color, style }: MetricChartProps) {
  const minimum = Math.min(...values, 0);
  const maximum = Math.max(...values, 0);
  const range = Math.max(maximum - minimum, 1);

  return (
    <Surface elevation={1} style={[styles.card, style]}>
      <View style={styles.header}>
        <Text variant="titleSmall" style={styles.title}>
          {title}
        </Text>
        <Text variant="labelLarge" style={{ color }}>
          {value}
        </Text>
      </View>
      <View accessible accessibilityLabel={`${title} chart for the last 30 seconds`} style={styles.chart}>
        {values.map((sample, index) => (
          <View
            key={`${index}-${sample}`}
            style={[
              styles.bar,
              {
                backgroundColor: color,
                height: `${Math.max(((sample - minimum) / range) * 100, 3)}%`,
              },
            ]}
          />
        ))}
      </View>
      <View style={styles.axis}>
        <Text variant="labelSmall">30s ago</Text>
        <Text variant="labelSmall">now</Text>
      </View>
    </Surface>
  );
}

const styles = StyleSheet.create({
  axis: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 5, opacity: 0.6 },
  bar: { borderRadius: 2, flex: 1, marginHorizontal: 1, minWidth: 2 },
  card: { borderRadius: 16, marginBottom: 12, padding: 14 },
  chart: { alignItems: 'flex-end', flexDirection: 'row', height: 82 },
  header: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', marginBottom: 10 },
  title: { fontWeight: '700' },
});

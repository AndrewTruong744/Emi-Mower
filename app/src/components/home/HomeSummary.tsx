import { Link } from 'expo-router';
import { ScrollView, StyleSheet, View } from 'react-native';
import { Button, Card, Chip, Text } from 'react-native-paper';
import { useHomeSummary } from '@/hooks/useHomeSummary';

export function HomeSummary() {
  const { activeMowerName, fleetCount, items, sessionStatus } = useHomeSummary();

  return (
    <ScrollView contentContainerStyle={styles.container} testID="home-summary">
      <View style={styles.hero}>
        <Text variant="headlineMedium" style={styles.title}>
          Emi Mower
        </Text>
        <Text variant="bodyLarge" style={styles.subtitle}>
          Your fleet at a glance.
        </Text>
        <View style={styles.chips}>
          <Chip icon="robot">{fleetCount} mowers</Chip>
          <Chip icon={sessionStatus === 'Session active' ? 'play-circle' : 'map-marker'}>
            {sessionStatus}
          </Chip>
        </View>
      </View>

      <Card style={styles.highlight} mode="contained">
        <Card.Content>
          <Text variant="labelLarge">Selected mower</Text>
          <Text variant="titleLarge" style={styles.highlightTitle}>
            {activeMowerName}
          </Text>
          <Text variant="bodyMedium">Open Mowers to view live telemetry and graph history.</Text>
        </Card.Content>
        <Card.Actions>
          <Link href="/(tabs)/mowers" asChild>
            <Button>View telemetry</Button>
          </Link>
        </Card.Actions>
      </Card>

      <Text variant="titleMedium" style={styles.sectionTitle}>
        Workspace
      </Text>
      {items.map((item) => (
        <Card key={item.id} style={styles.card} mode="outlined" testID={`home-summary-${item.id}`}>
          <Card.Content>
            <View style={styles.cardHeader}>
              <Text variant="titleMedium">{item.title}</Text>
              <Chip compact>{item.status}</Chip>
            </View>
            <Text variant="bodyMedium" style={styles.description}>
              {item.description}
            </Text>
          </Card.Content>
          <Card.Actions>
            <Link href={item.href} asChild>
              <Button>{item.actionLabel}</Button>
            </Link>
          </Card.Actions>
        </Card>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  card: { marginBottom: 12 },
  cardHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 12,
    justifyContent: 'space-between',
  },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 16 },
  container: { padding: 20, paddingBottom: 36 },
  description: { marginTop: 8, opacity: 0.72 },
  hero: { marginBottom: 20 },
  highlight: { marginBottom: 24 },
  highlightTitle: { fontWeight: '700', marginBottom: 4, marginTop: 2 },
  sectionTitle: { fontWeight: '700', marginBottom: 10 },
  subtitle: { marginTop: 4, opacity: 0.7 },
  title: { fontWeight: '700' },
});

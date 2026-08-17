import { ScrollView, StyleSheet, View } from 'react-native';
import { Surface } from 'react-native-paper';
import { useMowers } from '@/hooks/mowers/useMowers';
import { MowerSelector } from '@/components/mowers/MowerSelector';
import Controls from './Controls';
import { Livestream } from './Livestream';

/** Composes mower selection, secure livestream access, and control inputs. */
export function ControllerDashboard() {
  const { activeMower, mowerIds, selectedMowerUuid, selectMower } = useMowers();

  return (
    <ScrollView contentContainerStyle={styles.content}>
      <MowerSelector
        mowerIds={mowerIds}
        selectedMowerUuid={selectedMowerUuid}
        onSelect={selectMower}
      />
      <View style={styles.livestreamContainer}>
        <Livestream mowerId={activeMower?.uuid ?? null} />
      </View>

      <Surface elevation={1} style={styles.controlsCard}>
        <Controls mowerId={selectedMowerUuid} />
      </Surface>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: 12, paddingBottom: 36 },
  controlsCard: { borderRadius: 16, marginTop: 8, padding: 16 },
  livestreamContainer: { alignItems: 'center', justifyContent: 'center' },
});

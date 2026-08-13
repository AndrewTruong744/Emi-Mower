import { useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { ActivityIndicator, Button, Text } from 'react-native-paper';
import { useMowers } from '@/hooks/mowers/useMowers';
import { AddMowerModal } from './AddMowerModal';
import { MowerIdentitySection } from './MowerIdentitySection';
import { MowerSelector } from './MowerSelector';
import { MowerStatusSection } from './MowerStatusSection';
import { MowerTelemetrySection } from './MowerTelemetrySection';
import { RenameMowerModal } from './RenameMowerModal';

export function Mowers() {
  const [isAddModalVisible, setAddModalVisible] = useState(false);
  const [isRenameModalVisible, setRenameModalVisible] = useState(false);
  const {
    activeMower,
    addMower,
    mowerOptions,
    renameActiveMower,
    selectMower,
    selectedMowerUuid,
  } = useMowers();

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <View style={styles.heading}>
            <Text variant="headlineMedium" style={styles.title}>
              Mowers
            </Text>
            <Text variant="bodyMedium" style={styles.subtitle}>
              Monitor your mower fleet and its active session.
            </Text>
          </View>
          <Button mode="contained" icon="plus" onPress={() => setAddModalVisible(true)} style={styles.addButton}>
            Add mower
          </Button>
        </View>

        <MowerSelector
          mowers={mowerOptions}
          selectedMowerUuid={selectedMowerUuid}
          onSelect={selectMower}
        />

        {activeMower ? (
          <>
            <MowerIdentitySection mower={activeMower} onEditName={() => setRenameModalVisible(true)} />
            <MowerStatusSection mower={activeMower} />
            <MowerTelemetrySection mower={activeMower} />
          </>
        ) : (
          <View style={styles.loading}>
            <ActivityIndicator />
            <Text>Loading mower data…</Text>
          </View>
        )}
      </ScrollView>

      <AddMowerModal
        visible={isAddModalVisible}
        onDismiss={() => setAddModalVisible(false)}
        onAddMower={addMower}
      />
      <RenameMowerModal
        visible={isRenameModalVisible}
        currentName={activeMower?.name ?? ''}
        onDismiss={() => setRenameModalVisible(false)}
        onRename={renameActiveMower}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  addButton: { alignSelf: 'flex-start', marginTop: 14 },
  header: { marginBottom: 20 },
  heading: { flexShrink: 1 },
  loading: { alignItems: 'center', gap: 10, paddingVertical: 48 },
  scrollContent: { padding: 20, paddingBottom: 36 },
  subtitle: { marginTop: 4, opacity: 0.65, paddingRight: 12 },
  title: { fontWeight: '700' },
});

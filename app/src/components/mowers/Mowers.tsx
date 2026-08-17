import { useCallback, useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { Button, Surface, Text } from 'react-native-paper';
import { useBoundStore } from '@/store/useBoundStore';
import { AddMowerModal } from './AddMowerModal';
import { MowerDetailsContent } from './MowerDetailsContent';
import { MowerSelector } from './MowerSelector';
import { RenameMowerModal } from './RenameMowerModal';

export function Mowers() {
  const [isAddModalVisible, setAddModalVisible] = useState(false);
  const [isRenameModalVisible, setRenameModalVisible] = useState(false);
  const mowerIds = useBoundStore((state) => state.mowers);
  const selectedMowerUuid = useBoundStore((state) => state.selectedMowerUuid);
  const addMowerToStore = useBoundStore((state) => state.addMower);
  const renameMowerInStore = useBoundStore((state) => state.renameMower);
  const selectMower = useBoundStore((state) => state.selectMower);
  // Only read the name while its form is visible; telemetry updates must not
  // cause the surrounding page and selector to render.
  const activeMowerName = useBoundStore((state) =>
    isRenameModalVisible && selectedMowerUuid
      ? state.mowerDetails[selectedMowerUuid]?.name ?? ''
      : ''
  );

  const addMower = useCallback(
    (uuid: string) => {
      const normalizedUuid = uuid.trim();
      if (!normalizedUuid) return { success: false, error: 'A mower UUID is required.' };
      if (mowerIds.includes(normalizedUuid)) {
        selectMower(normalizedUuid);
        return { success: false, error: 'That mower is already in your fleet.' };
      }

      addMowerToStore(normalizedUuid);
      return { success: true };
    },
    [addMowerToStore, mowerIds, selectMower]
  );

  const renameActiveMower = useCallback(
    (name: string) => {
      const trimmedName = name.trim();
      if (!selectedMowerUuid) return { success: false, error: 'Select a mower first.' };
      if (!trimmedName) return { success: false, error: 'A mower name is required.' };

      renameMowerInStore(selectedMowerUuid, trimmedName);
      return { success: true };
    },
    [renameMowerInStore, selectedMowerUuid]
  );

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
          mowerIds={mowerIds}
          selectedMowerUuid={selectedMowerUuid}
          onSelect={selectMower}
        />

        {mowerIds.length === 0 ? (
          <Surface elevation={1} style={styles.emptyState}>
            <Text variant="titleMedium" style={styles.emptyStateTitle}>
              No mowers in your fleet
            </Text>
            <Text variant="bodyMedium" style={styles.emptyStateMessage}>
              Add a mower to view its status, location, and telemetry.
            </Text>
          </Surface>
        ) : (
          <MowerDetailsContent
            mowerId={selectedMowerUuid}
            onEditName={() => setRenameModalVisible(true)}
          />
        )}
      </ScrollView>

      <AddMowerModal
        visible={isAddModalVisible}
        onDismiss={() => setAddModalVisible(false)}
        onAddMower={addMower}
      />
      <RenameMowerModal
        visible={isRenameModalVisible}
        currentName={activeMowerName}
        onDismiss={() => setRenameModalVisible(false)}
        onRename={renameActiveMower}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  addButton: { alignSelf: 'flex-start', marginTop: 14 },
  emptyState: { borderRadius: 16, padding: 20 },
  emptyStateMessage: { marginTop: 6, opacity: 0.65 },
  emptyStateTitle: { fontWeight: '700' },
  header: { marginBottom: 20 },
  heading: { flexShrink: 1 },
  scrollContent: { padding: 20, paddingBottom: 36 },
  subtitle: { marginTop: 4, opacity: 0.65, paddingRight: 12 },
  title: { fontWeight: '700' },
});
